import json
from pathlib import Path
import numpy as np
import torch

from fastglycan.articulated_output import ArticulatedOutput
from fastglycan.anchored_geometry import PoseVariables
from fastglycan.sidechain_repulsion import sidechain_pair_mask,sidechain_repulsion
from fastglycan.sidechain_projection_fit import fit_sidechain_projection


def test_pair_support_respects_axis_endpoints_and_whole_rigid_sides():
    t=json.loads(Path('reports/mini_ccd_ideal_template_2026-09-30/reference/templates.json').read_text())['records']['K']
    names=t['atom_names'];n=len(names);x=np.concatenate([np.array(t['ideal']),np.array(t['ideal'])+[3,4,1]])
    nn=np.tile(names,2);ids=np.repeat([1,2],n)
    adapter=ArticulatedOutput(x,nn,ids,'KK',{'LYS:'+','.join(names):dict(atom_names=names,bonds=t['bonds'])}).double()
    pairs=np.column_stack(np.triu_indices(len(x),1));mask=sidechain_pair_mask(adapter,nn,pairs)
    pose=PoseVariables(adapter,torch.tensor(x));initial=pose().detach().numpy()
    for seed in range(3):
        rng=np.random.default_rng(seed);values=[]
        for group,q in zip(pose.groups,pose.variables):
            v=torch.zeros_like(q);local=nn[group.indices[0].numpy()]
            for j,r in enumerate(group.rotations):
                if not set(local[list(r.moving)]).intersection({'N','CA','C','O','OXT'}):v[:,6+j]=torch.tensor(rng.normal(size=len(q)))
            values.append(v)
        y=pose.coordinates(values).detach().numpy();a,b=pairs[~mask].T
        np.testing.assert_allclose(np.linalg.norm(y[a]-y[b],axis=1),np.linalg.norm(initial[a]-initial[b],axis=1),atol=1e-12,rtol=0)
    cb=names.index('CB');nz=names.index('NZ')
    lookup={tuple(pair):bool(keep) for pair,keep in zip(pairs,mask)}
    assert not lookup[(cb,n+cb)] and lookup[(nz,n+cb)]
    fit=fit_sidechain_projection(adapter,torch.tensor(x),nn,max_iter=8,max_eval=12,
        collision_pairs=torch.tensor(pairs),collision_radii=torch.full((len(x),),1.7,dtype=torch.float64))
    assert fit['collision']['final_objective']<=fit['collision']['initial_objective']+1e-10
    bone=np.isin(nn,['N','CA','C','O','OXT'])
    assert torch.equal(fit['initial'][bone],fit['coordinates'][bone])


def test_penalty_matches_dense_formula_and_local_derivative():
    x=torch.tensor([[0.,0.,0.],[.73,.16,.2],[2.14,.43,-.2],[5.,0.,0.]],dtype=torch.float64,requires_grad=True)
    pairs=torch.tensor([[0,1],[0,2],[1,3]]);radii=torch.full((4,),1.7,dtype=torch.float64)
    value,terms=sidechain_repulsion(x,pairs,radii)
    d=np.array([3.4-np.linalg.norm(x.detach().numpy()[a]-x.detach().numpy()[b]) for a,b in pairs])
    expected=np.maximum(d-1.5,0).dot(np.maximum(d-1.5,0))/4/.25+np.mean(np.maximum(d-1.9,0)**2/.01)
    assert abs(float(value.detach())-expected)<1e-12
    assert torch.autograd.gradcheck(lambda z:sidechain_repulsion(z,pairs,radii)[0],(x,))
    zero,_=sidechain_repulsion(x,pairs[:0],radii);assert float(zero.detach())==0
