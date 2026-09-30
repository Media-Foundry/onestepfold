import numpy as np
import pytest
import torch

from fastglycan.raw_contact_objective import RawContactPreservation,RawContactObjective
from fastglycan.calibrated_connection_objective import CalibratedConnectionObjective


def test_raw_only_selection_and_atom_weighting():
    raw=torch.tensor([[0.,0,0],[4.,0,0],[8.,0,0],[15.,0,0],[.2,0,0]],dtype=torch.double,requires_grad=True)
    # 0-3 upper endpoint excluded;0-4 overlap excluded;1-2 close sequence excluded.
    pairs=torch.tensor([[0,1],[0,2],[0,3],[0,4],[1,2],[1,3]])
    model=RawContactPreservation(raw,[1,6,7,12,20],pairs)
    assert model.contact_pairs.tolist()==[[0,1],[0,2],[1,3]]
    torch.testing.assert_close(model.contact_weights,torch.tensor([.25,.375,.375],dtype=torch.double))
    assert not model.contact_target.requires_grad and model(raw)==0
    x=raw.detach().clone();x[1,0]+=1;x[2,0]+=2;x.requires_grad_()
    expected=.625*(2*np.sqrt(2)-2)+.375*(2*np.sqrt(5)-2)
    assert float(model(x).detach())==pytest.approx(expected)
    assert torch.autograd.gradcheck(model,(x,),eps=1e-6,atol=1e-6,rtol=1e-4)
    rotation=torch.tensor([[0.,-1,0],[1.,0,0],[0.,0,1]],dtype=torch.double)
    torch.testing.assert_close(model(x@rotation+2),model(x),rtol=1e-12,atol=1e-12)


def test_empty_support_and_duplicate_rejection():
    x=torch.zeros((2,3),dtype=torch.double,requires_grad=True)
    model=RawContactPreservation(x,[1,2],torch.tensor([[0,1]]))
    assert model(x)==0 and torch.equal(torch.autograd.grad(model(x),x)[0],torch.zeros_like(x))
    with pytest.raises(ValueError,match='duplicate'):
        RawContactPreservation(x,[1,8],torch.tensor([[0,1],[0,1]]))


def test_contact_weight_is_not_scaled_with_chemistry_rho():
    raw=torch.tensor([[0.,1,0],[0.,0,0],[1.,0,0],[1.,1,0],
                      [5.,1,0],[5.,0,0],[6.,0,0],[6.,1,0]],dtype=torch.double)
    cal={'windows':{k:{'supported':True,'windows':{t:{'q95':{'pooled':.04}} for t in ['cn','angle_c','angle_n','omega','carbonyl']}} for k in ['Pro','other']}}
    args=(raw,[[0,1,2,3],[4,5,6,7]],'AA',torch.tensor([[0,4],[1,5]]),torch.ones(8,dtype=torch.double),cal)
    base=CalibratedConnectionObjective(*args)
    candidate=RawContactObjective(*args,residues=[1,1,1,1,8,8,8,8])
    x=raw.clone();x[4:,0]+=.5
    values=[torch.zeros((2,6),dtype=torch.double)]
    for rho in [1.,10.,100.]:
        a,_=base(x,values,rho);b,terms=candidate(x,values,rho)
        torch.testing.assert_close(b-a,terms['raw_contact'],rtol=1e-8,atol=1e-8)
        assert float(terms['raw_contact'])>0
