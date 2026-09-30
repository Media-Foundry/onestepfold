"""Sparse observed-atom smooth-lDDT supervision for the scratch folding core.

The neighborhood and reduction match ``scaling_metrics.lddt_observed``: target
distances strictly below 15 A, different residues, an average over each atom's
neighbors followed by an average over atoms that have neighbors. This is not a
uniform average over pairs. The sigmoid surrogate is a training loss, not the
reported hard-threshold lDDT metric. Even perfect coordinates have a small
positive surrogate loss at the fixed temperature of 0.1 A.
"""

from __future__ import annotations

import numpy as np
import torch
import math
from scipy.spatial import cKDTree

RADIUS = 15.0
THRESHOLDS = (0.5, 1.0, 2.0, 4.0)
TEMPERATURE = 0.1


def build_smooth_lddt_labels(labels, inventory):
    """Prepare detached CPU labels from the observed heavy-atom inventory.

    Unobserved coordinates are excluded before distance or finite-value checks.
    Missing labels are never replaced by reference coordinates. Unordered-pair
    weights implement the per-atom mean without a GPU scatter-add operation,
    keeping backward compatible with deterministic CUDA execution. An empty
    neighborhood is represented explicitly; it contributes zero loss.
    """
    target = labels["coordinate"].detach().cpu().double()
    mask = labels["coordinate_mask"].detach().cpu()
    if target.ndim != 2 or target.shape[-1] != 3:
        raise ValueError("expected [atom,3] coordinates")
    if mask.dtype != torch.bool or mask.shape != target.shape[:1]:
        raise ValueError("invalid observed mask")
    if not torch.isfinite(target[mask]).all():
        raise ValueError("nonfinite observed target")
    names = np.asarray(inventory["atom_name"])
    residues = np.asarray(inventory["residue_id"])
    if names.shape != residues.shape or residues.shape != (len(target),):
        raise ValueError("inventory shape mismatch")
    if not np.issubdtype(residues.dtype, np.integer) or np.any(residues < 1):
        raise ValueError("residue IDs must be positive integers")
    if len(set(zip(residues.tolist(), names.tolist(), strict=True))) != len(target):
        raise ValueError("duplicate atom identity")

    observed = np.flatnonzero(mask.numpy())
    points = target.numpy()[observed]
    local_pairs = cKDTree(points).query_pairs(RADIUS, output_type="ndarray")
    pairs = observed[local_pairs]
    distance = np.linalg.norm(points[local_pairs[:, 0]] - points[local_pairs[:, 1]], axis=1)
    keep = (distance < RADIUS) & (residues[pairs[:, 0]] != residues[pairs[:, 1]])
    pairs, distance = pairs[keep], distance[keep]
    # Explicit ordering pins labels independently of the spatial-tree traversal.
    order = np.lexsort((pairs[:, 1], pairs[:, 0]))
    pairs, distance = pairs[order], distance[order]
    counts = np.bincount(pairs.ravel(), minlength=len(target))
    evaluable_atoms = int(np.count_nonzero(counts))
    if evaluable_atoms:
        weight = (1.0 / counts[pairs[:, 0]] + 1.0 / counts[pairs[:, 1]]) / evaluable_atoms
    else:
        weight = np.empty(0, dtype=np.float64)
    return {
        "pairs": torch.from_numpy(pairs.astype(np.int64, copy=False)),
        "target_distance": torch.from_numpy(distance),
        "pair_weight": torch.from_numpy(weight),
        "neighbor_count": torch.from_numpy(counts.astype(np.int64, copy=False)),
        "evaluable_atoms": torch.tensor(evaluable_atoms, dtype=torch.long),
    }


def smooth_lddt_loss(prediction, labels, *, temperature=TEMPERATURE):
    """Return one minus sigmoid lDDT; the historical default remains 0.1 A.

    Only distances along the precomputed sparse pair list enter autograd; no
    dense atom-by-atom distance matrix is formed. FP64 inputs retain FP64 for
    gradient checks; other floating inputs are evaluated in FP32. Absolute
    distance errors use PyTorch's zero subgradient at an exact match. Very large
    errors saturate, so this term is an auxiliary to coordinate/geometry losses.
    """
    if prediction.ndim != 2 or prediction.shape[-1] != 3:
        raise ValueError("expected [atom,3] prediction")
    if not math.isfinite(temperature) or temperature <= 0:
        raise ValueError("temperature must be finite and positive")
    if not prediction.is_floating_point():
        raise ValueError("prediction must have floating-point coordinates")
    if labels["neighbor_count"].shape != prediction.shape[:1]:
        raise ValueError("prediction/label atom count mismatch")
    with torch.autocast(device_type=prediction.device.type, enabled=False):
        x = prediction if prediction.dtype == torch.float64 else prediction.float()
        if not len(labels["pairs"]):
            # Summing an empty view preserves an autograd connection without
            # reading absent/isolated NaN coordinates or multiplying them by 0.
            return x[:0].sum()
        pairs = labels["pairs"].to(device=x.device)
        reference = labels["target_distance"].to(device=x.device, dtype=x.dtype).detach()
        weight = labels["pair_weight"].to(device=x.device, dtype=x.dtype).detach()
        delta = x[pairs[:, 0]] - x[pairs[:, 1]]
        if not torch.isfinite(delta).all():
            raise ValueError("nonfinite prediction in an evaluable pair")
        error = (delta.norm(dim=-1) - reference).abs()
        thresholds = x.new_tensor(THRESHOLDS)
        pair_score = torch.sigmoid((thresholds - error[:, None]) / temperature).mean(-1)
        return 1.0 - (weight * pair_score).sum()
