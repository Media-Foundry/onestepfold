#!/usr/bin/env python3
"""Evaluate predictive and reactive Stage 0D recycle routing policies."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_sample_weight

RISK_LIMITS = (0.0, 0.01, 0.02, 0.05)
SEQUENCE_FEATURES = (
    "log_length",
    "sequence_entropy",
    "hydrophobic_fraction",
    "charged_fraction",
    "gly_pro_fraction",
    "cysteine_fraction",
) + tuple(f"aa_fraction_{aa}" for aa in "ACDEFGHIKLMNPQRSTVWY")
CONFIDENCE_FEATURES = (
    "confidence_plddt",
    "confidence_ptm",
    "confidence_gpde",
    "confidence_ranking_score",
    "confidence_disorder",
    "confidence_has_clash",
)
GEOMETRY_FEATURES = (
    "ca_radius_gyration",
    "ca_radius_gyration_over_cuberoot_length",
    "ca_end_to_end_distance",
    "ca_consecutive_mean",
    "ca_consecutive_std",
    "ca_consecutive_max",
    "ca_break_fraction_4p5",
    "ca_pair_mean",
    "ca_pair_std",
    "ca_pair_q10",
    "ca_pair_q50",
    "ca_pair_q90",
    "ca_contact_fraction_8",
    "ca_contact_fraction_12",
)
INTERNAL_FEATURES = (
    "internal_single_mean",
    "internal_single_std",
    "internal_single_abs_mean",
    "internal_single_normalized_norm_mean",
    "internal_single_normalized_norm_std",
    "internal_pair_mean",
    "internal_pair_std",
    "internal_pair_abs_mean",
    "internal_pair_normalized_norm_mean",
    "internal_pair_normalized_norm_std",
    "internal_pair_symmetry_abs_mean",
    "internal_pair_diagonal_mean",
    "internal_pair_diagonal_std",
    "internal_pair_diagonal_abs_mean",
    "internal_pair_diagonal_normalized_norm_mean",
    "internal_pair_diagonal_normalized_norm_std",
)


def summarize(values: np.ndarray) -> dict[str, float]:
    return {
        "mean": float(np.mean(values)),
        "median": float(np.median(values)),
        "p05": float(np.quantile(values, 0.05)),
        "p95": float(np.quantile(values, 0.95)),
    }


def extract_matrix(records: list[dict[str, Any]], names: tuple[str, ...]) -> np.ndarray:
    matrix = np.asarray(
        [[float(record["features"][name]) for name in names] for record in records],
        dtype=np.float64,
    )
    if not np.isfinite(matrix).all():
        raise ValueError(f"non-finite router features in {names}")
    return matrix


def grouped_oof_predictions(
    records: list[dict[str, Any]],
    feature_names: tuple[str, ...],
    model_name: str,
    seed: int,
) -> tuple[np.ndarray, list[dict[str, Any]], list[list[float]]]:
    features = extract_matrix(records, feature_names)
    labels = np.asarray(
        [record["labels"]["hard_c1_vs_c4s1_tm_0p05"] for record in records],
        dtype=np.int64,
    )
    groups = np.asarray([record["family_proxy_group_id"] for record in records])
    splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
    predictions = np.full(len(records), np.nan, dtype=np.float64)
    folds: list[dict[str, Any]] = []
    coefficients: list[list[float]] = []
    for fold_index, (train, validation) in enumerate(
        splitter.split(features, labels, groups), start=1
    ):
        if model_name == "logistic":
            model = make_pipeline(
                StandardScaler(),
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=5000,
                    random_state=seed + fold_index,
                ),
            )
            model.fit(features[train], labels[train])
            coefficients.append(model[-1].coef_[0].astype(float).tolist())
        elif model_name == "hist_gradient_boosting":
            model = HistGradientBoostingClassifier(
                learning_rate=0.05,
                max_iter=200,
                max_leaf_nodes=15,
                min_samples_leaf=20,
                l2_regularization=1.0,
                random_state=seed + fold_index,
            )
            weights = compute_sample_weight(class_weight="balanced", y=labels[train])
            model.fit(features[train], labels[train], sample_weight=weights)
        else:
            raise ValueError(f"unknown model: {model_name}")
        predictions[validation] = model.predict_proba(features[validation])[:, 1]
        folds.append(
            {
                "fold": fold_index,
                "train_count": int(len(train)),
                "validation_count": int(len(validation)),
                "train_positive_count": int(labels[train].sum()),
                "validation_positive_count": int(labels[validation].sum()),
                "train_family_proxy_count": int(len(set(groups[train]))),
                "validation_family_proxy_count": int(len(set(groups[validation]))),
            }
        )
    if not np.isfinite(predictions).all():
        raise RuntimeError("OOF prediction coverage is incomplete")
    return predictions, folds, coefficients


def routing_point(
    records: list[dict[str, Any]],
    route_deep: np.ndarray,
    shallow_setting: str,
    deep_setting: str,
    shallow_cycles: int,
    deep_cycles: int,
    threshold: float,
) -> dict[str, Any]:
    selected = [
        record["metrics"][deep_setting if deep else shallow_setting]
        for record, deep in zip(records, route_deep, strict=True)
    ]
    anchors = [record["metrics"][deep_setting] for record in records]
    delta_tm = np.asarray(
        [
            float(value["tm_score_ca"]) - float(anchor["tm_score_ca"])
            for value, anchor in zip(selected, anchors, strict=True)
        ]
    )
    delta_all_atom = np.asarray(
        [
            float(value["all_atom_lddt"]) - float(anchor["all_atom_lddt"])
            for value, anchor in zip(selected, anchors, strict=True)
        ]
    )
    return {
        "threshold": float(threshold),
        "route_deep_fraction": float(np.mean(route_deep)),
        "mean_cycles": float(shallow_cycles + (deep_cycles - shallow_cycles) * np.mean(route_deep)),
        "mean_delta_tm": float(np.mean(delta_tm)),
        "median_delta_tm": float(np.median(delta_tm)),
        "catastrophic_tm_risk": float(np.mean(delta_tm < -0.05)),
        "mean_delta_all_atom_lddt": float(np.mean(delta_all_atom)),
        "all_atom_lddt_risk_0p05": float(np.mean(delta_all_atom < -0.05)),
        "catastrophic_joint_risk": float(np.mean((delta_tm < -0.05) | (delta_all_atom < -0.05))),
    }


def routing_curve(
    records: list[dict[str, Any]],
    scores: np.ndarray,
    shallow_setting: str,
    deep_setting: str,
    shallow_cycles: int,
    deep_cycles: int,
) -> list[dict[str, Any]]:
    thresholds = np.concatenate(([math.inf], np.sort(np.unique(scores))[::-1], [-math.inf]))
    return [
        routing_point(
            records,
            scores >= threshold,
            shallow_setting,
            deep_setting,
            shallow_cycles,
            deep_cycles,
            float(threshold),
        )
        for threshold in thresholds
    ]


def constrained_points(
    curve: list[dict[str, Any]], risk_field: str
) -> dict[str, dict[str, Any] | None]:
    result: dict[str, dict[str, Any] | None] = {}
    for risk_limit in RISK_LIMITS:
        valid = [point for point in curve if point[risk_field] <= risk_limit]
        best = (
            min(valid, key=lambda item: (item["mean_cycles"], -item["mean_delta_tm"]))
            if valid
            else None
        )
        result[f"risk_le_{risk_limit:.2f}"] = best
    return result


def score_summary(labels: np.ndarray, scores: np.ndarray) -> dict[str, float]:
    return {
        "auroc": float(roc_auc_score(labels, scores)),
        "average_precision": float(average_precision_score(labels, scores)),
    }


def add_internal_features(records: list[dict[str, Any]], path: Path) -> None:
    feature_rows: dict[str, dict[str, float]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            sample_name = str(row["sample_name"])
            if sample_name in feature_rows:
                raise ValueError(f"duplicate internal feature row: {sample_name}")
            cycles = row.get("cycles", [])
            if int(row.get("cycle_count", -1)) != 1 or len(cycles) != 1:
                raise ValueError(f"expected exactly one cycle for {sample_name}")
            cycle = cycles[0]
            if "feature_error" in cycle:
                raise ValueError(
                    f"internal feature error for {sample_name}: {cycle['feature_error']}"
                )
            features = {
                f"internal_{key}": float(value)
                for key, value in cycle.items()
                if key not in {"cycle_index", "single_shape", "pair_shape"}
            }
            if set(features) != set(INTERNAL_FEATURES):
                missing = sorted(set(INTERNAL_FEATURES) - set(features))
                extra = sorted(set(features) - set(INTERNAL_FEATURES))
                raise ValueError(
                    f"internal feature schema mismatch for {sample_name}: "
                    f"missing={missing} extra={extra}"
                )
            feature_rows[sample_name] = features
    record_ids = {str(record["group_id"]) for record in records}
    if set(feature_rows) != record_ids:
        raise ValueError(
            f"internal feature coverage mismatch: records={len(record_ids)} "
            f"features={len(feature_rows)}"
        )
    for record in records:
        record["features"].update(feature_rows[str(record["group_id"])])


def analyze(
    input_path: Path, seed: int, internal_features_path: Path | None = None
) -> dict[str, Any]:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    records = payload["records"]
    if internal_features_path is not None:
        add_internal_features(records, internal_features_path)
    labels = np.asarray(
        [record["labels"]["hard_c1_vs_c4s1_tm_0p05"] for record in records],
        dtype=np.int64,
    )
    feature_sets = {
        "tier_a_sequence": SEQUENCE_FEATURES,
        "tier_ab_confidence": SEQUENCE_FEATURES + CONFIDENCE_FEATURES,
        "tier_ab_confidence_geometry": (
            SEQUENCE_FEATURES + CONFIDENCE_FEATURES + GEOMETRY_FEATURES
        ),
    }
    if internal_features_path is not None:
        feature_sets["tier_ab_confidence_internal"] = (
            SEQUENCE_FEATURES + CONFIDENCE_FEATURES + INTERNAL_FEATURES
        )
        feature_sets["tier_ab_confidence_geometry_internal"] = (
            SEQUENCE_FEATURES + CONFIDENCE_FEATURES + GEOMETRY_FEATURES + INTERNAL_FEATURES
        )
    policies: dict[str, Any] = {}
    fold_manifest: dict[str, Any] | None = None
    for feature_set, names in feature_sets.items():
        for model_name in ("logistic", "hist_gradient_boosting"):
            scores, folds, coefficients = grouped_oof_predictions(records, names, model_name, seed)
            if fold_manifest is None:
                fold_manifest = {"folds": folds}
            curve = routing_curve(records, scores, "c1_s1", "c4_s1", 1, 4)
            policy_name = f"{model_name}_{feature_set}"
            policies[policy_name] = {
                "availability": "cycle_1",
                "feature_names": list(names),
                "classification": score_summary(labels, scores),
                "tm_risk_constrained_points": constrained_points(curve, "catastrophic_tm_risk"),
                "joint_risk_constrained_points": constrained_points(
                    curve, "catastrophic_joint_risk"
                ),
            }
            if coefficients:
                mean_abs = np.mean(np.abs(np.asarray(coefficients)), axis=0)
                policies[policy_name]["mean_abs_standardized_coefficients"] = dict(
                    sorted(
                        zip(names, mean_abs.astype(float), strict=True),
                        key=lambda item: item[1],
                        reverse=True,
                    )
                )

    scalar_scores = {
        "length_threshold": np.asarray([record["features"]["log_length"] for record in records]),
        "confidence_ptm_threshold": -np.asarray(
            [record["features"]["confidence_ptm"] for record in records]
        ),
        "oracle_c1_hardness": -np.asarray(
            [record["labels"]["delta_c1s1_vs_c4s1_tm"] for record in records]
        ),
    }
    for name, scores in scalar_scores.items():
        curve = routing_curve(records, scores, "c1_s1", "c4_s1", 1, 4)
        policies[name] = {
            "availability": "oracle" if name.startswith("oracle") else "cycle_1",
            "classification": score_summary(labels, scores),
            "tm_risk_constrained_points": constrained_points(curve, "catastrophic_tm_risk"),
            "joint_risk_constrained_points": constrained_points(curve, "catastrophic_joint_risk"),
        }

    reactive_scores = np.asarray(
        [record["reactive"]["c1_c2_distance_map_rms_angstrom"] for record in records]
    )
    reactive_curve = routing_curve(records, reactive_scores, "c2_s1", "c4_s1", 2, 4)
    reactive_labels = np.asarray(
        [record["labels"]["delta_c2s1_vs_c4s1_tm"] < -0.05 for record in records]
    )
    policies["af_style_distance_convergence"] = {
        "availability": "after_cycle_2",
        "classification": score_summary(reactive_labels, reactive_scores),
        "tm_risk_constrained_points": constrained_points(reactive_curve, "catastrophic_tm_risk"),
        "joint_risk_constrained_points": constrained_points(
            reactive_curve, "catastrophic_joint_risk"
        ),
    }

    fixed = {}
    for setting, cycles in (("c1_s1", 1), ("c2_s1", 2), ("c2_s2", 2), ("c4_s1", 4)):
        fixed[setting] = routing_point(
            records,
            np.zeros(len(records), dtype=bool),
            setting,
            "c4_s1",
            cycles,
            cycles,
            math.inf,
        )
    family_counts = Counter(record["family_proxy_group_id"] for record in records)
    return {
        "scope": payload["scope"],
        "target_label": "c1_s1 TM-style delta versus c4_s1 < -0.05",
        "target_count": len(records),
        "positive_count": int(labels.sum()),
        "positive_fraction": float(labels.mean()),
        "family_proxy_definition": payload["family_proxy_definition"],
        "family_proxy_count": len(family_counts),
        "largest_family_proxy_group": max(family_counts.values()),
        "internal_features": (
            {
                "source": str(internal_features_path),
                "record_count": len(records),
                "feature_count": len(INTERNAL_FEATURES),
                "sha256": hashlib.sha256(internal_features_path.read_bytes()).hexdigest(),
            }
            if internal_features_path is not None
            else None
        ),
        "cross_validation": fold_manifest,
        "fixed_baselines_vs_c4_s1": fixed,
        "policies": policies,
    }


def fmt(value: float | None, digits: int = 3) -> str:
    return "NA" if value is None else f"{value:.{digits}f}"


def write_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Stage 0D Predictive Recycling",
        "",
        f"Scope: {result['scope']}.",
        "",
        (
            f"The clean recycle label contains {result['positive_count']}/{result['target_count']} "
            f"targets ({100 * result['positive_fraction']:.1f}%) with `c1_s1` TM-style degradation "
            "greater than 0.05 relative to `c4_s1`."
        ),
        "",
        (
            "Five-fold OOF predictions group "
            f"{result['family_proxy_count']} nearest-train-sequence "
            "proxies; this is a homology-aware proxy split, not a frozen family-cluster benchmark."
        ),
        "",
        "## Fixed Baselines",
        "",
        (
            "| setting | cycles | mean delta TM | catastrophic TM risk | "
            "mean delta all-atom lDDT | joint catastrophic risk |"
        ),
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for setting, point in result["fixed_baselines_vs_c4_s1"].items():
        lines.append(
            f"| {setting} | {point['mean_cycles']:.1f} | {point['mean_delta_tm']:.4f} | "
            f"{point['catastrophic_tm_risk']:.3f} | {point['mean_delta_all_atom_lddt']:.4f} |"
            f" {point['catastrophic_joint_risk']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Predictability",
            "",
            "| policy | availability | AUROC | average precision |",
            "| --- | --- | ---: | ---: |",
        ]
    )
    for name, policy in result["policies"].items():
        classification = policy["classification"]
        lines.append(
            f"| {name} | {policy['availability']} | {classification['auroc']:.3f} | "
            f"{classification['average_precision']:.3f} |"
        )
    for risk_name, field in (
        ("TM", "tm_risk_constrained_points"),
        ("Joint TM/All-Atom", "joint_risk_constrained_points"),
    ):
        for risk_limit in (0.01, 0.02):
            key = f"risk_le_{risk_limit:.2f}"
            lines.extend(
                [
                    "",
                    (
                        f"## Minimum Compute At {risk_name} Catastrophic Risk "
                        f"<= {100 * risk_limit:.0f}%"
                    ),
                    "",
                    (
                        "| policy | mean cycles | routed deep | mean delta TM | "
                        "mean delta all-atom lDDT |"
                    ),
                    "| --- | ---: | ---: | ---: | ---: |",
                ]
            )
            for name, policy in result["policies"].items():
                point = policy[field][key]
                if point is None:
                    continue
                lines.append(
                    f"| {name} | {point['mean_cycles']:.3f} | "
                    f"{100 * point['route_deep_fraction']:.1f}% | "
                    f"{point['mean_delta_tm']:.4f} | "
                    f"{point['mean_delta_all_atom_lddt']:.4f} |"
                )
    lines.extend(
        [
            "",
            (
                "All learned results are out-of-fold diagnostics on `temporal_dev_v1`. "
                "Thresholds are swept on those OOF predictions, so the selected operating points "
                "are not frozen-test estimates."
            ),
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260916)
    parser.add_argument("--internal-features", type=Path, default=None)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-markdown", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.input, args.seed, args.internal_features)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    write_markdown(args.output_markdown, result)
    print(
        json.dumps(
            {
                "target_count": result["target_count"],
                "positive_count": result["positive_count"],
                "family_proxy_count": result["family_proxy_count"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
