"""Candidate-scoped LoRA on native transition outputs; no merged weights."""
from contextlib import contextmanager
import math

import torch
from torch import nn


class LowRankProjection(nn.Module):
    def __init__(self, incoming, outgoing, rank=16):
        super().__init__()
        if rank <= 0 or rank > min(incoming, outgoing):
            raise ValueError('invalid weight update rank')
        self.down = nn.Linear(incoming, rank, bias=False)
        self.up = nn.Linear(rank, outgoing, bias=False)
        nn.init.kaiming_uniform_(self.down.weight, a=math.sqrt(5))
        nn.init.zeros_(self.up.weight)

    def forward(self, x):
        # alpha=rank: multiplier one; no dropout or weight merging.
        return self.up(self.down(x))


class RecycleLoRA(nn.Module):
    """Independent bank, temporarily attached only during candidate continuation.

The original module hierarchy/parameters are never replaced or registered here.
Activation checkpointing must be off: backward must not re-execute a forward
outside this context. Native eval chunking remains unchanged.
"""
    def __init__(self, stack, rank=16, expected_blocks=16):
        super().__init__()
        if len(stack.blocks) != expected_blocks:
            raise ValueError('unexpected native block count')
        if stack.blocks_per_ckpt is not None:
            raise ValueError('activation checkpointing unsupported by scoped hooks')
        self.paths = []
        self.adapters = nn.ModuleList()
        for i, block in enumerate(stack.blocks):
            for kind in ('pair_transition', 'single_transition'):
                path = f'blocks.{i}.{kind}.linear_no_bias'
                module = stack.get_submodule(path)
                if not isinstance(module, nn.Linear) or any(p.requires_grad for p in module.parameters()):
                    raise ValueError('frozen native linear required')
                self.paths.append(path)
                self.adapters.append(LowRankProjection(module.in_features, module.out_features, rank))
        self.config = dict(rank=rank, expected_blocks=expected_blocks)
        self._active = False

    @contextmanager
    def candidate(self, stack):
        if self._active or stack.blocks_per_ckpt is not None:
            raise RuntimeError('nested scope or checkpoint recomputation forbidden')
        handles = []
        self._active = True
        try:
            for path, adapter in zip(self.paths, self.adapters):
                def apply(module, inputs, output, adapter=adapter):
                    return output + adapter(inputs[0])
                handles.append(stack.get_submodule(path).register_forward_hook(apply))
            yield
        finally:
            for handle in handles:
                handle.remove()
            self._active = False
