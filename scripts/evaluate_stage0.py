#!/usr/bin/env python3
"""Evaluate one Protenix Stage 0 setting against frozen Stage B GT.

The evaluator is deliberately CPU-friendly and uses only Gemmi, NumPy,
SciPy, and the frozen manifest/tar shards. Predictions and labels are matched
by exact sequence group and residue index; no sequence alignment is performed.
"""

from __future__ import annotations

import argparse
import gzip
import io
import json
import math
import tarfile
import time
from pathlib import Path
from typing import Any

import numpy as np

from onestepfold.data.gt_materializer import ATOM37_INDEX, ATOM37_NAMES, BACKBONE_NAMES


def _quantiles(values: list[float]) -> dict[str, float | None]:
    finite = sorted(float(value) for value in values if math.isfinite(float(value)))
    if not finite:
        return {"mean": None, "median": None, "p05": None, "p25": None, "p75": None, "p95": None}
    return {
        "mean": float(np.mean(finite)),
        "median": float(np.median(finite)),
        **{
            f"p{int(fraction * 100):02d}": float(
                finite[min(len(finite) - 1, round(fraction * (len(finite) - 1)))]
            )
            for fraction in (0.05, 0.25, 0.75, 0.95)
        },
    }


def _kabsch(pred: np.ndarray, true: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    pred_center = pred.mean(axis=0)
    true_center = true.mean(axis=0)
    pred_centered = pred - pred_center
    true_centered = true - true_center
    covariance = pred_centered.T @ true_centered
    left, _, right_transpose = np.linalg.svd(covariance)
    rotation = left @ right_transpose
    if np.linalg.det(rotation) < 0:
        left[:, -1] *= -1
        rotation = left @ right_transpose
    aligned = pred_centered @ rotation + true_center
    return aligned, rotation


def _tm_score(pred: np.ndarray, true: np.ndarray) -> float:
    aligned, _ = _kabsch(pred, true)
    distances = np.linalg.norm(aligned - true, axis=1)
    length = len(distances)
    d0 = max(0.5, 1.24 * (length - 15) ** (1 / 3) - 1.8) if length > 15 else 0.5
    return float(np.mean(1.0 / (1.0 + (distances / d0) ** 2)))


def _rmsd(pred: np.ndarray, true: np.ndarray) -> tuple[float, np.ndarray]:
    aligned, _ = _kabsch(pred, true)
    return float(np.sqrt(np.mean(np.sum((aligned - true) ** 2, axis=1)))), aligned


def _lddt(pred: np.ndarray, true: np.ndarray, radius: float = 15.0) -> tuple[float, int]:
    """Return lDDT and number of reference atom pairs within radius."""
    if len(true) < 2:
        return float("nan"), 0
    from scipy.spatial import cKDTree

    pairs = cKDTree(true).query_pairs(radius, output_type="ndarray")
    if len(pairs) == 0:
        return float("nan"), 0
    true_distance = np.linalg.norm(true[pairs[:, 0]] - true[pairs[:, 1]], axis=1)
    pred_distance = np.linalg.norm(pred[pairs[:, 0]] - pred[pairs[:, 1]], axis=1)
    error = np.abs(pred_distance - true_distance)
    score = (
        (error < 0.5).astype(np.float32)
        + (error < 1.0).astype(np.float32)
        + (error < 2.0).astype(np.float32)
        + (error < 4.0).astype(np.float32)
    )
    return float(np.mean(score) * 0.25), int(len(pairs))


def _read_prediction(path: Path, length: int) -> tuple[np.ndarray, np.ndarray]:
    import gemmi

    positions = np.zeros((length, len(ATOM37_NAMES), 3), dtype=np.float32)
    mask = np.zeros((length, len(ATOM37_NAMES)), dtype=bool)
    structure = gemmi.read_structure(str(path))
    if len(structure) == 0 or len(structure[0]) == 0:
        raise ValueError("prediction has no model/chain")
    # Stage 0 is monomer-only. Select the first polymer chain and retain the
    # residue index from the emitted CIF, which is expected to be 1..L.
    chain = next(iter(structure[0]))
    for fallback_index, residue in enumerate(chain):
        index = int(residue.seqid.num) - 1
        if not 0 <= index < length:
            index = fallback_index
        for atom in residue:
            name = str(atom.name).strip().upper()
            atom_index = ATOM37_INDEX.get(name)
            if atom_index is None or atom.element.name.upper() == "H":
                continue
            if mask[index, atom_index]:
                continue
            position = atom.pos
            values = (float(position.x), float(position.y), float(position.z))
            if not np.isfinite(values).all():
                continue
            positions[index, atom_index] = values
            mask[index, atom_index] = True
    return positions, mask


def _read_gt(row: dict[str, Any], archives: dict[str, tarfile.TarFile]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    shard = str(row["shard"])
    archive = archives.get(shard)
    if archive is None:
        archive = tarfile.open(shard, "r")
        archives[shard] = archive
    payload = archive.extractfile(str(row["npz"]))
    if payload is None:
        raise FileNotFoundError(f"missing GT member {row['npz']} in {shard}")
    with np.load(io.BytesIO(payload.read())) as arrays:
        positions = np.asarray(arrays["atom37_positions"], dtype=np.float32)
        mask = np.asarray(arrays["atom37_mask"], dtype=bool)
        residue_mask = np.asarray(arrays["residue_mask"], dtype=bool)
    return positions, mask, residue_mask


def evaluate_row(row: dict[str, Any], prediction_root: Path, setting: str, archives: dict[str, tarfile.TarFile]) -> dict[str, Any]:
    group_id = str(row["group_id"])
    length = int(row["sequence_length"])
    prediction = prediction_root / setting / "seed-101" / group_id / "seed_101" / "predictions" / f"{group_id}_sample_0.cif"
    result: dict[str, Any] = {
        "group_id": group_id,
        "pdb_id": str(row["pdb_id"]),
        "sequence_length": length,
        "prediction_path": str(prediction),
    }
    try:
        true_positions, true_mask, residue_mask = _read_gt(row, archives)
        pred_positions, pred_mask = _read_prediction(prediction, length)
        ca_index = ATOM37_INDEX["CA"]
        common_ca = true_mask[:, ca_index] & pred_mask[:, ca_index] & residue_mask
        if int(common_ca.sum()) < 3:
            raise ValueError("fewer than three common CA atoms")
        true_ca = true_positions[common_ca, ca_index]
        pred_ca = pred_positions[common_ca, ca_index]
        ca_rmsd, aligned_ca = _rmsd(pred_ca, true_ca)
        common_atoms = true_mask & pred_mask & residue_mask[:, None]
        true_atoms = true_positions[common_atoms]
        pred_atoms = pred_positions[common_atoms]
        _, rotation = _kabsch(pred_ca, true_ca)
        pred_center = pred_ca.mean(axis=0)
        true_center = true_ca.mean(axis=0)
        aligned_atoms = (pred_positions - pred_center) @ rotation + true_center
        aligned_backbone = aligned_atoms[common_atoms]
        true_backbone = true_positions[common_atoms]
        backbone_atom_indices = [ATOM37_INDEX[name] for name in BACKBONE_NAMES]
        backbone_mask = np.zeros_like(common_atoms)
        backbone_mask[:, backbone_atom_indices] = common_atoms[:, backbone_atom_indices]
        backbone_pred = aligned_atoms[backbone_mask]
        backbone_true = true_positions[backbone_mask]
        sidechain_mask = common_atoms.copy()
        sidechain_mask[:, backbone_atom_indices] = False
        sidechain_pred = aligned_atoms[sidechain_mask]
        sidechain_true = true_positions[sidechain_mask]
        ca_lddt, ca_pairs = _lddt(pred_ca, true_ca)
        all_atom_lddt, all_atom_pairs = _lddt(pred_atoms, true_atoms)
        result.update(
            {
                "status": "ok",
                "common_ca_count": int(common_ca.sum()),
                "common_atom_count": int(common_atoms.sum()),
                "gt_atom_count": int((true_mask & residue_mask[:, None]).sum()),
                "tm_score_ca": _tm_score(pred_ca, true_ca),
                "ca_rmsd_angstrom": ca_rmsd,
                "backbone_rmsd_angstrom": float(np.sqrt(np.mean(np.sum((backbone_pred - backbone_true) ** 2, axis=1)))) if len(backbone_true) else float("nan"),
                "sidechain_rmsd_angstrom": float(np.sqrt(np.mean(np.sum((sidechain_pred - sidechain_true) ** 2, axis=1)))) if len(sidechain_true) else float("nan"),
                "ca_lddt": ca_lddt,
                "all_atom_lddt": all_atom_lddt,
                "ca_lddt_pair_count": ca_pairs,
                "all_atom_lddt_pair_count": all_atom_pairs,
                "pred_atom_coverage_on_gt": float(common_atoms.sum() / max(1, (true_mask & residue_mask[:, None]).sum())),
                "aligned_atoms_unused": int(aligned_backbone.shape[0]),
            }
        )
    except Exception as exc:  # keep one malformed target from hiding others
        result.update({"status": "error", "error": f"{type(exc).__name__}: {exc}"})
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--prediction-root", type=Path, required=True)
    parser.add_argument("--setting", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    started = time.time()
    rows: list[dict[str, Any]] = []
    with gzip.open(args.manifest, "rt", encoding="utf-8") as handle:
        for line in handle:
            rows.append(json.loads(line))
    if args.limit is not None:
        rows = rows[: args.limit]
    archives: dict[str, tarfile.TarFile] = {}
    records: list[dict[str, Any]] = []
    try:
        for index, row in enumerate(rows, start=1):
            records.append(evaluate_row(row, args.prediction_root, args.setting, archives))
            if index % 100 == 0:
                print(f"{args.setting}: evaluated {index}/{len(rows)}", flush=True)
    finally:
        for archive in archives.values():
            archive.close()
    ok = [record for record in records if record.get("status") == "ok"]
    metrics = ["tm_score_ca", "ca_rmsd_angstrom", "backbone_rmsd_angstrom", "sidechain_rmsd_angstrom", "ca_lddt", "all_atom_lddt"]
    summary = {
        "setting": args.setting,
        "manifest_count": len(rows),
        "ok_count": len(ok),
        "error_count": len(records) - len(ok),
        "elapsed_seconds": time.time() - started,
        "metrics": {metric: _quantiles([float(record[metric]) for record in ok]) for metric in metrics},
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in summary.items() if key != "records"}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
