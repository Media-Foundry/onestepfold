import torch
from fastglycan.factor_student import expand_pair_factors
from fastglycan.factor_memorization import canonical_pair_factors, aligned_factor_loss, sparse_response_masks


def test_canonical_scale_sign_and_full_reconstruction():
    torch.manual_seed(7)
    x=torch.randn(2,6,6,3)
    u,v,groups,e=canonical_pair_factors(x,6)
    torch.testing.assert_close(expand_pair_factors(u,v),x,atol=2e-6,rtol=2e-6)
    piv=u.abs().argmax(1,keepdim=True)
    assert (u.gather(1,piv)>=0).all()
    assert e['boundary_near_degenerate']==0
    assert aligned_factor_loss(u,v,u,v,groups)<1e-12


def test_degenerate_rotation_is_not_penalized_and_gradient_is_finite():
    x=torch.eye(5)[None,:,:,None]
    u,v,g,e=canonical_pair_factors(x,5)
    q,_=torch.linalg.qr(torch.randn(5,5))
    pu=(u@q).requires_grad_();pv=(v@q).requires_grad_()
    loss=aligned_factor_loss(pu,pv,u,v,g)
    assert e['clustered_vectors']==5 and loss<1e-12
    loss.backward()
    assert torch.isfinite(pu.grad).all() and torch.isfinite(pv.grad).all()
    torch.testing.assert_close(expand_pair_factors(pu,pv),x,atol=2e-6,rtol=2e-6)


def test_sparse_masks_directed_budget_and_locality():
    r=torch.zeros(7,7,2);r[6,0]=10
    ca=torch.stack([torch.arange(7)*10.,torch.zeros(7),torch.zeros(7)],-1)
    masks=sparse_response_masks(r,3,ca)
    assert masks['rowcol'].sum()==13 and masks['contact'].sum()==25
    assert masks['top_row_budget'].sum()==13 and masks['top_contact_budget'].sum()==25
    assert masks['top_row_budget'][6,0] and not masks['rowcol'][6,0]
    assert not masks['contact'][0].any()
