#!/usr/bin/env python3
"""Compute Stage 0D oracle recycle compute-quality frontiers."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

TOLERANCES = (0.005, 0.01, 0.02, 0.03, 0.05)
QUALITY_METRICS = ("tm_score_ca", "ca_lddt", "all_atom_lddt")


def load_setting(eval_root: Path, setting: str) -> dict[str, dict[str, Any]]:
    path = eval_root / f"{setting}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        str(record["group_id"]): record
        for record in payload.get("records", [])
        if record.get("status") == "ok"
    }


def setting_cost(setting: str) -> tuple[int, int]:
    cycle_text, step_text = setting.split("_")
    return int(cycle_text[1:]), int(step_text[1:])


def summarize(values: list[float]) -> dict[str, float | None]:
    finite = np.asarray([value for value in values if math.isfinite(value)], dtype=np.float64)
    if finite.size == 0:
        return {"mean": None, "median": None, "p05": None, "p95": None}
    return {
        "mean": float(np.mean(finite)),
        "median": float(np.median(finite)),
        "p05": float(np.quantile(finite, 0.05)),
        "p95": float(np.quantile(finite, 0.95)),
    }


def evaluate_selection(
    selected: dict[str, str],
    records: dict[str, dict[str, dict[str, Any]]],
    anchor_setting: str,
) -> dict[str, Any]:
    anchor = records[anchor_setting]
    setting_counts = Counter(selected.values())
    cycle_counts = Counter(setting_cost(setting)[0] for setting in selected.values())
    cycles = [setting_cost(setting)[0] for setting in selected.values()]
    steps = [setting_cost(setting)[1] for setting in selected.values()]
    metric_results: dict[str, Any] = {}
    for metric in QUALITY_METRICS:
        values = [
            float(records[setting][group_id][metric]) for group_id, setting in selected.items()
        ]
        deltas = [
            float(records[setting][group_id][metric]) - float(anchor[group_id][metric])
            for group_id, setting in selected.items()
        ]
        metric_results[metric] = {
            "selected": summarize(values),
            "delta_vs_anchor": summarize(deltas),
            "fraction_delta_below_minus_0.01": float(np.mean(np.asarray(deltas) < -0.01)),
            "fraction_delta_below_minus_0.02": float(np.mean(np.asarray(deltas) < -0.02)),
            "fraction_delta_below_minus_0.05": float(np.mean(np.asarray(deltas) < -0.05)),
        }
    mean_cycles = float(np.mean(cycles))
    return {
        "target_count": len(selected),
        "setting_counts": dict(sorted(setting_counts.items())),
        "cycle_counts": {str(key): value for key, value in sorted(cycle_counts.items())},
        "mean_cycles": mean_cycles,
        "mean_structure_steps": float(np.mean(steps)),
        "pairformer_cycle_reduction_vs_c4": 1.0 - mean_cycles / 4.0,
        "metrics": metric_results,
    }


def oracle_policy(
    records: dict[str, dict[str, dict[str, Any]]],
    candidates: tuple[str, ...],
    anchor_setting: str,
    tolerance: float,
    selection_metrics: tuple[str, ...] = ("tm_score_ca",),
) -> dict[str, Any]:
    anchor = records[anchor_setting]
    common = sorted(set(anchor).intersection(*(set(records[setting]) for setting in candidates)))
    selected: dict[str, str] = {}
    for group_id in common:
        for setting in candidates:
            acceptable = all(
                float(records[setting][group_id][metric])
                >= float(anchor[group_id][metric]) - tolerance
                for metric in selection_metrics
            )
            if acceptable:
                selected[group_id] = setting
                break
        else:
            selected[group_id] = anchor_setting
    result = evaluate_selection(selected, records, anchor_setting)
    result.update(
        {
            "quality_tolerance": tolerance,
            "selection_metrics": list(selection_metrics),
            "candidates_in_order": list(candidates),
            "anchor_setting": anchor_setting,
        }
    )
    return result


def fixed_policy(
    records: dict[str, dict[str, dict[str, Any]]], setting: str, anchor_setting: str
) -> dict[str, Any]:
    common = sorted(set(records[setting]) & set(records[anchor_setting]))
    result = evaluate_selection({group_id: setting for group_id in common}, records, anchor_setting)
    result.update({"setting": setting, "anchor_setting": anchor_setting})
    return result


def analyze(eval_root: Path) -> dict[str, Any]:
    required = ("c1_s1", "c2_s1", "c2_s2", "c4_s1", "c4_s5")
    records = {setting: load_setting(eval_root, setting) for setting in required}
    policies = {
        "practical_1_or_4": {
            "description": "Choose c1_s1 or c4_s5 against the c4_s5 anchor.",
            "anchor_setting": "c4_s5",
            "candidates": ("c1_s1", "c4_s5"),
            "selection_metrics": ("tm_score_ca",),
        },
        "practical_1_2_4": {
            "description": "Choose c1_s1, c2_s2, or c4_s5 against the c4_s5 anchor.",
            "anchor_setting": "c4_s5",
            "candidates": ("c1_s1", "c2_s2", "c4_s5"),
            "selection_metrics": ("tm_score_ca",),
        },
        "practical_joint_1_2_4": {
            "description": (
                "Choose c1_s1, c2_s2, or c4_s5 while protecting both TM-style score and "
                "all-atom lDDT against the c4_s5 anchor."
            ),
            "anchor_setting": "c4_s5",
            "candidates": ("c1_s1", "c2_s2", "c4_s5"),
            "selection_metrics": ("tm_score_ca", "all_atom_lddt"),
        },
        "step1_recycle_only_1_2_4": {
            "description": (
                "Hold structure steps at one and choose c1_s1, c2_s1, or c4_s1 against c4_s1."
            ),
            "anchor_setting": "c4_s1",
            "candidates": ("c1_s1", "c2_s1", "c4_s1"),
            "selection_metrics": ("tm_score_ca",),
        },
        "step1_joint_recycle_only_1_2_4": {
            "description": (
                "Hold structure steps at one and protect both TM-style score and all-atom lDDT "
                "against c4_s1."
            ),
            "anchor_setting": "c4_s1",
            "candidates": ("c1_s1", "c2_s1", "c4_s1"),
            "selection_metrics": ("tm_score_ca", "all_atom_lddt"),
        },
    }
    frontiers: dict[str, Any] = {}
    for name, policy in policies.items():
        frontiers[name] = {
            "description": policy["description"],
            "points": [
                oracle_policy(
                    records,
                    policy["candidates"],
                    policy["anchor_setting"],
                    tolerance,
                    policy["selection_metrics"],
                )
                for tolerance in TOLERANCES
            ],
        }
    return {
        "scope": "temporal_dev_v1 only; frozen temporal test was not read",
        "oracle_interpretation": (
            "Lower bound assuming cycle states can be continued and reused. Selection uses GT "
            "quality and is not a realizable router. Practical policies also vary structure-step "
            "count."
        ),
        "tolerances": list(TOLERANCES),
        "fixed_baselines_vs_c4_s5": {
            setting: fixed_policy(records, setting, "c4_s5")
            for setting in ("c1_s1", "c2_s2", "c4_s5")
        },
        "fixed_baselines_step1_vs_c4_s1": {
            setting: fixed_policy(records, setting, "c4_s1")
            for setting in ("c1_s1", "c2_s1", "c4_s1")
        },
        "oracle_frontiers": frontiers,
    }


def fmt(value: float | None, digits: int = 4) -> str:
    return "NA" if value is None else f"{value:.{digits}f}"


def write_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Stage 0D Oracle Recycle Frontier",
        "",
        result["scope"] + ".",
        "",
        (
            "Oracle points use experimental GT to select the shallowest acceptable setting. "
            "They are an unattainable upper bound, not a router result. Mean-cycle savings assume "
            "intermediate recycle states are reused rather than recomputed."
        ),
        "",
        "## Fixed Baselines",
        "",
        (
            "| setting | mean cycles | mean TM | mean delta TM vs c4_s5 | "
            "P(delta TM < -0.05) | mean all-atom lDDT |"
        ),
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for setting, item in result["fixed_baselines_vs_c4_s5"].items():
        tm = item["metrics"]["tm_score_ca"]
        lddt = item["metrics"]["all_atom_lddt"]
        lines.append(
            f"| {setting} | {item['mean_cycles']:.3f} | {fmt(tm['selected']['mean'])} | "
            f"{fmt(tm['delta_vs_anchor']['mean'])} | {tm['fraction_delta_below_minus_0.05']:.3f} | "
            f"{fmt(lddt['selected']['mean'])} |"
        )
    for name, frontier in result["oracle_frontiers"].items():
        lines.extend(
            [
                "",
                f"## `{name}`",
                "",
                frontier["description"],
                "",
                (
                    "| quality tolerance | protected metrics | c1 / c2 / c4 (%) | mean cycles | "
                    "cycle reduction vs c4 | mean steps | mean delta TM | "
                    "P(delta TM < -0.05) | mean delta all-atom lDDT |"
                ),
                "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for point in frontier["points"]:
            total = point["target_count"]
            cycle_counts = point["cycle_counts"]
            shares = "/".join(
                f"{100.0 * cycle_counts.get(str(cycle), 0) / total:.1f}" for cycle in (1, 2, 4)
            )
            tm = point["metrics"]["tm_score_ca"]
            lddt = point["metrics"]["all_atom_lddt"]
            lines.append(
                f"| {point['quality_tolerance']:.3f} | "
                f"{', '.join(point['selection_metrics'])} | {shares} | "
                f"{point['mean_cycles']:.3f} | "
                f"{100.0 * point['pairformer_cycle_reduction_vs_c4']:.1f}% | "
                f"{point['mean_structure_steps']:.3f} | "
                f"{fmt(tm['delta_vs_anchor']['mean'])} | "
                f"{tm['fraction_delta_below_minus_0.05']:.3f} | "
                f"{fmt(lddt['delta_vs_anchor']['mean'])} |"
            )
    lines.extend(
        [
            "",
            (
                "The `practical` frontier mixes cycle and structure-step settings and therefore "
                "measures the best existing operating path, not a pure recycle effect. The "
                "`step1_recycle_only` frontier holds structure NFE at one and uses `c4_s1` as its "
                "anchor."
            ),
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-root", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-markdown", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.eval_root)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    write_markdown(args.output_markdown, result)
    print(
        json.dumps(
            {name: value["points"] for name, value in result["oracle_frontiers"].items()}, indent=2
        )
    )


if __name__ == "__main__":
    main()
