#!/usr/bin/env python3
"""Summarize Pairformer recycle residuals for Stage 1A."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

TRANSITIONS = ("c1_to_c2", "c2_to_c3", "c3_to_c4")
RESIDUAL_FIELDS = (
    "single_delta_fro_norm",
    "single_delta_residue_norm_mean",
    "single_delta_residue_norm_p90",
    "single_delta_residue_active_fraction",
    "pair_delta_fro_norm",
    "pair_delta_pair_norm_mean",
    "pair_delta_pair_norm_p90",
    "pair_delta_pair_active_fraction",
    "pair_delta_energy_band_1_fraction",
    "pair_delta_energy_band_4_fraction",
    "pair_delta_energy_band_8_fraction",
    "pair_delta_energy_band_16_fraction",
    "pair_delta_row_energy_p90",
    "pair_delta_pooled_spatial_rank1_energy",
    "pair_delta_pooled_spatial_rank4_energy",
    "pair_delta_pooled_spatial_rank8_energy",
    "pair_delta_pooled_spatial_rank16_energy",
    "pair_delta_channel_rank1_energy",
    "pair_delta_channel_rank4_energy",
    "pair_delta_channel_rank8_energy",
    "pair_delta_channel_rank16_energy",
)


def summarize(values: list[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64)
    if array.size == 0:
        return {
            "count": 0,
            "mean": float("nan"),
            "median": float("nan"),
            "p05": float("nan"),
            "p95": float("nan"),
        }
    return {
        "count": int(array.size),
        "mean": float(np.mean(array)),
        "median": float(np.median(array)),
        "p05": float(np.quantile(array, 0.05)),
        "p95": float(np.quantile(array, 0.95)),
    }


def load_labels(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {str(record["group_id"]): record for record in payload["records"]}


def load_residuals(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            sample_name = str(row["sample_name"])
            if sample_name in rows:
                raise ValueError(f"duplicate residual row: {sample_name}")
            if int(row.get("cycle_count", -1)) != 4 or len(row.get("cycles", [])) != 4:
                raise ValueError(f"expected four cycles for {sample_name}")
            if any("feature_error" in cycle for cycle in row["cycles"]):
                raise ValueError(f"residual feature error for {sample_name}")
            observed = {cycle.get("residual", {}).get("transition") for cycle in row["cycles"]}
            if not {"c1_to_c2", "c2_to_c3", "c3_to_c4"}.issubset(observed):
                raise ValueError(f"missing residual transition for {sample_name}: {observed}")
            rows[sample_name] = row
    return rows


def correlation(left: list[float], right: list[float]) -> float | None:
    if len(left) < 3 or np.std(left) == 0 or np.std(right) == 0:
        return None
    return float(np.corrcoef(np.asarray(left), np.asarray(right))[0, 1])


def partial_correlation(
    left: list[float], right: list[float], control: list[float]
) -> float | None:
    """Correlation after linear residualization against one control variable."""
    if len(left) < 3 or len(left) != len(right) or len(left) != len(control):
        return None
    x = np.asarray(control, dtype=np.float64)
    design = np.column_stack([np.ones_like(x), x])
    left_residual = np.asarray(left, dtype=np.float64) - design @ np.linalg.lstsq(
        design, np.asarray(left, dtype=np.float64), rcond=None
    )[0]
    right_residual = np.asarray(right, dtype=np.float64) - design @ np.linalg.lstsq(
        design, np.asarray(right, dtype=np.float64), rcond=None
    )[0]
    return correlation(left_residual.tolist(), right_residual.tolist())


def analyze(residual_path: Path, labels_path: Path) -> dict[str, Any]:
    labels = load_labels(labels_path)
    residuals = load_residuals(residual_path)
    if set(labels) != set(residuals):
        raise ValueError(f"coverage mismatch: labels={len(labels)} residuals={len(residuals)}")
    transition_rows: dict[str, dict[str, Any]] = {}
    for transition in TRANSITIONS:
        transition_rows[transition] = next(
            cycle["residual"]
            for row in residuals.values()
            for cycle in row["cycles"]
            if cycle.get("residual", {}).get("transition") == transition
        )

    summaries: dict[str, Any] = {}
    for transition in TRANSITIONS:
        summaries[transition] = {}
        for field in RESIDUAL_FIELDS:
            values = [
                float(
                    next(
                        cycle["residual"][field]
                        for cycle in row["cycles"]
                        if cycle.get("residual", {}).get("transition") == transition
                    )
                )
                for row in residuals.values()
            ]
            summaries[transition][field] = summarize(values)

    subgroup_summary: dict[str, Any] = {}
    for subgroup, predicate in (
        ("hard_joint", lambda record: bool(record["labels"]["hard_c2_vs_c4s5_joint_0p05"])),
        ("nonhard_joint", lambda record: not bool(record["labels"]["hard_c2_vs_c4s5_joint_0p05"])),
    ):
        subgroup_summary[subgroup] = {"record_count": 0, "transitions": {}}
        selected = [group_id for group_id, record in labels.items() if predicate(record)]
        subgroup_summary[subgroup]["record_count"] = len(selected)
        for transition in TRANSITIONS:
            subgroup_summary[subgroup]["transitions"][transition] = {
                field: summarize(
                    [
                        float(
                            next(
                                cycle["residual"][field]
                                for cycle in residuals[group_id]["cycles"]
                                if cycle.get("residual", {}).get("transition") == transition
                            )
                        )
                        for group_id in selected
                    ]
                )
                for field in RESIDUAL_FIELDS
            }

    c2_delta = [
        float(labels[group_id]["labels"]["delta_c2s2_vs_c4s5_all_atom_lddt"])
        for group_id in residuals
    ]
    def sequence_length(group_id: str) -> int:
        record = labels[group_id]
        if record.get("sequence_length") is not None:
            return int(record["sequence_length"])
        features = record.get("features", {})
        log_length = features.get("log_length")
        if log_length is None:
            raise ValueError(f"missing sequence length for {group_id}")
        return int(round(math.exp(float(log_length))))

    lengths = [sequence_length(group_id) for group_id in residuals]
    correlations = {}
    for transition in ("c2_to_c3", "c3_to_c4"):
        correlations[transition] = {
            field: correlation(
                [
                    float(
                        next(
                            cycle["residual"][field]
                            for cycle in residuals[group_id]["cycles"]
                            if cycle.get("residual", {}).get("transition") == transition
                        )
                    )
                    for group_id in residuals
                ],
                c2_delta,
            )
            for field in (
                "single_delta_fro_norm",
                "single_delta_residue_norm_mean",
                "pair_delta_fro_norm",
                "pair_delta_pair_norm_mean",
                "pair_delta_pooled_spatial_rank8_energy",
            )
        }
        correlations[transition]["length_controlled"] = {
            field: partial_correlation(
                [
                    float(
                        next(
                            cycle["residual"][field]
                            for cycle in residuals[group_id]["cycles"]
                            if cycle.get("residual", {}).get("transition") == transition
                        )
                    )
                    for group_id in residuals
                ],
                c2_delta,
                lengths,
            )
            for field in (
                "single_delta_fro_norm",
                "single_delta_residue_norm_mean",
                "pair_delta_fro_norm",
                "pair_delta_pair_norm_mean",
                "pair_delta_pooled_spatial_rank8_energy",
            )
        }

    length_bands = ((20, 128), (128, 256), (256, 512), (512, 1025))
    length_stratified: dict[str, Any] = {}
    for lower, upper in length_bands:
        group_ids = [
            group_id
            for group_id in residuals
            if lower <= sequence_length(group_id) < upper
        ]
        band_name = f"{lower}_{upper - 1}"
        length_stratified[band_name] = {
            "record_count": len(group_ids),
            "hard_joint_count": sum(
                bool(labels[group_id]["labels"]["hard_c2_vs_c4s5_joint_0p05"])
                for group_id in group_ids
            ),
            "transitions": {
                transition: {
                    field: summarize(
                        [
                            float(
                                next(
                                    cycle["residual"][field]
                                    for cycle in residuals[group_id]["cycles"]
                                    if cycle.get("residual", {}).get("transition") == transition
                                )
                            )
                            for group_id in group_ids
                        ]
                    )
                    for field in (
                        "single_delta_residue_norm_mean",
                        "pair_delta_pair_norm_mean",
                        "pair_delta_pooled_spatial_rank8_energy",
                    )
                }
                for transition in TRANSITIONS
            },
        }

    return {
        "scope": "temporal_dev_v1 only; frozen temporal test was not read",
        "record_count": len(residuals),
        "hard_joint_count": int(
            sum(bool(record["labels"]["hard_c2_vs_c4s5_joint_0p05"]) for record in labels.values())
        ),
        "residual_file": str(residual_path),
        "label_file": str(labels_path),
        "transitions": summaries,
        "subgroups": subgroup_summary,
        "correlations_with_c2_all_atom_delta": correlations,
        "length_stratified": length_stratified,
    }


def write_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Stage 1A Recycle Residual Characterization",
        "",
        result["scope"] + ".",
        "",
        f"Records: {result['record_count']}; joint hard targets: {result['hard_joint_count']}.",
        "Only compact hook summaries are used; full Pairformer tensors are not stored.",
        "",
        "## Residual Magnitudes",
        "",
        "| transition | single Fro norm median | pair Fro norm median | "
        "pair spatial rank-8 energy median | local (<=8) energy median |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for transition, fields in result["transitions"].items():
        lines.append(
            f"| {transition} | {fields['single_delta_fro_norm']['median']:.4g} | "
            f"{fields['pair_delta_fro_norm']['median']:.4g} | "
            f"{fields['pair_delta_pooled_spatial_rank8_energy']['median']:.4f} | "
            f"{fields['pair_delta_energy_band_8_fraction']['median']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Easy/Hard Comparison",
            "",
            "| subgroup | count | transition | single norm median | pair norm median |",
            "| --- | ---: | --- | ---: | ---: |",
        ]
    )
    for subgroup, data in result["subgroups"].items():
        for transition, fields in data["transitions"].items():
            lines.append(
                f"| {subgroup} | {data['record_count']} | {transition} | "
                f"{fields['single_delta_fro_norm']['median']:.4g} | "
                f"{fields['pair_delta_fro_norm']['median']:.4g} |"
            )
    lines.extend(
        [
            "",
            "## Correlation With c2 All-Atom Degradation",
            "",
            "| transition | single norm | pair norm | spatial rank-8 energy |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for transition, fields in result["correlations_with_c2_all_atom_delta"].items():
        lines.append(
            f"| {transition} | {fields['single_delta_fro_norm']} | "
            f"{fields['pair_delta_fro_norm']} | "
            f"{fields['pair_delta_pooled_spatial_rank8_energy']} |"
        )
    lines.extend(
        [
            "",
            "Length-controlled correlations are reported in the JSON under "
            "`correlations_with_c2_all_atom_delta.*.length_controlled`; pair "
            "norm means and residue-normalized single norms are less sensitive "
            "to the raw L and L^2 scaling than Frobenius norms.",
            "",
            "## Length-Stratified Pair Residual Means",
            "",
            "| length band | records | hard | c1->c2 | c2->c3 | c3->c4 |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for band, data in result["length_stratified"].items():
        medians = [
            data["transitions"][transition]["pair_delta_pair_norm_mean"]["median"]
            for transition in TRANSITIONS
        ]
        lines.append(
            f"| {band} | {data['record_count']} | {data['hard_joint_count']} | "
            f"{medians[0]:.3f} | {medians[1]:.3f} | {medians[2]:.3f} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--residuals", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-markdown", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.residuals, args.labels)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    write_markdown(args.output_markdown, result)
    print(
        json.dumps(
            {"record_count": result["record_count"], "hard_joint_count": result["hard_joint_count"]}
        )
    )


if __name__ == "__main__":
    main()
