#!/usr/bin/env python3
"""Evaluate predictive c2-to-c4 recycle routing on temporal_dev_v1."""

from __future__ import annotations

import argparse
import json
import math
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
SEQUENCE_FEATURES = tuple(
    name
    for name in (
        "log_length",
        "sequence_entropy",
        "hydrophobic_fraction",
        "charged_fraction",
        "gly_pro_fraction",
        "cysteine_fraction",
    )
    + tuple(f"aa_fraction_{aa}" for aa in "ACDEFGHIKLMNPQRSTVWY")
)
C2_CONFIDENCE_FEATURES = tuple(
    f"c2_confidence_{name}"
    for name in ("plddt", "ptm", "gpde", "ranking_score", "disorder", "has_clash")
)
CONFIDENCE_DELTA_FEATURES = tuple(
    f"confidence_delta_c2_c1_{name}"
    for name in ("plddt", "ptm", "gpde", "ranking_score", "disorder", "has_clash")
)
TRAJECTORY_FEATURES = tuple(
    f"trajectory_{kind}_{name}"
    for kind in ("delta", "abs_delta", "relative_delta")
    for name in (
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
)
COORDINATE_TRAJECTORY_FEATURES = (
    "trajectory_coordinate_distance_map_rms_angstrom",
    "trajectory_coordinate_kabsch_ca_rmsd_angstrom",
)


def extract_matrix(records: list[dict[str, Any]], names: tuple[str, ...]) -> np.ndarray:
    matrix = np.asarray(
        [[float(record["features"][name]) for name in names] for record in records],
        dtype=np.float64,
    )
    if not np.isfinite(matrix).all():
        raise ValueError(f"non-finite features in {names[:2]}")
    return matrix


def oof_predictions(
    records: list[dict[str, Any]], names: tuple[str, ...], model_name: str, seed: int
) -> tuple[np.ndarray, list[dict[str, Any]]]:
    features = extract_matrix(records, names)
    labels = np.asarray(
        [record["labels"]["hard_c2_vs_c4s5_joint_0p05"] for record in records], dtype=np.int64
    )
    groups = np.asarray([record["family_proxy_group_id"] for record in records])
    splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
    predictions = np.full(len(records), np.nan, dtype=np.float64)
    folds = []
    for fold, (train, validation) in enumerate(splitter.split(features, labels, groups), start=1):
        if model_name == "logistic":
            model = make_pipeline(
                StandardScaler(),
                LogisticRegression(
                    class_weight="balanced", max_iter=5000, random_state=seed + fold
                ),
            )
            model.fit(features[train], labels[train])
        elif model_name == "hist_gradient_boosting":
            model = HistGradientBoostingClassifier(
                learning_rate=0.05,
                max_iter=200,
                max_leaf_nodes=15,
                min_samples_leaf=20,
                l2_regularization=1.0,
                random_state=seed + fold,
            )
            model.fit(
                features[train],
                labels[train],
                sample_weight=compute_sample_weight(class_weight="balanced", y=labels[train]),
            )
        else:
            raise ValueError(f"unknown model: {model_name}")
        predictions[validation] = model.predict_proba(features[validation])[:, 1]
        folds.append(
            {
                "fold": fold,
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
    return predictions, folds


def routing_point(
    records: list[dict[str, Any]], route_deep: np.ndarray, threshold: float
) -> dict[str, Any]:
    selected = [
        record["metrics"]["c4_s5" if deep else "c2_s2"]
        for record, deep in zip(records, route_deep, strict=True)
    ]
    anchors = [record["metrics"]["c4_s5"] for record in records]
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
        "mean_cycles": float(2.0 + 2.0 * np.mean(route_deep)),
        "mean_delta_tm": float(np.mean(delta_tm)),
        "mean_delta_all_atom_lddt": float(np.mean(delta_all_atom)),
        "catastrophic_tm_risk": float(np.mean(delta_tm < -0.05)),
        "catastrophic_joint_risk": float(np.mean((delta_tm < -0.05) | (delta_all_atom < -0.05))),
    }


def routing_curve(records: list[dict[str, Any]], scores: np.ndarray) -> list[dict[str, Any]]:
    thresholds = np.concatenate(([math.inf], np.sort(np.unique(scores))[::-1], [-math.inf]))
    return [
        routing_point(records, scores >= threshold, float(threshold)) for threshold in thresholds
    ]


def constrained(curve: list[dict[str, Any]], field: str) -> dict[str, dict[str, Any] | None]:
    result = {}
    for limit in RISK_LIMITS:
        valid = [point for point in curve if point[field] <= limit]
        result[f"risk_le_{limit:.2f}"] = (
            min(valid, key=lambda point: point["mean_cycles"]) if valid else None
        )
    return result


def oracle_curve(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Higher score means a larger joint degradation and therefore routes to c4.
    scores = np.asarray(
        [
            -min(
                float(record["labels"]["delta_c2s2_vs_c4s5_tm"]),
                float(record["labels"]["delta_c2s2_vs_c4s5_all_atom_lddt"]),
            )
            for record in records
        ]
    )
    return routing_curve(records, scores)


def analyze(path: Path, seed: int) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload["records"]
    labels = np.asarray(
        [record["labels"]["hard_c2_vs_c4s5_joint_0p05"] for record in records], dtype=np.int64
    )
    feature_sets = {
        "tier_a_sequence": SEQUENCE_FEATURES,
        "tier_b_c2_confidence": SEQUENCE_FEATURES + C2_CONFIDENCE_FEATURES,
        "tier_b_c2_confidence_delta": (
            SEQUENCE_FEATURES + C2_CONFIDENCE_FEATURES + CONFIDENCE_DELTA_FEATURES
        ),
        "tier_c_trajectory": (
            SEQUENCE_FEATURES
            + C2_CONFIDENCE_FEATURES
            + CONFIDENCE_DELTA_FEATURES
            + TRAJECTORY_FEATURES
        ),
        "tier_c_trajectory_geometry": (
            SEQUENCE_FEATURES
            + C2_CONFIDENCE_FEATURES
            + CONFIDENCE_DELTA_FEATURES
            + TRAJECTORY_FEATURES
            + COORDINATE_TRAJECTORY_FEATURES
        ),
    }
    policies: dict[str, Any] = {}
    folds = None
    for feature_name, names in feature_sets.items():
        for model_name in ("logistic", "hist_gradient_boosting"):
            scores, fold_rows = oof_predictions(records, names, model_name, seed)
            folds = folds or fold_rows
            curve = routing_curve(records, scores)
            policies[f"{model_name}_{feature_name}"] = {
                "availability": "after_cycle_2",
                "feature_names": list(names),
                "classification": {
                    "auroc": float(roc_auc_score(labels, scores)),
                    "average_precision": float(average_precision_score(labels, scores)),
                },
                "joint_risk_constrained_points": constrained(curve, "catastrophic_joint_risk"),
                "tm_risk_constrained_points": constrained(curve, "catastrophic_tm_risk"),
            }
    reactive = np.asarray(
        [record["reactive"]["c1_c2_distance_map_rms_angstrom"] for record in records]
    )
    policies["reactive_c1_c2_distance"] = {
        "availability": "after_cycle_2",
        "classification": {
            "auroc": float(roc_auc_score(labels, reactive)),
            "average_precision": float(average_precision_score(labels, reactive)),
        },
        "joint_risk_constrained_points": constrained(
            routing_curve(records, reactive), "catastrophic_joint_risk"
        ),
        "tm_risk_constrained_points": constrained(
            routing_curve(records, reactive), "catastrophic_tm_risk"
        ),
    }
    oracle = oracle_curve(records)
    fixed_c2 = routing_point(records, np.zeros(len(records), dtype=bool), math.inf)
    fixed_c4 = routing_point(records, np.ones(len(records), dtype=bool), math.inf)
    return {
        "scope": payload["scope"],
        "target_label": payload["target_label"],
        "target_count": len(records),
        "positive_count": int(labels.sum()),
        "positive_fraction": float(labels.mean()),
        "cross_validation": {"folds": folds},
        "fixed_baselines": {"c2_s2": fixed_c2, "c4_s5": fixed_c4},
        "oracle_joint_risk_constrained_points": constrained(oracle, "catastrophic_joint_risk"),
        "policies": policies,
    }


def write_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Stage 0E c2-to-c4 Predictive Recycling",
        "",
        result["scope"] + ".",
        "",
        (
            f"The joint hard-target label contains {result['positive_count']}/"
            f"{result['target_count']} targets."
        ),
        (
            "All learned results are family-proxy grouped out-of-fold diagnostics; "
            "frozen temporal test was not read."
        ),
        "",
        "## Fixed Baselines",
        "",
        "| policy | mean cycles | joint catastrophe risk | mean delta TM | "
        "mean delta all-atom lDDT |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for name, point in result["fixed_baselines"].items():
        lines.append(
            f"| {name} | {point['mean_cycles']:.3f} | "
            f"{point['catastrophic_joint_risk']:.3f} | "
            f"{point['mean_delta_tm']:.4f} | "
            f"{point['mean_delta_all_atom_lddt']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Predictors",
            "",
            "| policy | AUROC | average precision | joint-risk <=1% mean cycles | "
            "joint-risk <=1% deep fraction |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for name, policy in result["policies"].items():
        point = policy["joint_risk_constrained_points"]["risk_le_0.01"]
        classification = policy["classification"]
        if point is None:
            lines.append(
                f"| {name} | {classification['auroc']:.3f} | "
                f"{classification['average_precision']:.3f} | NA | NA |"
            )
        else:
            lines.append(
                f"| {name} | {classification['auroc']:.3f} | "
                f"{classification['average_precision']:.3f} | "
                f"{point['mean_cycles']:.3f} | {point['route_deep_fraction']:.3f} |"
            )
    lines.extend(
        [
            "",
            "## Oracle",
            "",
            "| joint-risk limit | mean cycles | deep fraction | catastrophe risk |",
            "| ---: | ---: | ---: | ---: |",
        ]
    )
    for key, point in result["oracle_joint_risk_constrained_points"].items():
        if point is None:
            lines.append(f"| {key.removeprefix('risk_le_')} | NA | NA | NA |")
        else:
            lines.append(
                f"| {key.removeprefix('risk_le_')} | {point['mean_cycles']:.3f} | "
                f"{point['route_deep_fraction']:.3f} | "
                f"{point['catastrophic_joint_risk']:.3f} |"
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260916)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-markdown", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.input, args.seed)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    write_markdown(args.output_markdown, result)
    print(
        json.dumps(
            {"target_count": result["target_count"], "positive_count": result["positive_count"]}
        )
    )


if __name__ == "__main__":
    main()
