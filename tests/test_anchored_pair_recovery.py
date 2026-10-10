"""Reference execution must preserve initial outputs and the full shared gradient."""
import copy

import pytest
import torch
from torch import nn

from fastglycan.models.stage_pair_recovery import StagePairRecovery
from fastglycan.models.anchored_pair_recovery import (
    ReferenceAnchoredPairRecovery, reference_gradient_proxy, backward_reference_proxy)


class PairBlock(nn.Module):
    def __init__(self, c_z=4, c_s=0, dropout=0.):
        super().__init__()
        self.layer = nn.Linear(c_z, c_z)

    def forward(self, single, pair, **kwargs):
        return single, pair + torch.tanh(self.layer(pair))


def _case(dtype=torch.float64):
    torch.manual_seed(13)
    blocks = [PairBlock(), PairBlock()]
    model = ReferenceAnchoredPairRecovery(blocks, 272001,
        input_channels=3, single_channels=2, pair_channels=4, width=8).to(dtype)
    native = StagePairRecovery(blocks, 272001,
        input_channels=3, single_channels=2, pair_channels=4, width=8).to(dtype)
    reference = torch.randn(4, 4, 4, dtype=dtype)
    def datum():
        boundary = torch.randn_like(reference)
        with torch.no_grad():
            pair = boundary
            for block in native.blocks:
                _, pair = block(None, pair)
        return (torch.randn(4,3,dtype=dtype), torch.randn(4,2,dtype=dtype), pair), boundary
    return model, native, reference, datum(), [datum() for _ in range(3)]


def test_initial_native_identity_no_edit_and_read_only_reference():
    model, native, ref, (wt, boundary), candidates = _case()
    guard = ref.clone()
    anchor = model.prepare_reference(wt, boundary, ref, 1, 0)
    assert torch.count_nonzero(anchor.drift) == 0
    for aa, (base, z) in enumerate(candidates, 1):
        result = model(base,z,ref,1,0,aa,anchor=anchor)
        assert result[0] is base[0] and result[1] is base[1]
        assert torch.equal(result[2], base[2])
        assert torch.equal(native(base,z,ref,1,0,aa)[0][2], result[2])
    assert model(wt,boundary,ref,1,0,0,anchor=anchor) is wt
    assert torch.equal(ref, guard)


def test_proxy_pullback_matches_joint_autograd_and_finite_difference():
    model, _, ref, (wt, boundary), candidates = _case()
    model2 = copy.deepcopy(model)
    label = torch.randn_like(ref)
    def joint(net):
        a = net.prepare_reference(wt,boundary,ref,1,0)
        losses = [(net(b,z,ref,1,0,k,anchor=a)[2]-label).square().mean()
                  for k,(b,z) in enumerate(candidates,1)]
        return torch.stack(losses).mean()
    joint(model).backward()
    anchor = model2.prepare_reference(wt,boundary,ref,1,0)
    proxy = reference_gradient_proxy(anchor)
    for aa,(base,z) in enumerate(candidates,1):
        loss = (model2(base,z,ref,1,0,aa,anchor=proxy)[2]-label).square().mean()/len(candidates)
        loss.backward()
    backward_reference_proxy(anchor,proxy)
    for p,q in zip(model.parameters(), model2.parameters()):
        assert p.grad is not None and q.grad is not None
        torch.testing.assert_close(p.grad, q.grad, rtol=1e-11, atol=1e-12)
    parameter = model.blocks[0].layer.weight
    index = (1,2); exact = parameter.grad[index].item(); eps = 1e-6
    with torch.no_grad(): parameter[index] += eps
    plus = joint(model).item()
    with torch.no_grad(): parameter[index] -= 2*eps
    minus = joint(model).item()
    with torch.no_grad(): parameter[index] += eps
    assert (plus-minus)/(2*eps) == pytest.approx(exact, rel=1e-5, abs=1e-7)


def test_anchor_reuse_order_and_fixed_parameter_centering():
    model,native,ref,(wt,boundary),candidates = _case()
    with torch.no_grad():
        for p in model.parameters(): p.add_(torch.randn_like(p)*.01)
    native.load_state_dict(model.state_dict())
    with torch.no_grad():
        anchor = model.prepare_reference(wt,boundary,ref,1,0)
        correct=[]; raw=[]
        for aa,(base,z) in enumerate(candidates,1):
            correct.append(model(base,z,ref,1,0,aa,anchor=anchor)[2])
            raw.append(native(base,z,ref,1,0,aa)[0][2])
        a,b=torch.stack(correct),torch.stack(raw)
        torch.testing.assert_close(a-a.mean(0),b-b.mean(0),rtol=1e-12,atol=1e-12)
        base,z=candidates[0]
        assert torch.equal(a[0],model(base,z,ref,1,0,1,anchor=anchor)[2])


@pytest.mark.parametrize('change',['parameter','reference','anchor','position','owner'])
def test_stale_or_unrelated_anchor_is_rejected(change):
    model,_,ref,(wt,boundary),candidates=_case()
    anchor=model.prepare_reference(wt,boundary,ref,1,0)
    pos=1
    with torch.no_grad():
        if change=='parameter': next(model.parameters()).add_(.01)
        elif change=='reference': ref.add_(.01)
        elif change=='anchor': anchor.drift.add_(.01)
        elif change=='position': pos=2
        else: model=copy.deepcopy(model)
    base,z=candidates[0]
    with pytest.raises(ValueError):model(base,z,ref,pos,0,1,anchor=anchor)


def test_reference_vjp_decomposition_matches_explicit_centered_losses():
    from fastglycan.anchor_gradients import initial_site_gradients, flat_gradients
    model,_,ref,(wt,boundary),raw_candidates=_case()
    candidates=[(aa,base,z,torch.randn_like(z)) for aa,(base,z) in enumerate(raw_candidates,1)]
    vectors,_=initial_site_gradients(model,candidates,wt,boundary,ref,1,0,1.7)
    anchor=model.prepare_reference(wt,boundary,ref,1,0)
    error=torch.stack([model(base,z,ref,1,0,aa,anchor=anchor)[2]-target
                       for aa,base,z,target in candidates])
    parameters=list(model.parameters())
    raw=flat_gradients(error.square().mean()/1.7,parameters,retain_graph=True)
    common=flat_gradients(error.mean(0).square().mean()/1.7,parameters,retain_graph=True)
    aa=flat_gradients((error-error.mean(0)).square().mean()/1.7,parameters)
    for actual,expected in [(raw,vectors['anchored']),(common,vectors['anchored_common']),(aa,vectors['aa'])]:
        torch.testing.assert_close(actual,expected,rtol=1e-11,atol=1e-12)
