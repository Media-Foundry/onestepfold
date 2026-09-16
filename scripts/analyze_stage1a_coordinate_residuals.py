#!/usr/bin/env python3
"""Analyze c2_s2 to c4_s2 coordinate residuals on temporal_dev_v1."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np


def read_ca(path: Path, length: int) -> np.ndarray:
    import gemmi

    coordinates = np.full((length, 3), np.nan, dtype=np.float32)
    structure = gemmi.read_structure(str(path))
    chain = next(iter(structure[0]))
    for fallback_index, residue in enumerate(chain):
        index = int(residue.seqid.num) - 1
        if not 0 <= index < length:
            index = fallback_index
        atom = next((item for item in residue if str(item.name).strip().upper() == "CA"), None)
        if atom is not None:
            coordinates[index] = (atom.pos.x, atom.pos.y, atom.pos.z)
    if not np.isfinite(coordinates).all():
        raise ValueError(f"missing CA coordinates: {path}")
    return coordinates


def kabsch(left: np.ndarray, right: np.ndarray) -> tuple[np.ndarray, float]:
    left_centered = left - left.mean(axis=0)
    right_centered = right - right.mean(axis=0)
    u, _, vt = np.linalg.svd(left_centered.T @ right_centered)
    rotation = u @ vt
    if np.linalg.det(rotation) < 0:
        u[:, -1] *= -1
        rotation = u @ vt
    aligned = left_centered @ rotation
    residual = aligned - right_centered
    return residual, float(np.sqrt(np.mean(np.sum(residual**2, axis=1))))


def pair_distances(coordinates: np.ndarray) -> np.ndarray:
    from scipy.spatial.distance import pdist

    return np.asarray(pdist(coordinates), dtype=np.float32)


def summarize(values: list[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64)
    return {
        "mean": float(np.mean(array)),
        "median": float(np.median(array)),
        "p05": float(np.quantile(array, 0.05)),
        "p95": float(np.quantile(array, 0.95)),
    }


def analyze(c2_eval: Path, c4_eval: Path) -> dict[str, Any]:
    c2 = json.loads(c2_eval.read_text(encoding="utf-8"))["records"]
    c4 = json.loads(c4_eval.read_text(encoding="utf-8"))["records"]
    c2 = {str(row["group_id"]): row for row in c2 if row.get("status") == "ok"}
    c4 = {str(row["group_id"]): row for row in c4 if row.get("status") == "ok"}
    rows = []
    for group_id in sorted(set(c2) & set(c4)):
        row2, row4 = c2[group_id], c4[group_id]
        length = int(row2["sequence_length"])
        coord2 = read_ca(Path(row2["prediction_path"]), length)
        coord4 = read_ca(Path(row4["prediction_path"]), length)
        aligned_residual, kabsch_rmsd = kabsch(coord2, coord4)
        displacement = np.linalg.norm(aligned_residual, axis=1)
        distance_delta = pair_distances(coord2) - pair_distances(coord4)
        distance_rmsd = float(np.sqrt(np.mean(distance_delta**2)))
        pair_index = np.triu_indices(length, k=1)
        index_distance = pair_index[1] - pair_index[0]
        distance_energy = distance_delta**2
        distance_total = max(float(np.sum(distance_energy)), 1e-8)
        displacement_energy = displacement**2
        displacement_total = max(float(np.sum(displacement_energy)), 1e-8)
        active = displacement > 1.0
        runs = []
        start = None
        for position, is_active in enumerate(active):
            if is_active and start is None:
                start = position
            elif not is_active and start is not None:
                runs.append(position - start)
                start = None
        if start is not None:
            runs.append(length - start)
        c2_tm = float(row2["tm_score_ca"])
        c4_tm = float(row4["tm_score_ca"])
        c2_lddt = float(row2["all_atom_lddt"])
        c4_lddt = float(row4["all_atom_lddt"])
        rows.append(
            {
                "group_id": group_id,
                "length": length,
                "kabsch_ca_rmsd": kabsch_rmsd,
                "pair_distance_rmsd": distance_rmsd,
                "residual_mean": float(np.mean(displacement)),
                "residual_p90": float(np.quantile(displacement, 0.90)),
                "residual_active_fraction": float(np.mean(displacement > 1.0)),
                "residual_top10_energy_fraction": float(
                    np.sort(displacement_energy)[-max(1, min(10, length)) :].sum()
                    / displacement_total
                ),
                "residual_top25_energy_fraction": float(
                    np.sort(displacement_energy)[-max(1, min(25, length)) :].sum()
                    / displacement_total
                ),
                "residual_active_run_max": float(max(runs, default=0)),
                "pair_distance_energy_band_8_fraction": float(
                    distance_energy[index_distance <= 8].sum() / distance_total
                ),
                "pair_distance_energy_band_16_fraction": float(
                    distance_energy[index_distance <= 16].sum() / distance_total
                ),
                "delta_c2_vs_c4_tm": c2_tm - c4_tm,
                "delta_c2_vs_c4_all_atom_lddt": c2_lddt - c4_lddt,
                "joint_hard_vs_c4s5": bool(c2_tm - c4_tm < -0.05 or c2_lddt - c4_lddt < -0.05),
            }
        )
    result = {
        "scope": "temporal_dev_v1 only; frozen temporal test was not read",
        "record_count": len(rows),
        "rows": rows,
        "all": {
            field: summarize([float(row[field]) for row in rows])
            for field in (
                "kabsch_ca_rmsd",
                "pair_distance_rmsd",
                "residual_mean",
                "residual_p90",
                "residual_active_fraction",
                "residual_top10_energy_fraction",
                "residual_top25_energy_fraction",
                "residual_active_run_max",
                "pair_distance_energy_band_8_fraction",
                "pair_distance_energy_band_16_fraction",
            )
        },
    }
    for subgroup, selected in (
        ("hard", [row for row in rows if row["joint_hard_vs_c4s5"]]),
        ("nonhard", [row for row in rows if not row["joint_hard_vs_c4s5"]]),
    ):
        result[subgroup] = {"record_count": len(selected)}
        result[subgroup].update(
            {
                field: summarize([float(row[field]) for row in selected])
                for field in (
                    "kabsch_ca_rmsd",
                    "pair_distance_rmsd",
                    "residual_mean",
                    "residual_p90",
                    "residual_active_fraction",
                    "residual_top10_energy_fraction",
                    "residual_top25_energy_fraction",
                    "residual_active_run_max",
                    "pair_distance_energy_band_8_fraction",
                    "pair_distance_energy_band_16_fraction",
                )
            }
        )
    return result


def write_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Stage 1A Coordinate Residuals",
        "",
        result["scope"] + ".",
        "",
        (
            f"Records: {result['record_count']}; joint-hard subgroup: "
            f"{result['hard']['record_count']}."
        ),
        (
            "This compares standalone c2_s2 and c4_s2 predictions; it is not an "
            "in-forward hidden-state residual."
        ),
        "",
        "| subgroup | count | Kabsch Cα RMSD median | pair-distance RMSD median | "
        "residue p90 | active fraction | top-10 energy | pair local <=8 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for subgroup in ("all", "hard", "nonhard"):
        data = result[subgroup]
        lines.append(
            f"| {subgroup} | {data.get('record_count', result['record_count'])} | "
            f"{data['kabsch_ca_rmsd']['median']:.4f} | "
            f"{data['pair_distance_rmsd']['median']:.4f} | "
            f"{data['residual_p90']['median']:.4f} | "
            f"{data['residual_active_fraction']['median']:.4f} |"
            f" {data['residual_top10_energy_fraction']['median']:.4f} |"
            f" {data['pair_distance_energy_band_8_fraction']['median']:.4f} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--c2-eval", type=Path, required=True)
    parser.add_argument("--c4-eval", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-markdown", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.c2_eval, args.c4_eval)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    write_markdown(args.output_markdown, result)
    print(
        json.dumps(
            {"record_count": result["record_count"], "hard_count": result["hard"]["record_count"]}
        )
    )


if __name__ == "__main__":
    main()
