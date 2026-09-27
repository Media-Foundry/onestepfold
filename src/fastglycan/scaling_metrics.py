"""Fixed-correspondence observed lDDT and TM-align CA evaluation for scaling."""

import numpy as np
from scipy.spatial import cKDTree

from fastglycan.experimental_metrics import prediction_atom37
from onestepfold.data.gt_materializer import ATOM37_INDEX


def lddt_observed(predicted, target, residues, radius=15.0):
    """Per-atom mean of inter-residue observed-pair lDDT; excluded atoms counted."""
    x, y = np.asarray(predicted, dtype=np.float64), np.asarray(target, dtype=np.float64)
    residues = np.asarray(residues)
    if x.shape != y.shape or x.shape != (len(residues), 3):
        raise ValueError("coordinate/residue mismatch")
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("nonfinite observed coordinates")
    pairs = cKDTree(y).query_pairs(radius, output_type="ndarray")
    if len(pairs):
        reference = np.linalg.norm(y[pairs[:, 0]] - y[pairs[:, 1]], axis=1)
        keep = (reference < radius) & (residues[pairs[:, 0]] != residues[pairs[:, 1]])
        pairs, reference = pairs[keep], reference[keep]
    if not len(pairs):
        raise ValueError("no evaluable inter-residue lDDT pairs")
    error = np.abs(np.linalg.norm(x[pairs[:, 0]] - x[pairs[:, 1]], axis=1) - reference)
    score = np.mean(error[:, None] < np.array([0.5, 1.0, 2.0, 4.0]), axis=1)
    counts = np.bincount(pairs.ravel(), minlength=len(x))
    totals = np.bincount(pairs.ravel(), weights=np.repeat(score, 2), minlength=len(x))
    valid = counts > 0
    return {
        "score": float(np.mean(totals[valid] / counts[valid])),
        "pairs": len(pairs),
        "evaluable_atoms": int(valid.sum()),
        "atoms_without_neighbors": int((~valid).sum()),
    }


def quality_metrics(prediction, arrays, sequence):
    from tmtools import tm_align

    positions, predicted = prediction_atom37(prediction, sequence)
    mask = predicted & arrays["atom37_mask"] & arrays["residue_mask"][:, None]
    ri, _ = np.nonzero(mask)
    allatom = lddt_observed(positions[mask], arrays["atom37_positions"][mask], ri)
    ca = mask[:, ATOM37_INDEX["CA"]]
    x = np.asarray(positions[ca, ATOM37_INDEX["CA"]], dtype=np.float64)
    y = np.asarray(arrays["atom37_positions"][ca, ATOM37_INDEX["CA"]], dtype=np.float64)
    if len(x) < 3:
        raise ValueError("fewer than three observed CA")
    ca_lddt = lddt_observed(x, y, np.flatnonzero(ca))
    seq = "".join(a for a, keep in zip(sequence, ca, strict=True) if keep)
    # Fix sequence correspondence, while optimizing the TM-score superposition.
    tm = tm_align(x, y, seq, seq, alignment=[seq, seq])
    value = float(tm.tm_norm_chain2)
    assert 0 <= value <= 1 + 1e-8
    return {
        "all_atom_lddt": allatom["score"],
        "ca_lddt": ca_lddt["score"],
        "tm_score_ca_observed": value,
        "tm_normalization_ca_count": len(x),
        "ca_coverage": len(x) / len(sequence),
        "lddt_details": allatom,
    }


def summarize_quality(rows):
    result = {}
    for seed in (12345, 54321):
        part = [r for r in rows if r["noise"] == seed]
        if not part:
            raise ValueError("both noise evaluations required")
        result[str(seed)] = {
            "proteins": len(part),
            **{
                key: float(np.mean([r["quality"][key] for r in part]))
                for key in ("all_atom_lddt", "ca_lddt", "tm_score_ca_observed")
            },
            **{
                key: float(np.mean([r["metrics"][key] for r in part]))
                for key in ("all_heavy_atom_rmsd", "ca_pair_distance_rmse")
            },
        }
    return {
        "conditions": result,
        "selection_score": min(r["all_atom_lddt"] for r in result.values()),
    }
