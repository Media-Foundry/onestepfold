#!/usr/bin/env python3
"""Extract predictive and reactive Stage 0D recycling features."""

from __future__ import annotations

import argparse
import gzip
import json
import math
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np

AA_ORDER = "ACDEFGHIKLMNPQRSTVWY"
EVAL_SETTINGS = ("c1_s1", "c2_s1", "c2_s2", "c4_s1", "c4_s5")
COORDINATE_SETTINGS = ("c1_s1", "c2_s1", "c4_s1")


def load_jsonl_gz(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            rows[str(row["group_id"])] = row
    return rows


def load_eval(eval_root: Path, setting: str) -> dict[str, dict[str, Any]]:
    payload = json.loads((eval_root / f"{setting}.json").read_text(encoding="utf-8"))
    return {
        str(record["group_id"]): record
        for record in payload.get("records", [])
        if record.get("status") == "ok"
    }


def confidence_path(prediction_path: Path) -> Path:
    suffix = "_sample_0.cif"
    if not prediction_path.name.endswith(suffix):
        raise ValueError(f"unexpected prediction filename: {prediction_path.name}")
    stem = prediction_path.name[: -len(suffix)]
    return prediction_path.with_name(f"{stem}_summary_confidence_sample_0.json")


def read_ca(path: Path, length: int) -> np.ndarray:
    import gemmi

    coordinates = np.full((length, 3), np.nan, dtype=np.float32)
    structure = gemmi.read_structure(str(path))
    if len(structure) == 0 or len(structure[0]) == 0:
        raise ValueError(f"prediction has no model/chain: {path}")
    chain = next(iter(structure[0]))
    for fallback_index, residue in enumerate(chain):
        index = int(residue.seqid.num) - 1
        if not 0 <= index < length:
            index = fallback_index
        atom = next((item for item in residue if str(item.name).strip().upper() == "CA"), None)
        if atom is None:
            continue
        values = np.asarray([atom.pos.x, atom.pos.y, atom.pos.z], dtype=np.float32)
        if np.isfinite(values).all():
            coordinates[index] = values
    if not np.isfinite(coordinates).all():
        missing = int((~np.isfinite(coordinates).all(axis=1)).sum())
        raise ValueError(f"prediction has {missing} missing CA coordinates: {path}")
    return coordinates


def kabsch_rmsd(left: np.ndarray, right: np.ndarray) -> float:
    left_centered = left - left.mean(axis=0)
    right_centered = right - right.mean(axis=0)
    u, _, vt = np.linalg.svd(left_centered.T @ right_centered)
    rotation = u @ vt
    if np.linalg.det(rotation) < 0:
        u[:, -1] *= -1
        rotation = u @ vt
    aligned = left_centered @ rotation
    return float(np.sqrt(np.mean(np.sum((aligned - right_centered) ** 2, axis=1))))


def pair_distances(coordinates: np.ndarray) -> np.ndarray:
    from scipy.spatial.distance import pdist

    return np.asarray(pdist(coordinates), dtype=np.float32)


def sequence_features(sequence: str) -> dict[str, float]:
    length = len(sequence)
    counts = {aa: sequence.count(aa) for aa in AA_ORDER}
    fractions = {aa: counts[aa] / length for aa in AA_ORDER}
    entropy = -sum(value * math.log(value) for value in fractions.values() if value > 0)
    result = {
        "length": float(length),
        "log_length": math.log(length),
        "sequence_entropy": entropy,
        "hydrophobic_fraction": sum(fractions[aa] for aa in "AVILMFWY"),
        "charged_fraction": sum(fractions[aa] for aa in "DEKR"),
        "gly_pro_fraction": fractions["G"] + fractions["P"],
        "cysteine_fraction": fractions["C"],
    }
    result.update({f"aa_fraction_{aa}": value for aa, value in fractions.items()})
    return result


def coordinate_features(coordinates: np.ndarray, distances: np.ndarray) -> dict[str, float]:
    centered = coordinates - coordinates.mean(axis=0)
    radius = float(np.sqrt(np.mean(np.sum(centered**2, axis=1))))
    consecutive = np.linalg.norm(np.diff(coordinates, axis=0), axis=1)
    return {
        "ca_radius_gyration": radius,
        "ca_radius_gyration_over_cuberoot_length": radius / len(coordinates) ** (1.0 / 3.0),
        "ca_end_to_end_distance": float(np.linalg.norm(coordinates[-1] - coordinates[0])),
        "ca_consecutive_mean": float(np.mean(consecutive)),
        "ca_consecutive_std": float(np.std(consecutive)),
        "ca_consecutive_max": float(np.max(consecutive)),
        "ca_break_fraction_4p5": float(np.mean(consecutive > 4.5)),
        "ca_pair_mean": float(np.mean(distances)),
        "ca_pair_std": float(np.std(distances)),
        "ca_pair_q10": float(np.quantile(distances, 0.10)),
        "ca_pair_q50": float(np.quantile(distances, 0.50)),
        "ca_pair_q90": float(np.quantile(distances, 0.90)),
        "ca_contact_fraction_8": float(np.mean(distances < 8.0)),
        "ca_contact_fraction_12": float(np.mean(distances < 12.0)),
    }


def extract_one(task: dict[str, Any]) -> dict[str, Any]:
    group_id = str(task["group_id"])
    sequence = str(task["sequence"])
    length = len(sequence)
    paths = {setting: Path(task["prediction_paths"][setting]) for setting in COORDINATE_SETTINGS}
    coordinates = {setting: read_ca(path, length) for setting, path in paths.items()}
    distance_maps = {setting: pair_distances(value) for setting, value in coordinates.items()}
    confidence = json.loads(confidence_path(paths["c1_s1"]).read_text(encoding="utf-8"))
    metrics = task["metrics"]
    features = sequence_features(sequence)
    features.update(
        {
            "confidence_plddt": float(confidence["plddt"]),
            "confidence_ptm": float(confidence["ptm"]),
            "confidence_gpde": float(confidence["gpde"]),
            "confidence_ranking_score": float(confidence["ranking_score"]),
            "confidence_disorder": float(confidence.get("disorder", 0.0)),
            "confidence_has_clash": float(bool(confidence.get("has_clash", False))),
        }
    )
    features.update(coordinate_features(coordinates["c1_s1"], distance_maps["c1_s1"]))
    reactive = {
        "c1_c2_distance_map_rms_angstrom": float(
            np.sqrt(np.mean((distance_maps["c2_s1"] - distance_maps["c1_s1"]) ** 2))
        ),
        "c2_c4_distance_map_rms_angstrom": float(
            np.sqrt(np.mean((distance_maps["c4_s1"] - distance_maps["c2_s1"]) ** 2))
        ),
        "c1_c2_kabsch_ca_rmsd_angstrom": kabsch_rmsd(coordinates["c1_s1"], coordinates["c2_s1"]),
        "c2_c4_kabsch_ca_rmsd_angstrom": kabsch_rmsd(coordinates["c2_s1"], coordinates["c4_s1"]),
    }
    labels = {
        "hard_c1_vs_c4s5_tm_0p05": (
            float(metrics["c1_s1"]["tm_score_ca"]) - float(metrics["c4_s5"]["tm_score_ca"]) < -0.05
        ),
        "hard_c1_vs_c4s1_tm_0p05": (
            float(metrics["c1_s1"]["tm_score_ca"]) - float(metrics["c4_s1"]["tm_score_ca"]) < -0.05
        ),
        "delta_c1s1_vs_c4s5_tm": (
            float(metrics["c1_s1"]["tm_score_ca"]) - float(metrics["c4_s5"]["tm_score_ca"])
        ),
        "delta_c1s1_vs_c4s1_tm": (
            float(metrics["c1_s1"]["tm_score_ca"]) - float(metrics["c4_s1"]["tm_score_ca"])
        ),
        "delta_c2s1_vs_c4s1_tm": (
            float(metrics["c2_s1"]["tm_score_ca"]) - float(metrics["c4_s1"]["tm_score_ca"])
        ),
    }
    return {
        "group_id": group_id,
        "family_proxy_group_id": task["family_proxy_group_id"],
        "features": features,
        "reactive": reactive,
        "labels": labels,
        "metrics": metrics,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--groups", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    manifest = load_jsonl_gz(args.manifest)
    groups = load_jsonl_gz(args.groups)
    evaluations = {setting: load_eval(args.eval_root, setting) for setting in EVAL_SETTINGS}
    common = sorted(set(manifest).intersection(*(set(value) for value in evaluations.values())))
    if args.limit is not None:
        common = common[: args.limit]
    tasks = []
    for group_id in common:
        group = groups[group_id]
        closest = group.get("closest_pair") or {}
        tasks.append(
            {
                "group_id": group_id,
                "sequence": manifest[group_id]["sequence"],
                "family_proxy_group_id": str(closest.get("group_id") or group_id),
                "prediction_paths": {
                    setting: evaluations[setting][group_id]["prediction_path"]
                    for setting in COORDINATE_SETTINGS
                },
                "metrics": {
                    setting: {
                        metric: evaluations[setting][group_id][metric]
                        for metric in ("tm_score_ca", "ca_lddt", "all_atom_lddt")
                    }
                    for setting in EVAL_SETTINGS
                },
            }
        )
    records: list[dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        for index, record in enumerate(executor.map(extract_one, tasks), start=1):
            records.append(record)
            if index % 100 == 0:
                print(f"extracted {index}/{len(tasks)}", flush=True)
    payload = {
        "record_count": len(records),
        "scope": "temporal_dev_v1 only; frozen temporal test was not read",
        "family_proxy_definition": "closest pre-cutoff train group from the near-homology audit",
        "reactive_definition": "RMS change between condensed all-pair CA distance maps",
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in payload.items() if key != "records"}, indent=2))


if __name__ == "__main__":
    main()
