import torch
from fastglycan.factor_student import FactorStudent,expand_pair_factors


def test_zero_wt_batch_equivalence_and_gradient():
    torch.manual_seed(230301);m=FactorStudent(single_channels=12,pair_channels=4,rank=3,width=16)
    s=torch.randn(7,12);z=torch.randn(7,7,4);u,v=m(s,z,2,3,[3,4,5]);assert torch.equal(expand_pair_factors(u,v),torch.zeros(3,7,7,4))
    loss=(expand_pair_factors(u,v)[1]-torch.randn(7,7,4)).square().mean();loss.backward();assert m.v.weight.grad.norm()>0
    with torch.no_grad():m.v.weight.add_(-.1*m.v.weight.grad)
    u,v=m(s,z,2,3,[3,4,5]);d=expand_pair_factors(u,v);assert torch.equal(d[0],torch.zeros_like(d[0]))
    for i,a in enumerate([3,4,5]):
        a1,b1=m(s,z,2,3,[a]);torch.testing.assert_close(d[i],expand_pair_factors(a1,b1)[0],atol=1e-7,rtol=1e-5)
    m.zero_grad();d[1:].square().sum().backward();assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in m.parameters())


def test_factor_gauge_invariance_and_channel_specificity():
    torch.manual_seed(3);u=torch.randn(2,5,3,2,dtype=torch.double);v=torch.randn_like(u);a=torch.tensor([[2.,1.],[0.,.5]],dtype=torch.double)
    torch.testing.assert_close(expand_pair_factors(u@a,v@torch.linalg.inv(a).T),expand_pair_factors(u,v))
    d=expand_pair_factors(u,v);assert not torch.allclose(d,d.transpose(1,2))
