import pytest
import torch
from torch import nn
from fastglycan.models.stage_pair_recovery import StagePairRecovery, aligned_pair_loss
from fastglycan.stage_pair_data import PairStageCapture


class MockStageBlock(nn.Module):
    def __init__(self,c_z=4,c_s=0,dropout=0.):
        super().__init__(); self.linear=nn.Linear(c_z,c_z)
    def forward(self,s,z,**kwargs): return s,z+torch.tanh(self.linear(z))


def test_native_suffix_identity_first_step_gradient_and_frozen_single():
    native=[MockStageBlock(),MockStageBlock()]
    boundary=torch.randn(5,5,4); z=boundary
    for block in native: _,z=block(None,z)
    base=(torch.randn(5,3),torch.randn(5,2),z.detach())
    ref=torch.randn_like(boundary); before=boundary.clone()
    net=StagePairRecovery(native,272001,input_channels=3,single_channels=2,pair_channels=4,width=8)
    c,stages=net(base,boundary,ref,2,0,1)
    assert torch.equal(c[2],base[2]) and c[0] is base[0] and c[1] is base[1]
    assert net(base,boundary,ref,2,0,0)[0] is base
    assert net.blocks[0].linear.weight.data_ptr()!=native[0].linear.weight.data_ptr()
    target=torch.randn_like(z)
    loss,_=aligned_pair_loss(stages,target,None,2.,'final'); loss.backward()
    assert all(b.linear.weight.grad.abs().sum()>0 for b in net.blocks)
    assert net.left.weight.grad.abs().sum()>0
    assert all(p.grad is None for b in native for p in b.parameters())
    assert torch.equal(boundary,before)
    a=net(base,boundary,ref,2,0,1)[0][2].clone()
    net(base,boundary,ref,2,0,3)
    assert torch.equal(a,net(base,boundary,ref,2,0,1)[0][2])


def test_hint_matches_actual_first_suffix_output_and_labels_are_loss_only():
    a=torch.randn(3,3,4,requires_grad=True); b=torch.randn_like(a,requires_grad=True)
    t=torch.randn_like(a); h=torch.randn_like(a)
    full,_=aligned_pair_loss((a,b),t,None,3.,'final')
    hint,_=aligned_pair_loss((a,b),t,h,3.,'hint')
    assert torch.allclose(hint,.5*(full+(a-h).square().mean()/3))
    hint.backward(); assert a.grad.abs().sum()>0 and b.grad.abs().sum()>0
    with pytest.raises(ValueError): aligned_pair_loss((a,b),t,None,3.,'hint')


def test_capture_clones_actual_native_stage_and_cleans_up_on_error():
    stack=nn.Module();stack.blocks=nn.ModuleList([MockStageBlock(),MockStageBlock()])
    z=torch.randn(4,4,4)
    with PairStageCapture(stack,(0,1)) as capture:
        _,x=stack.blocks[0](None,z);_,y=stack.blocks[1](None,x)
    assert torch.equal(capture.values[0],x) and torch.equal(capture.values[1],y)
    x.add_(1);assert not torch.equal(capture.values[0],x)
    with pytest.raises(RuntimeError):
        with PairStageCapture(stack,(0,)):
            stack.blocks[0](None,z);stack.blocks[0](None,z)
    assert not any(b._forward_hooks for b in stack.blocks)
