"""Versioned normalization of inference-available model confidence."""

from __future__ import annotations

import math

import torch
from torch import Tensor

C2_QUALITY_FEATURE_NAMES = ("ca_plddt_div100", "mean_plddt_div100", "ptm", "log1p_gpde")


def c2_quality_features(
    ca_plddt: Tensor, ca_mask: Tensor, *, mean_plddt: float, ptm: float, gpde: float
) -> Tensor:
    """Return [L,4] c2-only features; invalid CA positions remain masked zeros."""
    if ca_plddt.ndim != 1 or ca_mask.shape != ca_plddt.shape:
        raise ValueError("CA confidence and mask must have shape [L]")
    if not all(math.isfinite(value) for value in (mean_plddt, ptm, gpde)):
        raise ValueError("non-finite global confidence")
    if not (0 <= mean_plddt <= 100 and 0 <= ptm <= 1 and gpde >= 0):
        raise ValueError("confidence outside the declared range")
    mask = ca_mask.bool()
    valid_values = ca_plddt[mask]
    if not bool(
        torch.isfinite(valid_values).all() & (valid_values >= 0).all() & (valid_values <= 100).all()
    ):
        raise ValueError("invalid CA pLDDT")
    features = torch.stack(
        (
            torch.where(mask, ca_plddt.float(), 0.0) / 100.0,
            torch.full_like(ca_plddt, mean_plddt / 100.0, dtype=torch.float32),
            torch.full_like(ca_plddt, ptm, dtype=torch.float32),
            torch.full_like(ca_plddt, math.log1p(gpde), dtype=torch.float32),
        ),
        dim=-1,
    )
    return features * mask[:, None]
