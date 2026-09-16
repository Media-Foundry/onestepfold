#!/usr/bin/env python3
"""Build c2-to-c4 routing features from the frozen Stage 0D dev artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

INTERNAL_FEATURES = (
    "single_mean",
    "single_std",
    "single_abs_mean",
    "single_normalized_norm_mean",
    "single_normalized_norm_std",
    "pair_mean",
    "pair_std",
    "pair_abs_mean",
    "pair_normalized_norm_mean",
    "pair_normalized_norm_std",
    "pair_symmetry_abs_mean",
    "pair_diagonal_mean",
    "pair_diagonal_std",
    "pair_diagonal_abs_mean",
    "pair_diagonal_normalized_norm_mean",
    "pair_diagonal_normalized_norm_std",
)


def confidence_path(prediction_path: Path) -> Path:
    suffix = "_sample_0.cif"
    if not prediction_path.name.endswith(suffix):
        raise ValueError(f"unexpected prediction filename: {prediction_path.name}")
    stem = prediction_path.name[: -len(suffix)]
    return prediction_path.with_name(f"{stem}_summary_confidence_sample_0.json")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_internal(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            sample_name = str(row["sample_name"])
            if sample_name in rows:
                raise ValueError(f"duplicate c2 internal row: {sample_name}")
            cycles = row.get("cycles", [])
            if int(row.get("cycle_count", -1)) != 2 or len(cycles) != 2:
                raise ValueError(f"expected two cycles for {sample_name}")
            if any("feature_error" in cycle for cycle in cycles):
                raise ValueError(f"internal feature error for {sample_name}")
            for cycle in cycles:
                observed = {key: float(cycle[key]) for key in INTERNAL_FEATURES if key in cycle}
                if set(observed) != set(INTERNAL_FEATURES):
                    raise ValueError(f"internal feature schema mismatch for {sample_name}")
            rows[sample_name] = row
    return rows


def confidence_features(path: Path, prefix: str) -> dict[str, float]:
    row = load_json(path)
    return {
        f"{prefix}_plddt": float(row["plddt"]),
        f"{prefix}_ptm": float(row["ptm"]),
        f"{prefix}_gpde": float(row["gpde"]),
        f"{prefix}_ranking_score": float(row["ranking_score"]),
        f"{prefix}_disorder": float(row.get("disorder", 0.0)),
        f"{prefix}_has_clash": float(bool(row.get("has_clash", False))),
    }


def trajectory_features(row: dict[str, Any]) -> dict[str, float]:
    first, second = row["cycles"]
    result: dict[str, float] = {}
    for name in INTERNAL_FEATURES:
        left = float(first[name])
        right = float(second[name])
        delta = right - left
        result[f"trajectory_delta_{name}"] = delta
        result[f"trajectory_abs_delta_{name}"] = abs(delta)
        result[f"trajectory_relative_delta_{name}"] = delta / max(abs(left), 1e-6)
    return result


def build(args: argparse.Namespace) -> dict[str, Any]:
    base = load_json(args.base_features)
    c2_eval = load_json(args.c2_eval)
    c2_records = {
        str(row["group_id"]): row for row in c2_eval["records"] if row.get("status") == "ok"
    }
    internal = load_internal(args.c2_internal)
    records = []
    for source in base["records"]:
        group_id = str(source["group_id"])
        if group_id not in c2_records or group_id not in internal:
            raise ValueError(f"missing c2 data for {group_id}")
        c2_record = c2_records[group_id]
        c2_confidence = confidence_path(Path(c2_record["prediction_path"]))
        features = {
            key: float(value)
            for key, value in source["features"].items()
            if key.startswith(
                (
                    "log_",
                    "sequence_",
                    "hydrophobic_",
                    "charged_",
                    "gly_",
                    "cysteine_",
                    "aa_fraction_",
                )
            )
        }
        features.update(confidence_features(c2_confidence, "c2_confidence"))
        for metric_name in ("plddt", "ptm", "gpde", "ranking_score", "disorder", "has_clash"):
            c1_name = f"confidence_{metric_name}"
            c2_name = f"c2_confidence_{metric_name}"
            if c1_name in source["features"] and c2_name in features:
                features[f"confidence_delta_c2_c1_{metric_name}"] = features[c2_name] - float(
                    source["features"][c1_name]
                )
        internal_row = internal[group_id]
        features.update(trajectory_features(internal_row))
        for name in INTERNAL_FEATURES:
            features[f"c2_internal_{name}"] = float(internal_row["cycles"][1][name])
        c2_metrics = source["metrics"]["c2_s2"]
        anchor_metrics = source["metrics"]["c4_s5"]
        delta_tm = float(c2_metrics["tm_score_ca"]) - float(anchor_metrics["tm_score_ca"])
        delta_all_atom = float(c2_metrics["all_atom_lddt"]) - float(anchor_metrics["all_atom_lddt"])
        records.append(
            {
                "group_id": group_id,
                "family_proxy_group_id": source["family_proxy_group_id"],
                "features": features,
                "labels": {
                    "hard_c2_vs_c4s5_joint_0p05": bool(delta_tm < -0.05 or delta_all_atom < -0.05),
                    "hard_c2_vs_c4s5_tm_0p05": bool(delta_tm < -0.05),
                    "delta_c2s2_vs_c4s5_tm": delta_tm,
                    "delta_c2s2_vs_c4s5_all_atom_lddt": delta_all_atom,
                },
                "metrics": source["metrics"],
                "reactive": source["reactive"],
            }
        )
    if len(records) != len(base["records"]):
        raise ValueError("record count changed during c2 feature extraction")
    return {
        "record_count": len(records),
        "scope": "temporal_dev_v1 only; frozen temporal test was not read",
        "target_label": "c2_s2 joint TM/all-atom degradation below -0.05 versus c4_s5",
        "feature_definition": "cycle-2 confidence plus c1-to-c2 internal-state trajectory",
        "records": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-features", type=Path, required=True)
    parser.add_argument("--c2-eval", type=Path, required=True)
    parser.add_argument("--c2-internal", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    labels = [row["labels"]["hard_c2_vs_c4s5_joint_0p05"] for row in result["records"]]
    print(json.dumps({"target_count": len(labels), "positive_count": int(np.sum(labels))}))


if __name__ == "__main__":
    main()
