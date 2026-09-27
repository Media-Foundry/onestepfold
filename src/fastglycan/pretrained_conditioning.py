"""Strict transfer of Mini-ESM folding weights with an explicit ESMC projection."""
import torch
from torch import nn


def install_pretrained_bridge(model, native_state, bridge):
    """Replace only the ESM projection, rejecting every other checkpoint mismatch."""
    key = 'input_embedder.linear_esm.weight'
    target = model.core.state_dict()
    if set(native_state) != set(target):
        raise ValueError('Native checkpoint keys differ from the folding core')
    if native_state[key].shape != (449, 2560) or target[key].shape != (449, 1152):
        raise ValueError('Unexpected native/ESMC projection dimensions')
    for name in target:
        if name != key and target[name].shape != native_state[name].shape:
            raise ValueError('Unexpected folding tensor shape: ' + name)
    weight, bias = bridge['weight'], bridge['bias']
    if weight.shape != (449, 1152) or bias.shape != (449,):
        raise ValueError('Invalid learned bridge shape')
    if not torch.isfinite(weight).all() or not torch.isfinite(bias).all():
        raise ValueError('Nonfinite bridge parameters')
    model.core.input_embedder.linear_esm = nn.Linear(1152, 449, bias=True)
    state = dict(native_state)
    state[key] = weight.float()
    state['input_embedder.linear_esm.bias'] = bias.float()
    model.core.load_state_dict(state, strict=True)
    loaded = model.core.state_dict()
    for name, value in native_state.items():
        if name != key:
            assert torch.equal(loaded[name].cpu(), value.cpu()), name
    assert torch.equal(loaded[key].cpu(), weight.float().cpu())
    assert torch.equal(loaded['input_embedder.linear_esm.bias'].cpu(), bias.float().cpu())
    return native_state[key].detach().clone()


class NativeProjectionReference(nn.Module):
    """Diagnostic only: supply the native ESM2 projection for identical chemistry."""

    def __init__(self, embedding, weight):
        super().__init__()
        self.register_buffer('embedding', embedding)
        self.register_buffer('weight', weight)

    def forward(self, esmc_embedding):
        if esmc_embedding.shape != (len(self.embedding), 1152):
            raise ValueError('Reference token alignment mismatch')
        return torch.nn.functional.linear(self.embedding, self.weight)
