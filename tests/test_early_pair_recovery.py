"""A frozen native continuation must transmit gradients and preserve ownership."""
import copy

import pytest
import torch
from torch import nn

from fastglycan.models.anchored_pair_recovery import (
    ReferenceAnchoredPairRecovery, backward_reference_proxy, reference_gradient_proxy)
from fastglycan.models.early_pair_recovery import EarlyPairRecovery, FrozenPairContinuation


class PairBlock(nn.Module):
    def __init__(self, c_z=4, c_s=0, dropout=0.):
        super().__init__()
        self.layer = nn.Linear(c_z, c_z)

    def forward(self, single, pair, **kwargs):
        # Include nonlocal dependence: moving the trainable blocks changes the
        # downstream input derivative even though every frozen weight is fixed.
        update = self.layer(pair + .1*pair.mean(0, keepdim=True))
        return single, pair + .1*torch.tanh(update)


def make_case():
    torch.manual_seed(71)
    native = [PairBlock().double() for _ in range(16)]
    tail = FrozenPairContinuation(native[2:], pair_channels=4)
    options = dict(input_channels=3, single_channels=2, pair_channels=4, width=8)
    early = EarlyPairRecovery(native[:2], 272001, tail, **options).double()
    late = ReferenceAnchoredPairRecovery(native[-2:], 272001, **options).double()
    reference_pair = torch.randn(4,4,4,dtype=torch.float64)
    records=[]
    for _ in range(4):
        entry = torch.randn_like(reference_pair)
        pair = entry
        with torch.no_grad():
            for index, block in enumerate(native):
                _, pair = block(None, pair)
                if index==13: boundary13=pair.clone()
        base=(torch.randn(4,3,dtype=torch.float64),
              torch.randn(4,2,dtype=torch.float64),pair)
        records.append((base,entry,boundary13))
    return early,late,tail,native,reference_pair,records


def test_initial_full_native_identity_equal_budget_and_noedit():
    early,late,tail,native,ref,records=make_case()
    wt,entry,late_entry=records[0]
    ea=early.prepare_reference(wt,entry,ref,1,0)
    la=late.prepare_reference(wt,late_entry,ref,1,0)
    assert torch.count_nonzero(ea.drift)==torch.count_nonzero(la.drift)==0
    assert sum(p.numel() for p in early.parameters())==sum(p.numel() for p in late.parameters())
    assert all(p.requires_grad for p in early.parameters())
    for name,parameter in early.named_parameters():
        if not name.startswith('blocks.'):
            assert torch.equal(parameter,dict(late.named_parameters())[name])
    for aa,(base,x,y) in enumerate(records[1:],1):
        a=early(base,x,ref,1,0,aa,anchor=ea)
        b=late(base,y,ref,1,0,aa,anchor=la)
        assert a[0] is base[0] and a[1] is base[1]
        assert torch.equal(a[2],base[2]) and torch.equal(a[2],b[2])
    assert early(wt,entry,ref,1,0,0,anchor=ea) is wt
    tail.check_unchanged()
    assert not any(p.grad is not None for block in native for p in block.parameters())


def test_frozen_tail_transmits_joint_and_proxy_gradient_and_finite_difference():
    model,_,tail,_,ref,records=make_case()
    second=copy.deepcopy(model)
    target=torch.randn_like(ref)
    wt,entry,_=records[0]

    def joint(net):
        anchor=net.prepare_reference(wt,entry,ref,1,0)
        return torch.stack([(net(base,x,ref,1,0,aa,anchor=anchor)[2]-target).square().mean()
                            for aa,(base,x,_) in enumerate(records[1:],1)]).mean()

    joint(model).backward()
    anchor=second.prepare_reference(wt,entry,ref,1,0)
    proxy=reference_gradient_proxy(anchor)
    for aa,(base,x,_) in enumerate(records[1:],1):
        ((second(base,x,ref,1,0,aa,anchor=proxy)[2]-target).square().mean()/3).backward()
    backward_reference_proxy(anchor,proxy)
    for a,b in zip(model.parameters(),second.parameters()):
        assert a.grad is not None and b.grad is not None
        torch.testing.assert_close(a.grad,b.grad,rtol=1e-11,atol=1e-12)
    parameter=model.blocks[0].layer.weight
    exact=parameter.grad[1,2].item()
    assert abs(exact)>1e-8
    epsilon=1e-6
    with torch.no_grad():parameter[1,2]+=epsilon
    plus=joint(model).item()
    with torch.no_grad():parameter[1,2]-=2*epsilon
    minus=joint(model).item()
    with torch.no_grad():parameter[1,2]+=epsilon
    assert (plus-minus)/(2*epsilon)==pytest.approx(exact,rel=1e-5,abs=1e-7)
    tail.check_unchanged();second.continuation.check_unchanged()


def test_optimizer_and_reconstruction_do_not_update_native_tail_or_single():
    model,_,tail,native,ref,records=make_case()
    wt,entry,_=records[0];base,x,_=records[1]
    guards=[tensor.clone() for tensor in (*base,entry,x,ref)]
    optimizer=torch.optim.AdamW(model.parameters(),lr=.01)
    for _ in range(2):
        optimizer.zero_grad(set_to_none=True)
        anchor=model.prepare_reference(wt,entry,ref,1,0)
        model(base,x,ref,1,0,1,anchor=anchor)[2].square().mean().backward()
        optimizer.step()
    model.train();tail.check_unchanged()
    clone_tail=FrozenPairContinuation(native[2:],pair_channels=4)
    clone=EarlyPairRecovery(native[:2],272001,clone_tail,input_channels=3,
                            single_channels=2,pair_channels=4,width=8).double()
    clone.load_state_dict(model.state_dict())
    with torch.no_grad():
        a=model.prepare_reference(wt,entry,ref,1,0)
        b=clone.prepare_reference(wt,entry,ref,1,0)
        expected=model(base,x,ref,1,0,1,anchor=a)
        clone(base,x,ref,1,0,3,anchor=b)
        actual=clone(base,x,ref,1,0,1,anchor=b)
    assert actual[0] is base[0] and actual[1] is base[1]
    assert torch.equal(expected[2],actual[2])
    assert all(torch.equal(tensor,guard) for tensor,guard in zip((*base,entry,x,ref),guards))
    clone_tail.check_unchanged()


def test_changed_frozen_tail_is_detected():
    _,_,tail,_,_,_=make_case()
    with torch.no_grad():next(tail.blocks.parameters()).add_(.1)
    with pytest.raises(RuntimeError,match='continuation changed'):
        tail.check_unchanged()
