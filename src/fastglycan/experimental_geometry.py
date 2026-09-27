"""Observed-GT local geometry diagnostics, independent of model selection."""
from __future__ import annotations

import numpy as np

from fastglycan.experimental_metrics import prediction_atom37
from onestepfold.data.gt_materializer import ATOM37_INDEX


def compare_local_geometry(prediction, arrays, sequence):
    """Compare named local distances and CA signed volumes with experimental GT.

    Uses only observed matching atoms. Consecutive C-N distances are reported
    separately because observation alone does not prove an intact peptide bond.
    This is not complete stereochemical validation: side-chain bond/angle checks,
    alternative atom-name permutations and a chemical clash model are absent.
    """
    predicted, available = prediction_atom37(prediction, sequence)
    observed = arrays["atom37_mask"] & arrays["residue_mask"][:, None]
    if np.any(observed & ~available):
        raise ValueError("missing observed prediction atoms")
    x, y = predicted.astype(np.float64), arrays["atom37_positions"].astype(np.float64)
    if not np.isfinite(y[observed]).all():
        raise ValueError("nonfinite observed GT atoms")
    length = len(sequence)
    distances = {}
    for label, first, second, offset in (
        ("N_CA", "N", "CA", 0), ("CA_C", "CA", "C", 0), ("C_O", "C", "O", 0),
        ("consecutive_C_N", "C", "N", 1),
    ):
        a, b = ATOM37_INDEX[first], ATOM37_INDEX[second]
        left = np.arange(length - offset)
        right = left + offset
        keep = observed[left, a] & observed[right, b]
        left, right = left[keep], right[keep]
        pred_distance = np.linalg.norm(x[left, a] - x[right, b], axis=-1)
        gt_distance = np.linalg.norm(y[left, a] - y[right, b], axis=-1)
        error = pred_distance - gt_distance
        count = len(error)
        distances[label] = {
            "count": count, "squared_error_sum": float(np.sum(error ** 2)),
            "absolute_error_sum": float(np.sum(np.abs(error))),
            "rmse": float(np.sqrt(np.mean(error ** 2))) if count else None,
            "mae": float(np.mean(np.abs(error))) if count else None,
            "predicted_mean_distance": float(np.mean(pred_distance)) if count else None,
            "gt_mean_distance": float(np.mean(gt_distance)) if count else None,
            "gt_max_distance": float(np.max(gt_distance)) if count else None,
        }
    names = [ATOM37_INDEX[n] for n in ("N", "CA", "C", "CB")]
    keep = observed[:, names].all(axis=1)

    def volumes(positions):
        n, ca, c, cb = [positions[keep, i] for i in names]
        return np.einsum("ij,ij->i", np.cross(n - ca, c - ca), cb - ca)

    vx, vy = volumes(x), volumes(y)
    nondegenerate = np.abs(vy) > 1e-6
    vx, vy = vx[nondegenerate], vy[nondegenerate]
    degenerate = np.abs(vx) <= 1e-6
    opposite = (~degenerate) & (np.sign(vx) != np.sign(vy))
    return {
        "local_distances": distances,
        "ca_chirality": {
            "observed_count": int(keep.sum()), "gt_degenerate_count": int((~nondegenerate).sum()),
            "evaluable_count": len(vx), "predicted_degenerate_count": int(degenerate.sum()),
            "opposite_sign_count": int(opposite.sum()),
            "agreement_count": int((~(degenerate | opposite)).sum()),
        },
    }
