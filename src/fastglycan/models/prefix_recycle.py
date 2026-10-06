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

"""Eval-only native recycle continuation adapted from differentiable_mini.

Adds explicit token-state/RNG capture and restoration without changing native
bridge arithmetic. Each hard candidate rebuilds its own chemistry and inputs.
Original Protenix source SHA256:
c4250bd93d592a11d9019285cfd84b71b26fa6a8aca6944a239fb31e0337e179
"""
from typing import Any, Optional
import torch
import random
import numpy as np
import torch.nn.functional as F


def capture_rng_state():
    """Exact execution state; no seeds or candidate chemistry are substituted."""
    return dict(python=random.getstate(),numpy=np.random.get_state(),cpu=torch.get_rng_state().clone(),
                gpu=[x.clone() for x in torch.cuda.get_rng_state_all()] if torch.cuda.is_initialized() else [])


def restore_rng_state(state):
    random.setstate(state['python']);np.random.set_state(state['numpy']);torch.set_rng_state(state['cpu'])
    if state['gpu']:
        if len(state['gpu']) != torch.cuda.device_count():raise ValueError('RNG device count mismatch')
        torch.cuda.set_rng_state_all(state['gpu'])


def prefix_recycle_pairformer(
    self,
    input_feature_dict: dict[str, Any],
    N_cycle: int,
    inplace_safe: bool = False,
    chunk_size: Optional[int] = None,
    mc_dropout: bool = False,
    mc_dropout_rate: float = 0.4,
    initial_state=None,
    capture_cycles=(),
    snapshots=None,
    initial_rng=None,
    snapshot_rng=None,
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
    if self.training or mc_dropout:
        raise ValueError("prefix experiment requires eval mode and no MC dropout")
    if N_cycle < 1 or any(c < 1 or c > N_cycle for c in capture_cycles):
        raise ValueError("invalid cycle budget")
    if capture_cycles and snapshots is None:
        raise ValueError("snapshot output required")
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
    if initial_state is not None:
        if len(initial_state) != 2:
            raise ValueError("only token s/z can be restored")
        old_s, old_z = initial_state
        if old_s.shape != s.shape or old_z.shape != z.shape:
            raise ValueError("token state shape mismatch")
        if old_s.dtype != s.dtype or old_z.dtype != z.dtype or old_s.device != s.device or old_z.device != z.device:
            raise ValueError("state dtype/device mismatch")
        s, z = old_s.clone(), old_z.clone()

    if initial_rng is not None:
        if initial_state is None:raise ValueError("RNG continuation requires token state")
        restore_rng_state(initial_rng)

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

        if cycle_no + 1 in capture_cycles:
            snapshots[cycle_no + 1] = (s.detach().clone(), z.detach().clone())
            if snapshot_rng is not None:
                snapshot_rng[cycle_no + 1] = capture_rng_state()

    if self.train_confidence_only:
        self.input_embedder.train()
        self.template_embedder.train()
        self.msa_module.train()
        self.pairformer_stack.train()

    return s_inputs, s, z
