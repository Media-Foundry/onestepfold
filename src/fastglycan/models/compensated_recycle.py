"""Cached native Mini continuation and a trainable pre-recycle correction.

Native bridge arithmetic follows prefix_recycle.py (Apache-2.0, ByteDance).
Only the input embedder is bypassed, using that candidate's archived s_inputs.
No target final state is accepted by the correction network.
"""
from dataclasses import dataclass

import torch
from torch import nn

from fastglycan.models.prefix_recycle import capture_rng_state, restore_rng_state


@dataclass(frozen=True)
class RecycleInitialization:
    inputs: torch.Tensor
    single: torch.Tensor
    pair: torch.Tensor


def initialize_cached_recycle(model, features, s_inputs):
    """Native initialization, with already computed candidate input embedding."""
    if model.training or model.train_confidence_only:
        raise ValueError('ordinary frozen eval folding model required')
    if any(p.requires_grad for p in model.parameters()):
        raise ValueError('native weights must remain frozen')
    if s_inputs.ndim != 2 or s_inputs.dtype != torch.float32:
        raise ValueError('unbatched FP32 input memory required')
    s = model.linear_no_bias_sinit(s_inputs)
    z = model.linear_no_bias_zinit1(s)[..., None, :] + model.linear_no_bias_zinit2(s)[..., None, :, :]
    z = z + model.relative_position_encoding(features['relp'])
    z = z + model.linear_no_bias_token_bond(features['token_bonds'].unsqueeze(-1))
    if 'constraint_feature' in features:
        constraint = model.constraint_embedder(features['constraint_feature'])
        if constraint is not None:
            z = z + constraint
    return RecycleInitialization(s_inputs, s, z)


def native_recycle_step(model, features, initialization, state, *, rng=None):
    """Exactly one native update, retaining autograd through the input state.

No input embedding, ESM, feature preparation or diffusion call. RNG is restored
at the continuation boundary when provided; callers may separately preserve
their ambient RNG. Inputs are never modified in place.
"""
    if model.training or model.train_confidence_only:
        raise ValueError('eval folding model required')
    s, z = state
    for actual, expected in zip(state, (initialization.single, initialization.pair)):
        if actual.shape != expected.shape or actual.dtype != expected.dtype or actual.device != expected.device:
            raise ValueError('prefix shape/dtype/device mismatch')
    if rng is not None:
        restore_rng_state(rng)
    options = dict(triangle_multiplicative=model.configs.triangle_multiplicative,
                   triangle_attention=model.configs.triangle_attention,
                   inplace_safe=False, chunk_size=None)
    z = initialization.pair + model.linear_no_bias_z_cycle(model.layernorm_z_cycle(z))
    if model.template_embedder.n_blocks > 0:
        z = z + model.template_embedder(features, z, **options)
    z = model.msa_module(features, z, initialization.inputs, pair_mask=None, **options)
    s = initialization.single + model.linear_no_bias_s(model.layernorm_s(s))
    return model.pairformer_stack(s, z, pair_mask=None, **options)


def capture_cached_prefix(model, features, initialization, depth=3):
    """Generate a reference prefix once; caller owns no-grad and RNG setup."""
    if depth < 1:
        raise ValueError('positive prefix depth required')
    state = (torch.zeros_like(initialization.single), torch.zeros_like(initialization.pair))
    for _ in range(depth):
        state = native_recycle_step(model, features, initialization, state)
    return tuple(x.detach().clone() for x in state), capture_rng_state()


class RecycleCompensator(nn.Module):
    """Global, hard-edit-conditioned residual before the last native recycle.

WT prefix and edit identity are the ONLY inputs. Dense pair correction is
generated in row chunks; there is no prescribed AA or spatial rank. Zero heads
start at the unmodified WT3→Target1 path. Native updates, not this network alone,
produce final conditioning. No-edit returns the original read-only tensors.
"""
    def __init__(self, c_s=384, c_z=128, width=256, pair_width=128, chunk=16):
        super().__init__()
        self.config = dict(c_s=c_s, c_z=c_z, width=width, pair_width=pair_width, chunk=chunk)
        self.chunk = chunk
        self.single = nn.Sequential(nn.LayerNorm(c_s), nn.Linear(c_s, width))
        self.relation = nn.Sequential(nn.LayerNorm(2*c_z), nn.Linear(2*c_z, width))
        self.aa = nn.Embedding(20, width)
        self.site = nn.Parameter(torch.randn(width)*.02)
        self.nodes = nn.ModuleList([
            nn.Sequential(nn.LayerNorm(width), nn.Linear(width, 4*width), nn.SiLU(), nn.Linear(4*width, width))
            for _ in range(2)])
        self.single_out = nn.Linear(width, c_s, bias=False)
        self.pair_base = nn.Sequential(nn.LayerNorm(c_z), nn.Linear(c_z, pair_width))
        self.left = nn.Linear(width, pair_width, bias=False)
        self.right = nn.Linear(width, pair_width, bias=False)
        self.pair_out = nn.Linear(pair_width, c_z, bias=False)
        nn.init.zeros_(self.single_out.weight)
        nn.init.zeros_(self.pair_out.weight)

    def forward(self, state, position, original, target):
        s, z = state
        if not 0 <= position < len(s) or not 0 <= original < 20 or not 0 <= target < 20:
            raise ValueError('invalid hard edit')
        if original == target:
            return state
        query = self.aa.weight[target] - self.aa.weight[original]
        relation = torch.cat((z[position], z[:, position]), dim=-1)
        flag = torch.zeros((len(s), 1), device=s.device, dtype=s.dtype)
        flag[position] = 1
        h = self.single(s) + self.relation(relation) + query + flag*self.site
        for block in self.nodes:
            h = h + block(h)
        ds = self.single_out(h)
        left, right = self.left(h), self.right(h)
        chunks = []
        for start in range(0, len(s), self.chunk):
            stop = min(start+self.chunk, len(s))
            u = self.pair_base(z[start:stop]) + left[start:stop, None] + right[None]
            chunks.append(self.pair_out(torch.nn.functional.silu(u)))
        return s + ds, z + torch.cat(chunks, dim=0)
