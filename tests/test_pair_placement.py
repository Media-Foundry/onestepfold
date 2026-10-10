"""The native boundary observer must never silently reuse another invocation."""
import pytest
import torch
from torch import nn

from fastglycan.pair_placement import PairEntryCapture


class Block(nn.Module):
    def forward(self,s,z):
        return s,z+1


class Stack:
    def __init__(self):
        self.blocks=[Block()]


def test_entry_is_owned_snapshot_for_positional_and_keyword_paths():
    for keyword in (False,True):
        stack=Stack();z=torch.randn(4,4,3)
        with PairEntryCapture(stack) as cap:
            if keyword:stack.blocks[0](s=None,z=z)
            else:stack.blocks[0](None,z)
        assert torch.equal(cap.value,z) and cap.value.data_ptr()!=z.data_ptr()
        assert not cap.value.requires_grad
        assert not stack.blocks[0]._forward_pre_hooks


def test_repeated_missing_and_failed_capture_remove_hooks():
    stack=Stack();z=torch.ones(2,2,3)
    with pytest.raises(RuntimeError,match='twice'):
        with PairEntryCapture(stack):
            stack.blocks[0](None,z);stack.blocks[0](None,z)
    assert not stack.blocks[0]._forward_pre_hooks
    with pytest.raises(RuntimeError,match='not executed'):
        with PairEntryCapture(stack):pass
    assert not stack.blocks[0]._forward_pre_hooks
    with pytest.raises(ValueError):
        with PairEntryCapture(stack):raise ValueError('upstream error')
    assert not stack.blocks[0]._forward_pre_hooks
