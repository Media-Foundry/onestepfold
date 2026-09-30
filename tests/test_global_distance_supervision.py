import numpy as np
import pytest
import torch
from fastglycan.global_distance_supervision import build_global_ca_distance_labels,global_ca_distance_loss


def mapping(x,mask=None):
    n=len(x)
    return dict(coordinates=np.asarray(x),mask=np.ones(n,dtype=bool) if mask is None else mask,
                atom_names=np.array(['CA']*n),residue_ids=np.arange(1,n+1),chain_ids=np.array(['A']*n))


def test_mask_isolation_and_empty_support():
    y=np.arange(150,dtype=float).reshape(50,3);mask=np.ones(50,dtype=bool);mask[-1]=False
    y[-1]=np.nan;labels=build_global_ca_distance_labels(mapping(y,mask))
    x=torch.tensor(y,requires_grad=True);loss=global_ca_distance_loss(x,labels);loss.backward()
    assert loss==0 and torch.isfinite(x.grad).all() and x.grad[-1].abs().sum()==0
    small=mapping(np.full((5,3),np.nan),np.zeros(5,dtype=bool));empty=build_global_ca_distance_labels(small)
    z=torch.full((5,3),float('nan'),requires_grad=True);out=global_ca_distance_loss(z,empty);out.backward()
    assert out==0 and z.grad.abs().sum()==0
    bad=mapping(np.ones((50,3)));bad['residue_ids'][1]=1
    with pytest.raises(ValueError):build_global_ca_distance_labels(bad)


def test_invariant_and_direct_pair_formula_with_tail_response():
    rng=np.random.default_rng(4);y=rng.normal(size=(64,3))*30;labels=build_global_ca_distance_labels(mapping(y))
    q,_=np.linalg.qr(rng.normal(size=(3,3)));q[:,0]*=np.linalg.det(q)
    x=torch.tensor(y@q+44);assert global_ca_distance_loss(x,labels)<1e-25
    x=torch.tensor(.5*y,requires_grad=True);loss=global_ca_distance_loss(x,labels)
    e=np.array([abs(np.linalg.norm(.5*y[i]-.5*y[j])-np.linalg.norm(y[i]-y[j])) for i in range(64) for j in range(i+24,64)])
    expected=np.where(e<10,.5*e*e/10,e-5).mean()
    assert abs(loss.item()-expected)<1e-12
    grad,=torch.autograd.grad(loss,x);assert (grad*torch.tensor(y)).sum()<0 and torch.isfinite(grad).all()
    assert np.max(labels['target_distance'].numpy())>30


def test_directional_derivative_and_chunk_boundary():
    rng=np.random.default_rng(17);y=rng.normal(size=(45,3))*8;labels=build_global_ca_distance_labels(mapping(y))
    x=torch.tensor(y+rng.normal(size=y.shape),requires_grad=True);v=torch.tensor(rng.normal(size=y.shape));v/=v.norm()
    loss=global_ca_distance_loss(x,labels);g,=torch.autograd.grad(loss,x);ad=(g*v).sum();h=1e-4
    fd=(global_ca_distance_loss(x+h*v,labels)-global_ca_distance_loss(x-h*v,labels))/(2*h)
    assert torch.allclose(ad,fd,atol=1e-9,rtol=1e-6)
    y=rng.normal(size=(400,3));labels=build_global_ca_distance_labels(mapping(y));assert len(labels['pairs'])>65536
    x=torch.tensor(y+2*rng.normal(size=y.shape));p=labels['pairs'];d=(x[p[:,0]]-x[p[:,1]]).norm(dim=-1)
    direct=torch.nn.functional.smooth_l1_loss(d,labels['target_distance'],beta=10)
    assert torch.allclose(global_ca_distance_loss(x,labels),direct,rtol=1e-13,atol=1e-13)
