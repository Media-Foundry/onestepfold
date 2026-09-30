"""Reversible ESM input projection for a frozen Mini folding comparison."""
from contextlib import contextmanager
import torch
from torch import nn


@contextmanager
def temporary_folding_esmc_projection(model, bridge):
    """Replace only linear_esm; restore the original module even on failure."""
    old = model.input_embedder.linear_esm
    if model.training or any(p.requires_grad for p in model.parameters()):
        raise ValueError('Requires a frozen inference model')
    if old.weight.shape != (449, 2560) or getattr(old, 'bias', None) is not None:
        raise ValueError('Unexpected native projection')
    weight, bias = bridge['weight'], bridge['bias']
    if weight.shape != (449, 1152) or bias.shape != (449,):
        raise ValueError('Unexpected bridge shape')
    if not torch.isfinite(weight).all() or not torch.isfinite(bias).all():
        raise ValueError('Nonfinite bridge')
    layer = nn.Linear(1152, 449, bias=True, device=old.weight.device, dtype=old.weight.dtype)
    with torch.no_grad():
        layer.weight.copy_(weight); layer.bias.copy_(bias)
    layer.eval().requires_grad_(False)
    model.input_embedder.linear_esm = layer
    try:
        yield layer
    finally:
        model.input_embedder.linear_esm = old
