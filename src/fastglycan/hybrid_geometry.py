"""Differentiable all-atom penalties and separately locked hard geometry gates.

Element radii follow AlphaFold residue_constants (C/N/O/S). They define an
operational overlap diagnostic; the acceptance limits below are pilot protocol
choices, not universal chemistry standards. Reference conformers supply intrabond
lengths and handedness; predictions never define the ideal chemistry.
"""
from dataclasses import dataclass,asdict
import numpy as np
import torch

RADII={'C':1.70,'N':1.55,'O':1.52,'S':1.80}

@dataclass(frozen=True)
class GeometryRules:
    bond_rmse_max: float=.25
    peptide_mae_max: float=.15
    chirality_fraction_min: float=.99
    severe_pairs_per_atom_max: float=.02
    max_penetration_max: float=2.0
    bond_regression_max: float=.01
    peptide_regression_max: float=.01
    severe_rate_regression_max: float=.002
    penetration_regression_max: float=.05
    chirality_regression_max: float=0.

class GeometryTopology:
    def __init__(self,atoms,reference):
        self.n=len(atoms)
        bonds=np.asarray(atoms.bonds.as_array()[:,:2],dtype=np.int64)
        self.bonds=torch.from_numpy(bonds)
        ref=np.asarray(reference,dtype=np.float64)
        self.peptide=torch.tensor([atoms.chain_id[i]==atoms.chain_id[j] and atoms.res_id[i]!=atoms.res_id[j] and {str(atoms.atom_name[i]),str(atoms.atom_name[j])}=={'C','N'} for i,j in bonds])
        ideal=np.linalg.norm(ref[bonds[:,0]]-ref[bonds[:,1]],axis=-1)
        ideal[self.peptide.numpy()]=1.33
        self.ideal=torch.tensor(ideal)
        # Exclude graph distances1,2,3 (1-2,1-3,1-4) and self from clashes.
        neighbors=[set() for _ in range(self.n)]
        for i,j in bonds:neighbors[i].add(int(j));neighbors[j].add(int(i))
        excluded=np.eye(self.n,dtype=bool)
        for i in range(self.n):
            seen={i};front={i}
            for _ in range(3):
                front={k for j in front for k in neighbors[j]}-seen;seen|=front
            excluded[i,list(seen)]=True
        self.pairs=torch.tensor(np.stack(np.where(np.triu(~excluded,1)),axis=1),dtype=torch.long)
        elements=[str(e).upper() for e in atoms.element]
        if set(elements)-set(RADII):raise ValueError('unsupported element; do not guess a radius')
        self.radii=torch.tensor([RADII[e] for e in elements])
        lookup={(str(c),int(r),str(n)):i for i,(c,r,n) in enumerate(zip(atoms.chain_id,atoms.res_id,atoms.atom_name))}
        centres=[];volumes=[]
        for chain,residue in sorted(set(zip(atoms.chain_id,atoms.res_id))):
            keys=[(str(chain),int(residue),name) for name in ('CA','N','C','CB')]
            if not all(k in lookup for k in keys):continue
            ca,n,c,cb=[lookup[k] for k in keys]
            volume=np.dot(np.cross(ref[n]-ref[ca],ref[c]-ref[ca]),ref[cb]-ref[ca])
            if abs(volume)>1e-4:centres.append([ca,n,c,cb]);volumes.append(volume)
        self.centres=torch.tensor(centres,dtype=torch.long).reshape(-1,4)
        self.volumes=torch.tensor(volumes,dtype=torch.float64)

    def terms(self,coordinate):
        x=coordinate[0] if coordinate.ndim==3 else coordinate
        if len(x)!=self.n:raise ValueError('topology/coordinate mismatch')
        bonds=self.bonds.to(x.device);ideal=self.ideal.to(x);peptide=self.peptide.to(x.device)
        distances=(x[bonds[:,0]]-x[bonds[:,1]]).norm(dim=-1)
        errors=distances-ideal
        zero=x.sum()*0
        bond=errors[~peptide].square().mean() if (~peptide).any() else zero
        peptide_loss=errors[peptide].square().mean() if peptide.any() else zero
        # Chunked fixed pair list limits activation memory without spatial truncation.
        pair=self.pairs.to(x.device);radii=self.radii.to(x)
        overlap=[];severe=[];penetration=[]
        for indices in pair.split(65536):
            d=(x[indices[:,0]]-x[indices[:,1]]).norm(dim=-1)
            depth=radii[indices[:,0]]+radii[indices[:,1]]-d
            overlap.append(torch.relu(depth-1.5).square().sum())
            severe.append((d<1.).sum());penetration.append(torch.relu(depth).max())
        clash=torch.stack(overlap).sum()/self.n if overlap else zero
        count=int(torch.stack(severe).sum()) if severe else 0
        max_pen=torch.stack(penetration).max() if penetration else zero
        centres=self.centres.to(x.device);volumes=self.volumes.to(x)
        if len(centres):
            ca,n,c,cb=centres.T
            signed=(torch.linalg.cross(x[n]-x[ca],x[c]-x[ca],dim=-1)*(x[cb]-x[ca])).sum(-1)
            ratio=signed*volumes.sign()/volumes.abs()
            chirality=torch.relu(.2-ratio).square().mean()
            fraction=float((ratio>0).double().mean().detach())
        else:chirality=zero;fraction=1.
        stats=dict(atom_count=self.n,bond_rmse=float(errors.square().mean().sqrt().detach()),
                   peptide_mae=float(errors[peptide].abs().mean().detach()) if peptide.any() else 0.,
                   chirality_fraction=fraction,severe_pairs=count,severe_pairs_per_atom=count/self.n,
                   max_penetration=float(max_pen.detach()))
        return dict(bond=bond,peptide=peptide_loss,clash=clash,chirality=chirality),stats


def hard_accept(task_loss,baseline_loss,geometry,baseline_geometry,rules=GeometryRules()):
    reasons=[]
    if not np.isfinite(task_loss) or not all(np.isfinite(v) for v in geometry.values()):
        return dict(accepted=False,reasons=['nonfinite'])
    if task_loss>=baseline_loss-1e-4:reasons.append('no_task_improvement')
    for key,limit in [('bond_rmse',rules.bond_rmse_max),('peptide_mae',rules.peptide_mae_max),
                      ('severe_pairs_per_atom',rules.severe_pairs_per_atom_max),('max_penetration',rules.max_penetration_max)]:
        if geometry[key]>limit:reasons.append(key+'_absolute')
    if geometry['chirality_fraction']<rules.chirality_fraction_min:reasons.append('chirality_absolute')
    for key,limit in [('bond_rmse',rules.bond_regression_max),('peptide_mae',rules.peptide_regression_max),
                      ('severe_pairs_per_atom',rules.severe_rate_regression_max),('max_penetration',rules.penetration_regression_max)]:
        if geometry[key]>baseline_geometry[key]+limit:reasons.append(key+'_regression')
    if geometry['chirality_fraction']<baseline_geometry['chirality_fraction']-rules.chirality_regression_max:
        reasons.append('chirality_regression')
    return dict(accepted=not reasons,reasons=reasons)
