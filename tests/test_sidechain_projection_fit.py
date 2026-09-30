import json
from pathlib import Path
import numpy as np
import torch

from fastglycan.articulated_output import ArticulatedOutput
from fastglycan.articulated_reference import geometry_invariants
from fastglycan.sidechain_projection_fit import fit_sidechain_projection


def test_fit_preserves_backbone_chemistry_and_rigid_equivariance():
    t=json.loads(Path('reports/mini_ccd_ideal_template_2026-09-30/reference/templates.json').read_text())['records']['T']
    names=t['atom_names'];x=torch.tensor(t['ideal'],dtype=torch.float64)
    variants={'THR:'+','.join(names):dict(atom_names=names,bonds=t['bonds'])}
    adapter=ArticulatedOutput(x,names,np.ones(len(x),int),'T',variants).double()
    raw=x.clone();raw[names.index('N')]+=torch.tensor([.35,-.25,.3]);raw.requires_grad_(True)
    fit=fit_sidechain_projection(adapter,raw,names)
    assert fit['improved'] and fit['eligible_dof']==1
    bone=np.isin(names,['N','CA','C','O','OXT'])
    assert torch.equal(fit['coordinates'][bone],fit['initial'][bone])
    assert torch.equal(fit['values'][0][:,:6],torch.zeros_like(fit['values'][0][:,:6]))
    before=geometry_invariants(fit['initial'].numpy(),t['bonds']);after=geometry_invariants(fit['coordinates'].numpy(),t['bonds'])
    for a,b in zip(before,after):np.testing.assert_allclose(a,b,atol=1e-12,rtol=0)
    for center,a,b,c in [('CA','N','C','CB'),('CB','CA','OG1','CG2')]:
        ix=[names.index(n) for n in [center,a,b,c]]
        volumes=[]
        for y in [fit['initial'],fit['coordinates']]:
            p,q,r,s=y[ix];volumes.append(torch.dot(torch.linalg.cross(q-p,r-p),s-p))
        assert volumes[0]*volumes[1]>0
    q=torch.tensor([[0.,-1.,0.],[1.,0.,0.],[0.,0.,1.]],dtype=torch.float64)
    moved=fit_sidechain_projection(adapter,raw.detach()@q+7,names)
    torch.testing.assert_close(moved['coordinates'],fit['coordinates']@q+7,atol=1e-8,rtol=0)
    assert raw.grad is None and not fit['coordinates'].requires_grad


def test_ring_only_and_glycine_have_no_sidechain_freedom():
    templates=json.loads(Path('reports/mini_ccd_ideal_template_2026-09-30/reference/templates.json').read_text())['records']
    for aa in ['P','G','A']:
        t=templates[aa];names=t['atom_names'];x=torch.tensor(t['ideal'],dtype=torch.float64)
        adapter=ArticulatedOutput(x,names,np.ones(len(x),int),aa,{t['ccd']+':'+','.join(names):dict(atom_names=names,bonds=t['bonds'])}).double()
        fit=fit_sidechain_projection(adapter,x,names)
        assert fit['eligible_dof']==0 and fit['iterations']==0 and fit['closure_calls']==0
        assert torch.equal(fit['coordinates'],fit['initial'])
