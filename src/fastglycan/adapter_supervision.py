"""Mask-aware GT objectives and explicit full-inventory chemistry auxiliaries."""
import numpy as np
import torch
from scipy.spatial import cKDTree

from fastglycan.experimental_training import observed_aligned_mse
from fastglycan.hybrid_geometry import RADII
from fastglycan.smooth_lddt_supervision import build_smooth_lddt_labels, smooth_lddt_loss


def build_adapter_supervision(mapping, bonds, sequence):
    target=torch.as_tensor(mapping['coordinates'],dtype=torch.float64)
    mask=torch.as_tensor(mapping['mask'],dtype=torch.bool)
    names=np.asarray(mapping['atom_names']);residues=np.asarray(mapping['residue_ids'])
    reference=np.asarray(mapping['reference'],dtype=float);n=len(names)
    if target.shape!=(n,3) or mask.shape!=(n,) or not torch.isfinite(target[mask]).all():
        raise ValueError('invalid observed GT')
    inventory=dict(atom_name=names,residue_id=residues)
    smooth=build_smooth_lddt_labels(dict(coordinate=target,coordinate_mask=mask),inventory)
    bonds=np.asarray(bonds,dtype=np.int64)[:,:2]
    if bonds.ndim!=2 or bonds.shape[1]!=2 or np.any(bonds<0) or np.any(bonds>=n):raise ValueError('invalid topology')
    observed=mask.numpy()[bonds].all(1);gt_bonds=bonds[observed]
    peptide=residues[gt_bonds[:,0]]!=residues[gt_bonds[:,1]]
    distances=(target[gt_bonds[:,0]]-target[gt_bonds[:,1]]).norm(dim=-1)
    neighbors=[set() for _ in range(n)]
    for a,b in bonds:neighbors[a].add(int(b));neighbors[b].add(int(a))
    excluded=set()
    for i in range(n):
        seen={i};front={i}
        for _ in range(3):
            front={k for j in front for k in neighbors[j]}-seen;seen|=front
        excluded.update(i*n+j for j in seen if j>i)
    lookup={(int(r),str(a)):i for i,(r,a) in enumerate(zip(residues,names))}
    if len(lookup)!=n:raise ValueError('duplicate native identity')
    centres=[]
    for i,aa in enumerate(sequence,1):
        if aa!='G':centres.append([lookup[(i,k)] for k in ['CA','N','C','CB']])
        if aa in 'IT':centres.append([lookup[(i,k)] for k in ['CB','CA','CG1' if aa=='I' else 'OG1','CG2']])
    centres=np.asarray(centres,dtype=np.int64).reshape(-1,4)
    a,b,c,d=centres.T
    volumes=(np.cross(reference[b]-reference[a],reference[c]-reference[a])*(reference[d]-reference[a])).sum(1)
    if np.any(np.abs(volumes)<1e-4):raise ValueError('degenerate reference stereocentre')
    radii=np.array([RADII[str(name)[0]] for name in names])
    return dict(coordinate=target,coordinate_mask=mask,smooth=smooth,bonds=torch.from_numpy(gt_bonds),
        bond_distance=distances,peptide=torch.from_numpy(peptide),centres=torch.from_numpy(centres),
        volumes=torch.from_numpy(volumes),radii=torch.from_numpy(radii),excluded=np.array(sorted(excluded),dtype=np.int64),
        allowed_pair_count=n*(n-1)//2-len(excluded),atoms=n)


def adapter_loss_parts(prediction, supervision, teacher=None):
    """Return raw components; the locked pilot specifies weights separately.

    A detached radius query includes all pairs with potentially positive clash
    penalties (max radius sum3.6Å < query4Å). No GT mask hides predicted clashes.
    Active-set derivatives are piecewise, not a global smoothness claim.
    """
    x=prediction
    if x.shape!=(supervision['atoms'],3) or not torch.isfinite(x).all():raise ValueError('invalid prediction')
    coordinate=observed_aligned_mse(x,supervision['coordinate'].to(x.device),supervision['coordinate_mask'].to(x.device))
    smooth=smooth_lddt_loss(x,supervision['smooth'])
    pair=supervision['bonds'].to(x.device);distance=supervision['bond_distance'].to(x);peptide=supervision['peptide'].to(x.device)
    errors=((x[pair[:,0]]-x[pair[:,1]]).norm(dim=-1)-distance).square()
    categories=[errors[peptide==kind].mean() for kind in [False,True] if (peptide==kind).any()]
    zero=x[:0].sum();bond=torch.stack(categories).mean() if categories else zero
    centres=supervision['centres'].to(x.device);v=supervision['volumes'].to(x)
    if len(centres):
        a,b,c,d=centres.T
        volume=(torch.linalg.cross(x[b]-x[a],x[c]-x[a],dim=-1)*(x[d]-x[a])).sum(-1)
        chirality=torch.relu(.2-volume*v.sign()/v.abs()).square().mean()
    else:chirality=zero
    local=cKDTree(x.detach().cpu().double().numpy()).query_pairs(4.,output_type='ndarray')
    local=local[~np.isin(local[:,0]*len(x)+local[:,1],supervision['excluded'])]
    if len(local):
        p=torch.as_tensor(local,device=x.device);r=supervision['radii'].to(x)
        depth=r[p[:,0]]+r[p[:,1]]-(x[p[:,0]]-x[p[:,1]]).norm(dim=-1)
        average=torch.relu(depth-1.5).square().sum()/len(x)
        k=min(16,supervision['allowed_pair_count'])
        tail=(torch.relu(torch.topk(depth,min(k,len(depth))).values-1.9)/.1).square().sum()/k
        clash=average+tail
    else:clash=zero
    parts=dict(coordinate=coordinate,smooth_lddt=smooth,bond=bond,chirality=chirality,clash=clash)
    if teacher is not None:
        parts['teacher']=observed_aligned_mse(x,teacher.detach().to(x),torch.ones(len(x),device=x.device,dtype=torch.bool))
    return parts
