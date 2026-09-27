"""Map unchanged observed atom37 labels onto a generated chemical inventory."""

from __future__ import annotations

import numpy as np
import torch

from fastglycan.experimental_metrics import prediction_atom37, validate_experimental_record
from onestepfold.data.gt_materializer import ATOM37_INDEX


def map_experimental_atoms(arrays, metadata, sequence, sample_id, inventory):
    """Return label coordinates/masks in atom order, with no missing-label imputation.

    ``inventory`` supplies atom_name, residue_id and element; generated reference
    coordinates are deliberately not an argument. Zero placeholders for absent
    observations are always accompanied by False masks.
    """
    validate_experimental_record(arrays, metadata, sequence, sample_id)
    names = np.asarray(inventory["atom_name"])
    check = dict(inventory) | {"coordinate": np.zeros((len(names), 3), dtype=np.float32)}
    _, available = prediction_atom37(check, sequence)
    observed = arrays["atom37_mask"] & arrays["residue_mask"][:, None]
    if np.any(observed & ~available):
        raise ValueError("generated atom inventory is missing observed experimental atoms")
    residues = np.asarray(inventory["residue_id"], dtype=np.int64) - 1
    columns = np.array([ATOM37_INDEX[str(name)] for name in names])
    mask = observed[residues, columns].copy()
    if not mask.any():
        raise ValueError("no observed experimental atoms")
    coordinate = np.zeros((len(names), 3), dtype=np.float32)
    coordinate[mask] = arrays["atom37_positions"][residues[mask], columns[mask]]
    return {"coordinate": torch.from_numpy(coordinate), "coordinate_mask": torch.from_numpy(mask)}


def observed_aligned_mse(prediction, target, mask):
    """Observed-atom mean squared Euclidean error after a proper rigid alignment.

    Fit target to detached predictions in FP64, without scaling or reflections.
    Differentiation only through predictions avoids unstable SVD derivatives;
    at a regular optimum this is the derivative of the minimized objective.
    Missing entries are excluded before all arithmetic, including finite checks.
    Atom identities are fixed: no side-chain symmetry renaming is performed.
    """
    if prediction.ndim != 2 or prediction.shape[-1] != 3 or target.shape != prediction.shape:
        raise ValueError("expected matching [atom, 3] coordinate arrays")
    if mask.dtype != torch.bool or mask.shape != prediction.shape[:1] or mask.sum() < 3:
        raise ValueError("expected boolean mask with at least three observed atoms")
    x, y = prediction[mask].double(), target[mask].detach().double()
    if not torch.isfinite(x).all() or not torch.isfinite(y).all():
        raise ValueError("nonfinite observed coordinates")
    with torch.no_grad():
        xc, yc = x.detach().mean(0), y.mean(0)
        u, _, vh = torch.linalg.svd((y - yc).T @ (x.detach() - xc))
        sign = torch.ones(3, dtype=x.dtype, device=x.device)
        sign[-1] = torch.where(torch.linalg.det(u @ vh) < 0, -1.0, 1.0)
        aligned = (y - yc) @ (u * sign) @ vh + xc
    return (x - aligned).square().sum(-1).mean()
