"""Observed-GT quality and full-inventory chemical diagnostics, without a new gate."""
import numpy as np
from scipy.spatial import cKDTree

from .adapter_supervision import build_adapter_supervision
from .connection_audit import measure_connections
from .connection_diagnostics import describe_connection_distribution
from .scaling_metrics import lddt_observed


def prepare_pilot_scoring(mapping, bonds, sequence):
    labels=build_adapter_supervision(mapping,bonds,sequence)
    names=np.asarray(mapping['atom_names']);residues=np.asarray(mapping['residue_ids'])
    lookup={(int(r),str(a)):i for i,(r,a) in enumerate(zip(residues,names))}
    anchors=np.array([[lookup[(r,a)] for a in ['N','CA','C','O']] for r in range(1,len(sequence)+1)])
    pairs=np.asarray(bonds,dtype=int)[:,:2]
    peptide=(residues[pairs[:,0]]!=residues[pairs[:,1]])
    reference=np.asarray(mapping['reference'],dtype=float)
    ideal=np.linalg.norm(reference[pairs[:,0]]-reference[pairs[:,1]],axis=1);ideal[peptide]=1.33
    target=np.asarray(mapping['coordinates'],dtype=float);mask=np.asarray(mapping['mask'])
    assert mask.dtype==np.bool_ and mask[anchors].all()
    observed_target=np.zeros_like(target);observed_target[mask]=target[mask]
    return dict(mapping=mapping,labels=labels,anchors=anchors,sequence=sequence,bonds=pairs,
        peptide=peptide,legacy_bond_ideal=ideal,
        gt_branch=measure_connections(observed_target,anchors,sequence)['nearest_omega_sign'])


def score_diffusion_pilot(coordinate,context,calibration):
    x=np.asarray(coordinate,dtype=float);m=context['mapping'];labels=context['labels']
    names=np.asarray(m['atom_names']);residues=np.asarray(m['residue_ids']);mask=np.asarray(m['mask'])
    target=np.asarray(m['coordinates'],dtype=float);n=len(x)
    if x.shape!=target.shape or not np.isfinite(x).all():raise ValueError('invalid predicted inventory')
    ca=(names=='CA')&mask
    aa=lddt_observed(x[mask],target[mask],residues[mask]);ca_score=lddt_observed(x[ca],target[ca],residues[ca])
    xp=x[ca]-x[ca].mean(0);yp=target[ca]-target[ca].mean(0)
    u,_,vt=np.linalg.svd(xp.T@yp);rotation=u@np.diag([1,1,np.linalg.det(u@vt)])@vt
    rms=float(np.sqrt(np.mean(np.sum((xp@rotation-yp)**2,axis=1))))
    pairs=cKDTree(x).query_pairs(4.,output_type='ndarray')
    pairs=pairs[~np.isin(pairs[:,0]*n+pairs[:,1],labels['excluded'])]
    distance=np.linalg.norm(x[pairs[:,0]]-x[pairs[:,1]],axis=1)
    depth=np.maximum(0,labels['radii'].numpy()[pairs].sum(1)-distance)
    severe=distance<1.;bone=np.isin(names,['N','CA','C','O','OXT'])
    centres=labels['centres'].numpy();a,b,c,d=centres.T
    signed=(np.cross(x[b]-x[a],x[c]-x[a])*(x[d]-x[a])).sum(1)
    wrong=signed*labels['volumes'].numpy()<=0;main=names[a]=='CA'
    bonds=context['bonds'];bond_length=np.linalg.norm(x[bonds[:,0]]-x[bonds[:,1]],axis=1)
    errors=bond_length-context['legacy_bond_ideal'];peptide=context['peptide']
    observed=mask[bonds].all(1)
    gt_error=bond_length[observed]-np.linalg.norm(target[bonds[observed,0]]-target[bonds[observed,1]],axis=1)
    worst=[]
    for index in np.argsort(depth,kind='stable')[-10:][::-1]:
        pair=pairs[index]
        worst.append(dict(atoms=[dict(residue=int(residues[k]),atom=str(names[k]),chain=str(m['chain_ids'][k])) for k in pair],
            distance=float(distance[index]),penetration=float(depth[index])))
    connection=measure_connections(x,context['anchors'],context['sequence'])
    geometry=dict(atom_count=n,severe_pairs=int(severe.sum()),severe_pairs_per_atom=float(severe.sum()/n),
        severe_both_backbone=int((severe&bone[pairs[:,0]]&bone[pairs[:,1]]).sum()),
        max_penetration=float(depth.max()) if len(depth) else 0.,
        ca_chirality_wrong=int(wrong[main].sum()),ca_centres=int(main.sum()),
        sidechain_checked_wrong=int(wrong[~main].sum()),sidechain_checked_centres=int((~main).sum()),
        strict_checked_chirality=not bool(wrong.any()),
        legacy_reference_bond_rmse=float(np.sqrt(np.mean(errors**2))),
        legacy_reference_peptide_mae=float(np.mean(np.abs(errors[peptide]))),
        observed_gt_bond_rmse=float(np.sqrt(np.mean(gt_error**2))),
        worst_pairs=worst)
    return dict(all_atom_lddt=aa['score'],ca_lddt=ca_score['score'],ca_aligned_rmsd=rms,
        observed_atoms=int(mask.sum()),missing_gt_atoms=int((~mask).sum()),lddt_details=aa,geometry=geometry,
        connection_distribution=describe_connection_distribution(connection,context['sequence'],calibration),
        gt_branch_mismatches=int((connection['nearest_omega_sign']!=context['gt_branch']).sum()),
        legacy_joint_pass=None,legacy_joint_not_applicable='folding inference, no raw-displacement repair gate')
