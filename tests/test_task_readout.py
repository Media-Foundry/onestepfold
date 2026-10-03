import numpy as np
import torch
from fastglycan.task_readout import reference_node_features,ContextTaskReadout,AATaskReadout


def test_reference_invariance_and_missing_coordinates():
    rng=np.random.default_rng(4);x=rng.normal(size=(9,3));mask=np.ones(9,bool);mask[2]=False
    a=reference_node_features(x,mask,4)
    q,_=np.linalg.qr(rng.normal(size=(3,3)))
    y=x@q+8;y[2]=np.nan
    assert np.allclose(a,reference_node_features(y,mask,4),atol=1e-6)
    assert np.isfinite(a).all() and a.shape==(9,20)


def test_context_head_is_length_shared_and_reads_reference():
    torch.manual_seed(9);m=ContextTaskReadout(single_channels=7,pair_channels=5)
    with torch.no_grad():m.score[-1].weight.normal_(std=.02)
    for n in (6,9):
        s=torch.randn(n,7);z=torch.randn(n,n,5);ref=torch.randn(n,20,requires_grad=True)
        y=m(s,z,2,4,ref)
        assert y.shape==(20,) and y[4]==0
        y.sum().backward();assert ref.grad.norm()>0


def test_aa_only_is_context_free_and_wt_is_zero():
    m=AATaskReadout()
    y=m(3);assert y.shape==(20,) and torch.count_nonzero(y)==0
    (y-torch.arange(20)).square().mean().backward()
    assert m.score[-1].weight.grad.norm()>0
