"""A small global coordinate-residual baseline for recycle emulation.

This module deliberately predicts C-alpha corrections only. It is a diagnostic
baseline for the c2 -> c4 teacher pairs, not an all-atom replacement for the
Protenix structure module. Corrections are predicted in a residue-local
backbone frame and transformed back to Cartesian coordinates, so a rigid
transform of the input structure produces the same rigid transform of the
prediction.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import Tensor, nn


@dataclass(frozen=True)
class CoordinateRefinerConfig:
    """Configuration for the intentionally small refiner baseline."""

    input_dim: int
    hidden_dim: int = 256
    confidence_dim: int = 0
    num_layers: int = 2
    num_heads: int = 8
    dropout: float = 0.0
    max_length: int = 1024
    max_delta_angstrom: float = 8.0

    def __post_init__(self) -> None:
        if self.input_dim < 1 or self.hidden_dim < 1:
            raise ValueError("input_dim and hidden_dim must be positive")
        if self.confidence_dim < 0:
            raise ValueError("confidence_dim cannot be negative")
        if self.num_layers < 0:
            raise ValueError("num_layers cannot be negative")
        if self.num_heads < 1 or self.hidden_dim % self.num_heads:
            raise ValueError("hidden_dim must be divisible by num_heads")
        if self.max_length < 1 or self.max_delta_angstrom <= 0:
            raise ValueError("max_length and max_delta_angstrom must be positive")


def _normalize(vector: Tensor, eps: float = 1e-6) -> Tensor:
    return vector / torch.linalg.vector_norm(vector, dim=-1, keepdim=True).clamp_min(eps)


def backbone_frames(backbone_positions: Tensor) -> tuple[Tensor, Tensor, Tensor]:
    """Return residue origins and local-to-global rotation matrices.

    ``backbone_positions`` is `[B,L,4,3]` in N, CA, C, O order. Missing or
    degenerate frames fall back to the identity rotation and are marked false.
    """
    if backbone_positions.ndim != 4 or backbone_positions.shape[-2:] != (4, 3):
        raise ValueError("backbone_positions must have shape [B,L,4,3]")
    n_atom = backbone_positions[..., 0, :]
    ca_atom = backbone_positions[..., 1, :]
    c_atom = backbone_positions[..., 2, :]
    x_raw = c_atom - ca_atom
    y_raw = n_atom - ca_atom
    x_norm = torch.linalg.vector_norm(x_raw, dim=-1)
    z_raw = torch.cross(x_raw, y_raw, dim=-1)
    z_norm = torch.linalg.vector_norm(z_raw, dim=-1)
    valid = (x_norm > 1e-5) & (z_norm > 1e-5) & torch.isfinite(
        backbone_positions
    ).all(dim=(-1, -2))
    x_axis = _normalize(x_raw)
    z_axis = _normalize(z_raw)
    y_axis = _normalize(torch.cross(z_axis, x_axis, dim=-1))
    rotation = torch.stack((x_axis, y_axis, z_axis), dim=-1)
    identity = torch.eye(3, device=backbone_positions.device, dtype=backbone_positions.dtype)
    rotation = torch.where(valid[..., None, None], rotation, identity)
    return ca_atom, rotation, valid


class GlobalCoordinateRefiner(nn.Module):
    """Global Transformer baseline that predicts local-frame CA corrections."""

    def __init__(self, config: CoordinateRefinerConfig) -> None:
        super().__init__()
        self.config = config
        feature_dim = config.input_dim + config.confidence_dim
        self.input_projection = nn.Linear(feature_dim, config.hidden_dim)
        self.position_embedding = nn.Embedding(config.max_length, config.hidden_dim)
        if config.num_layers:
            layer = nn.TransformerEncoderLayer(
                d_model=config.hidden_dim,
                nhead=config.num_heads,
                dim_feedforward=4 * config.hidden_dim,
                dropout=config.dropout,
                activation="gelu",
                batch_first=True,
                norm_first=True,
            )
            self.encoder: nn.Module = nn.TransformerEncoder(layer, config.num_layers)
        else:
            self.encoder = nn.Identity()
        self.output_norm = nn.LayerNorm(config.hidden_dim)
        self.output_projection = nn.Linear(config.hidden_dim, 3)

    def forward(
        self,
        residue_features: Tensor,
        backbone_positions: Tensor,
        residue_mask: Tensor,
        confidence: Tensor | None = None,
    ) -> dict[str, Tensor]:
        """Predict corrected CA coordinates and the applied residual.

        Inputs use `[B,L,*]` shapes. ``residue_mask`` is boolean; padded tokens
        are forced to have zero correction and are ignored by the Transformer.
        """
        if residue_features.ndim != 3:
            raise ValueError("residue_features must have shape [B,L,D]")
        batch, length, _ = residue_features.shape
        if length > self.config.max_length:
            raise ValueError(
                f"sequence length {length} exceeds max_length {self.config.max_length}"
            )
        if residue_mask.shape != (batch, length):
            raise ValueError("residue_mask must have shape [B,L]")
        if confidence is None:
            if self.config.confidence_dim:
                raise ValueError("confidence features are required by this configuration")
            confidence = residue_features.new_zeros(batch, length, 0)
        elif confidence.shape != (batch, length, self.config.confidence_dim):
            raise ValueError("confidence has an unexpected shape")
        features = torch.cat((residue_features, confidence), dim=-1)
        positions = torch.arange(length, device=features.device)
        hidden = self.input_projection(features) + self.position_embedding(positions)[None]
        if self.config.num_layers:
            hidden = self.encoder(hidden, src_key_padding_mask=~residue_mask.bool())
        else:
            hidden = self.encoder(hidden)
        local_delta = torch.tanh(self.output_projection(self.output_norm(hidden)))
        local_delta = local_delta * self.config.max_delta_angstrom
        ca_positions, rotation, frame_valid = backbone_frames(backbone_positions)
        global_delta = torch.einsum("blij,blj->bli", rotation, local_delta)
        active = residue_mask.bool() & frame_valid
        global_delta = global_delta * active[..., None]
        corrected_ca = ca_positions + global_delta
        return {
            "corrected_ca": corrected_ca,
            "delta_ca": global_delta,
            "local_delta_ca": local_delta * active[..., None],
            "frame_valid": frame_valid,
        }
