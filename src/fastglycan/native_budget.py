"""Frozen native recycle-budget panel and CPU screening metrics."""
import itertools
import numpy as np
from fastglycan.functional_response_rank import response_geometry

CYCLES=(1,2,4)


def budget_parents(rows):
    dev=[i for i,r in enumerate(rows) if r['role']=='confirmation_candidate']
    stress=[i for i,r in enumerate(rows) if r['pdb_id'].lower()=='2v66']
    if len(dev)!=8 or len(stress)!=1 or stress[0] in dev:raise ValueError('expected archived8DEV plus2V66stress')
    return sorted(dev+stress)


def budget_order(sequence_index):
    return tuple(itertools.permutations(CYCLES))[sequence_index%6]


def screen_native(coordinates,inventory,labels,pairs,target_distances):
    x=np.asarray(coordinates,dtype=np.float64);ca=np.flatnonzero(inventory['atom_names']=='CA');i,j=np.asarray(pairs).T
    e=abs(np.linalg.norm(x[ca[i]]-x[ca[j]],axis=-1)-np.asarray(target_distances))
    task=float(np.where(e<=1,.5*e*e,e-.5).mean())
    geometry=response_geometry(x,labels)
    b=np.asarray(inventory['bonds'],int)[:,:2];r=np.asarray(inventory['reference'],float);res=inventory['residue_ids']
    peptide=res[b[:,0]]!=res[b[:,1]];expected=np.linalg.norm(r[b[:,0]]-r[b[:,1]],axis=-1);expected[peptide]=1.33
    d=np.linalg.norm(x[b[:,0]]-x[b[:,1]],axis=-1)-expected
    geometry.update(bond_rmse_reference=float(np.sqrt(np.mean(d*d))),peptide_mae_1p33=float(np.mean(abs(d[peptide]))) if peptide.any() else 0.)
    return dict(task=task,geometry=geometry)
