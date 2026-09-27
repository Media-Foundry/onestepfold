# Adapted from Protenix, Copyright 2024 ByteDance and/or its affiliates.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# https://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Explicit full-recycle derivative path, adapted from Protenix (Apache-2.0).

Fixed-chemical-graph conditioning diagnostic, NOT a complete soft-sequence oracle.
Source: archived protenix/model/protenix.py; only recycle autograd guard changed.
Original source SHA256: c4250bd93d592a11d9019285cfd84b71b26fa6a8aca6944a239fb31e0337e179
"""
from typing import Any, Optional
import torch
import torch.nn.functional as F

def full_recycle_pairformer(
    self,
    input_feature_dict: dict[str, Any],
    N_cycle: int,
    inplace_safe: bool = False,
    chunk_size: Optional[int] = None,
    mc_dropout: bool = False,
    mc_dropout_rate: float = 0.4,
) -> tuple[torch.Tensor, ...]:
    """
    The forward pass from the input to pairformer output

    Args:
        input_feature_dict (dict[str, Any]): input features
        N_cycle (int): number of cycles
        inplace_safe (bool): Whether it is safe to use inplace operations. Defaults to False.
        chunk_size (Optional[int]): Chunk size for memory-efficient operations. Defaults to None.

    Returns:
        Tuple[torch.Tensor, ...]: s_inputs, s, z
    """
    if self.train_confidence_only:
        self.input_embedder.eval()
        self.template_embedder.eval()
        self.msa_module.eval()
        self.pairformer_stack.eval()

    # Line 1-5
    s_inputs = self.input_embedder(
        input_feature_dict, inplace_safe=False, chunk_size=chunk_size
    )  # [..., N_token, 449]
    z_constraint = None

    if "constraint_feature" in input_feature_dict:
        z_constraint = self.constraint_embedder(
            input_feature_dict["constraint_feature"]
        )

    s_init = self.linear_no_bias_sinit(s_inputs)  # [..., N_token, c_s]
    z_init = (
        self.linear_no_bias_zinit1(s_init)[..., None, :]
        + self.linear_no_bias_zinit2(s_init)[..., None, :, :]
    )  # [..., N_token, N_token, c_z]
    if inplace_safe:
        z_init += self.relative_position_encoding(input_feature_dict["relp"])
        z_init += self.linear_no_bias_token_bond(
            input_feature_dict["token_bonds"].unsqueeze(dim=-1)
        )
        if z_constraint is not None:
            z_init += z_constraint
    else:
        z_init = z_init + self.relative_position_encoding(
            input_feature_dict["relp"]
        )
        z_init = z_init + self.linear_no_bias_token_bond(
            input_feature_dict["token_bonds"].unsqueeze(dim=-1)
        )
        if z_constraint is not None:
            z_init = z_init + z_constraint
    # Line 6
    z = torch.zeros_like(z_init)
    s = torch.zeros_like(s_init)

    # Line 7-13 recycling
    for cycle_no in range(N_cycle):
        with torch.set_grad_enabled(
            torch.is_grad_enabled()
        ):
            if mc_dropout:
                z = z_init + F.dropout(
                    self.linear_no_bias_z_cycle(self.layernorm_z_cycle(z)),
                    p=self.configs.mc_dropout_rate,
                )
            else:
                z = z_init + self.linear_no_bias_z_cycle(self.layernorm_z_cycle(z))
            if inplace_safe:
                if self.template_embedder.n_blocks > 0:
                    z += self.template_embedder(
                        input_feature_dict,
                        z,
                        triangle_multiplicative=self.configs.triangle_multiplicative,
                        triangle_attention=self.configs.triangle_attention,
                        inplace_safe=inplace_safe,
                        chunk_size=chunk_size,
                    )
                z = self.msa_module(
                    input_feature_dict,
                    z,
                    s_inputs,
                    pair_mask=None,
                    triangle_multiplicative=self.configs.triangle_multiplicative,
                    triangle_attention=self.configs.triangle_attention,
                    inplace_safe=inplace_safe,
                    chunk_size=chunk_size,
                )
            else:
                if self.template_embedder.n_blocks > 0:
                    z = z + self.template_embedder(
                        input_feature_dict,
                        z,
                        triangle_multiplicative=self.configs.triangle_multiplicative,
                        triangle_attention=self.configs.triangle_attention,
                        inplace_safe=inplace_safe,
                        chunk_size=chunk_size,
                    )
                z = self.msa_module(
                    input_feature_dict,
                    z,
                    s_inputs,
                    pair_mask=None,
                    triangle_multiplicative=self.configs.triangle_multiplicative,
                    triangle_attention=self.configs.triangle_attention,
                    inplace_safe=inplace_safe,
                    chunk_size=chunk_size,
                )
            s = s_init + self.linear_no_bias_s(self.layernorm_s(s))
            s, z = self.pairformer_stack(
                s,
                z,
                pair_mask=None,
                triangle_multiplicative=self.configs.triangle_multiplicative,
                triangle_attention=self.configs.triangle_attention,
                inplace_safe=inplace_safe,
                chunk_size=chunk_size,
            )

    if self.train_confidence_only:
        self.input_embedder.train()
        self.template_embedder.train()
        self.msa_module.train()
        self.pairformer_stack.train()

    return s_inputs, s, z


def fixed_graph_coordinates(model, features, initial_coordinate, *, steps=1, stable_euler=False):
    """C4/S1 or S2 with fixed noise, identity rotations and no dropout.

    Caller supplies device-resident prepared features (relp and atom caches).
    Float32 only for the first diagnostic. Does not detach any feature tensor.
    Model parameters must be frozen; ESM features may be differentiable.
    """
    if steps not in (1, 2):
        raise ValueError("diagnostic supports S1/S2 only")
    if model.training or model.train_confidence_only:
        raise ValueError("requires eval mode and ordinary folding model")
    if any(p.requires_grad for p in model.parameters()):
        raise ValueError("freeze model parameters before input differentiation")
    if initial_coordinate.dtype != torch.float32:
        raise ValueError("first diagnostic requires FP32")
    if any(m.training for m in model.modules()):
        raise ValueError("all modules must be in eval mode")
    s_inputs, s, z = full_recycle_pairformer(
        model, features, N_cycle=4, inplace_safe=False, chunk_size=None,
        mc_dropout=False)
    module = model.diffusion_module
    pair_z = module.diffusion_conditioning.prepare_cache(features['relp'], z, False)
    names = ('ref_pos', 'ref_charge', 'ref_mask', 'ref_element',
             'ref_atom_name_chars', 'atom_to_token_idx', 'd_lm', 'v_lm', 'pad_info')
    p_lm, c_l = module.atom_attention_encoder.prepare_cache(
        **{k: features[k] for k in names}, r_l=True, z=pair_z, inplace_safe=False)
    schedule = model.inference_noise_scheduler(
        N_step=steps, device=s.device, dtype=s.dtype)
    x = initial_coordinate
    for sigma, next_sigma in zip(schedule[:-1], schedule[1:]):
        x = x - x.mean(-2, keepdim=True)
        denoised = module(
            x_noisy=x, t_hat_noise_level=sigma.expand(x.shape[:-2]),
            input_feature_dict=features, s_inputs=s_inputs, s_trunk=s,
            z_trunk=None, pair_z=pair_z, p_lm=p_lm, c_l=c_l,
            chunk_size=None, inplace_safe=False,
            enable_efficient_fusion=model.configs.enable_efficient_fusion)
        # Preserve native Euler arithmetic, including the last step.
        if stable_euler:
            x = denoised + (next_sigma / sigma) * (x - denoised)
        else:
            delta = (x - denoised) / sigma
            x = x + (next_sigma - sigma) * delta
    return x


def directional_check(function, point, direction, steps=(1e-1, 1e-2, 1e-3, 1e-4)):
    """Central differences of a deterministic scalar objective; no hidden RNG reset."""
    x = point.detach().clone().requires_grad_(True)
    v = direction.detach() / direction.norm().clamp_min(torch.finfo(direction.dtype).tiny)
    value = function(x)
    gradient, = torch.autograd.grad(value, x)
    analytic = (gradient * v).sum().item()
    rows = []
    with torch.no_grad():
        for h in steps:
            numerical = ((function(x + h*v) - function(x - h*v))/(2*h)).item()
            rows.append(dict(h=h, analytic=analytic, numerical=numerical,
                             absolute_error=abs(analytic-numerical),
                             relative_error=abs(analytic-numerical)/max(abs(analytic),abs(numerical),1e-12)))
    return gradient, rows


def prepare_atom_pairs(features):
    """Native reference-pair preparation without the upstream no_grad guard."""
    from protenix.model.modules.transformer import rearrange_qk_to_dense_trunk
    f = dict(features)
    q, k, pad_info = rearrange_qk_to_dense_trunk(
        q=[f['ref_pos'], f['ref_space_uid']],
        k=[f['ref_pos'], f['ref_space_uid']],
        dim_q=[-2,-1], dim_k=[-2,-1], n_queries=32, n_keys=128, compute_mask=True)
    f['d_lm'] = q[0][...,None,:] - k[0][...,None,:,:]
    f['v_lm'] = (q[1][...,None].int() == k[1][...,None,:].int()).unsqueeze(-1)
    f['pad_info'] = pad_info
    return f
