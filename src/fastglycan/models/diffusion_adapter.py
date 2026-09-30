"""Explicit, mergeable low-rank updates to Mini's token diffusion transformer.

Weight parametrization preserves native Linear implementations, including direct
weight access in fused paths. It does not change the forward sampling algorithm.
"""
import math

import torch
from torch import nn
from torch.nn.utils import parametrize


class DiffusionLowRankDelta(nn.Module):
    def __init__(self, weight, rank, generator):
        super().__init__()
        if weight.ndim != 2 or not 0 < rank <= min(weight.shape):
            raise ValueError('invalid matrix/rank')
        # A local CPU generator leaves model/sampler random streams untouched.
        initial = torch.randn(rank, weight.shape[1], generator=generator) / math.sqrt(weight.shape[1])
        self.down = nn.Parameter(initial.to(device=weight.device, dtype=weight.dtype))
        self.up = nn.Parameter(torch.zeros(weight.shape[0], rank, device=weight.device, dtype=weight.dtype))

    def forward(self, original):
        return original + self.up @ self.down


def attach_diffusion_adapter(model, rank=8, seed=20260930, expected_blocks=8):
    """Attach only the seven explicit attention/transition matrices per block.

    Model weights must already be frozen. All targets are checked before mutation;
    return exact module names and new parameters for optimizer/checkpoint auditing.
    """
    if any(p.requires_grad for p in model.parameters()):
        raise ValueError('freeze pretrained model before adapter installation')
    blocks = model.diffusion_module.diffusion_transformer.blocks
    if len(blocks) != expected_blocks:
        raise ValueError('unexpected diffusion transformer depth')
    suffixes = [f'attention_pair_bias.attention.linear_{x}' for x in ['q','k','v','o']]
    suffixes += [f'conditioned_transition_block.linear_nobias_{x}' for x in ['a1','a2','b']]
    targets = {}
    for i in range(len(blocks)):
        for suffix in suffixes:
            name = f'diffusion_module.diffusion_transformer.blocks.{i}.{suffix}'
            module = model.get_submodule(name)
            if not isinstance(module, nn.Linear) or parametrize.is_parametrized(module, 'weight'):
                raise ValueError('unsupported/already parametrized target: '+name)
            if not 0 < rank <= min(module.weight.shape):
                raise ValueError('rank exceeds target matrix')
            targets[name] = module
    generator = torch.Generator(device='cpu').manual_seed(seed)
    adapters = {}
    for name, module in targets.items():
        adapter = DiffusionLowRankDelta(module.weight, rank, generator)
        parametrize.register_parametrization(module, 'weight', adapter)
        adapters[name] = adapter
    return adapters


def merge_diffusion_adapter(model, names):
    """Materialize trained deltas into native weights, restoring native state keys."""
    names = list(names)
    if len(names) != len(set(names)):
        raise ValueError('duplicate adapter names')
    modules = [model.get_submodule(name) for name in names]
    for module in modules:
        if not parametrize.is_parametrized(module, 'weight') or len(module.parametrizations.weight) != 1:
            raise ValueError('expected exactly one weight parametrization')
        if not isinstance(module.parametrizations.weight[0], DiffusionLowRankDelta):
            raise ValueError('unrecognized parametrization')
    for module in modules:
        parametrize.remove_parametrizations(module, 'weight', leave_parametrized=True)
