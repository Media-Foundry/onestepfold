"""Observed named-distance labels; never inputs or idealized chemical targets."""

from __future__ import annotations

import numpy as np
import torch

DISTANCE_CATEGORIES = ("N_CA", "CA_C", "C_O", "consecutive_C_N")


def build_distance_labels(labels, inventory):
    """Preserve the four existing geometry gate pair sets and observed masks.

    Consecutive residue IDs define C-N observations, not certified peptide bonds.
    No pair crosses an unrepresented residue ID and no absent atom is imputed.
    """
    target = labels["coordinate"].detach().cpu().double()
    mask = labels["coordinate_mask"].detach().cpu()
    if target.ndim != 2 or target.shape[-1] != 3:
        raise ValueError("expected [atom,3] coordinates")
    if mask.dtype != torch.bool or mask.shape != target.shape[:1]:
        raise ValueError("invalid observed mask")
    if not torch.isfinite(target[mask]).all():
        raise ValueError("nonfinite observed target")
    names, residues = np.asarray(inventory["atom_name"]), np.asarray(inventory["residue_id"])
    if names.shape != residues.shape or names.shape != (len(target),):
        raise ValueError("inventory shape mismatch")
    if not np.issubdtype(residues.dtype, np.integer) or np.any(residues < 1):
        raise ValueError("residue IDs must be positive integers")
    lookup = {(int(r), str(n)): i for i, (r, n) in enumerate(zip(residues, names, strict=True))}
    if len(lookup) != len(names):
        raise ValueError("duplicate atom identity")
    pairs, categories = [], []
    for category, (first, second, offset) in enumerate(
        (("N", "CA", 0), ("CA", "C", 0), ("C", "O", 0), ("C", "N", 1))
    ):
        for residue in np.unique(residues):
            i = lookup.get((int(residue), first))
            j = lookup.get((int(residue) + offset, second))
            if i is not None and j is not None and bool(mask[i] & mask[j]):
                pairs.append([i, j])
                categories.append(category)
    if not pairs:
        raise ValueError("no observed named-distance pairs")
    pairs = torch.tensor(pairs, dtype=torch.long)
    return {
        "pairs": pairs,
        "category": torch.tensor(categories, dtype=torch.long),
        "target_distance": (target[pairs[:, 0]] - target[pairs[:, 1]]).norm(dim=-1),
    }


def observed_distance_mse(prediction, supervision):
    """Equal-category mean of distance MSEs in Å²; omit empty categories.

    Standard norm uses its zero subgradient for exactly coincident predictions.
    No smoothing, pair removal or target length replacement is performed.
    """
    if prediction.ndim != 2 or prediction.shape[-1] != 3:
        raise ValueError("expected [atom,3] prediction")
    x = prediction if prediction.dtype == torch.float64 else prediction.float()
    pairs = supervision["pairs"].to(x.device)
    category = supervision["category"].to(x.device)
    target = supervision["target_distance"].to(device=x.device, dtype=x.dtype).detach()
    distances = (x[pairs[:, 0]] - x[pairs[:, 1]]).norm(dim=-1)
    errors = (distances - target).square()
    return torch.stack([errors[category == c].mean() for c in category.unique()]).mean()
