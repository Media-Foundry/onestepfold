import numpy as np
import pytest
import torch
from types import SimpleNamespace
from fastglycan.chord_edit import chord_backbone_update, lift_backbone, initialize_target_atoms


def test_same_condition_cancels_and_sigma_sign():
    b=torch.randn(3,4,3,dtype=torch.double);s=torch.randn_like(b);t=torch.randn_like(b)
    a,c,_,_=chord_backbone_update(b,s,s,t,t)
    assert torch.equal(a,b) and torch.equal(c,b)
    shift=torch.ones_like(b)*.3
    # Constant drift difference across the two sigmas: same displacement for both.
    a,c,_,_=chord_backbone_update(b,s,s+16*shift,t,t+12*shift)
    torch.testing.assert_close(a,b+16*shift);torch.testing.assert_close(c,a)
    with pytest.raises(ValueError):chord_backbone_update(b,s,s,t,t,sigma_low=16)
    with pytest.raises(ValueError):chord_backbone_update(b,s[:2],s,t,t)


def test_rigid_lift_and_backbone_exact():
    x=torch.tensor([[0.,1.,0.],[0.,0.,0.],[1.,0.,0.],[1.,1.,0.],[0.,0.,1.]],dtype=torch.double)
    idx=np.array([[0,1,2,3]]);b=x[torch.tensor(idx)]
    q=torch.linalg.qr(torch.randn(3,3,dtype=torch.double))[0]
    q[:,0]*=torch.linalg.det(q)
    new=b@q+4
    y=lift_backbone(x,np.ones(5),idx,b,new)
    torch.testing.assert_close(y,x@q+4)
    assert torch.equal(y[torch.tensor(idx)],new)


def test_different_atom_inventory_and_identity_replay():
    src=SimpleNamespace(res_id=np.ones(5,dtype=int),atom_name=np.array(['N','CA','C','O','CB']))
    dst=SimpleNamespace(res_id=np.ones(6,dtype=int),atom_name=np.array(['N','CA','C','O','CB','OG']))
    # SimpleNamespace needs length for identity validation.
    class Atoms:
        def __init__(self,v):self.__dict__.update(v.__dict__)
        def __len__(self):return len(self.res_id)
    src,dst=Atoms(src),Atoms(dst)
    x=torch.tensor([[0.,1.,0.],[0.,0.,0.],[1.,0.,0.],[1.,1.,0.],[0.,0.,1.]])
    ref=torch.cat([x,torch.tensor([[0.,1.,1.]])])
    out=initialize_target_atoms(src,x,dst,ref,'A','S')
    assert out.shape==(6,3) and torch.equal(out[:4],x[:4])
    same=initialize_target_atoms(src,x,src,x,'A','A')
    assert torch.equal(same,x)
