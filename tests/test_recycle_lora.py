from types import SimpleNamespace

import pytest
import torch
from torch import nn

from fastglycan.models.recycle_lora import RecycleLoRA


class Stack(nn.Module):
    def __init__(self):
        super().__init__()
        self.blocks_per_ckpt = None
        self.blocks = nn.ModuleList([nn.Module() for _ in range(2)])
        for b in self.blocks:
            for kind in ('pair_transition', 'single_transition'):
                t = nn.Module(); t.linear_no_bias = nn.Linear(8, 8, bias=False)
                setattr(b, kind, t)
        self.requires_grad_(False)

    def forward(self, x):
        for b in self.blocks:
            x = x + b.pair_transition.linear_no_bias(x)
            x = x + b.single_transition.linear_no_bias(x)
        return x


def test_zero_replay_gradients_freeze_and_scope_restoration():
    torch.manual_seed(5); stack = Stack(); bank = RecycleLoRA(stack, 2, 2)
    x = torch.randn(3, 8); baseline = stack(x).detach().clone()
    original = {k:v.clone() for k,v in stack.state_dict().items()}
    optimizer = torch.optim.AdamW(bank.parameters(), lr=.01)
    for step in range(2):
        optimizer.zero_grad()
        with bank.candidate(stack):
            actual = stack(x)
        if step == 0: assert torch.equal(actual, baseline)
        actual.square().mean().backward()
        assert all(a.up.weight.grad.norm() > 0 for a in bank.adapters)
        if step: assert all(a.down.weight.grad.norm() > 0 for a in bank.adapters)
        optimizer.step()
        assert torch.equal(stack(x), baseline)
    assert all(p.grad is None for p in stack.parameters())
    assert all(torch.equal(v, original[k]) for k,v in stack.state_dict().items())
    with bank.candidate(stack):
        first = stack(x); stack(x+1); second = stack(x)
    assert torch.equal(first, second) and not torch.equal(first, baseline)
    assert not any(m._forward_hooks for m in stack.modules())


def test_exception_nested_and_checkpoint_fail_closed():
    stack = Stack(); bank = RecycleLoRA(stack, 2, 2)
    with pytest.raises(RuntimeError):
        with bank.candidate(stack):
            with bank.candidate(stack): pass
    assert not any(m._forward_hooks for m in stack.modules())
    with pytest.raises(ValueError):
        with bank.candidate(stack): raise ValueError('abort')
    assert not bank._active
    stack.blocks_per_ckpt = 1
    with pytest.raises(ValueError): RecycleLoRA(stack, 2, 2)
    with pytest.raises(RuntimeError):
        with bank.candidate(stack): pass


def test_zero_native_input_has_zero_weight_gradient_but_connected_output():
    from fastglycan.models.recycle_lora import LowRankProjection
    adapter=LowRankProjection(8,8,2)
    output=adapter(torch.zeros(3,8));output.retain_grad()
    output.sum().backward()
    assert output.grad.norm()>0
    assert adapter.up.weight.grad is not None and adapter.up.weight.grad.norm()==0
    assert adapter.down.weight.grad is not None and adapter.down.weight.grad.norm()==0
