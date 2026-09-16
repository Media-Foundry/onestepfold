#!/usr/bin/env python3
"""Aggregate per-setting Stage 0 GT-backed evaluation JSON files."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


SETTINGS = ("c1_s1", "c1_s2", "c1_s5", "c2_s1", "c2_s2", "c2_s5", "c4_s1", "c4_s2", "c4_s5")
METRICS = ("tm_score_ca", "ca_lddt", "all_atom_lddt", "ca_rmsd_angstrom", "backbone_rmsd_angstrom", "sidechain_rmsd_angstrom")


def _quantiles(values: list[float]) -> dict[str, float | None]:
    values = sorted(float(value) for value in values if math.isfinite(float(value)))
    if not values:
        return {"mean": None, "median": None, "p05": None, "p95": None}
    return {
        "mean": sum(values) / len(values),
        "median": values[len(values) // 2],
        "p05": values[min(len(values) - 1, round(0.05 * (len(values) - 1)))],
        "p95": values[min(len(values) - 1, round(0.95 * (len(values) - 1)))],
    }


def load_eval(root: Path) -> dict[str, dict[str, Any]]:
    result = {}
    for setting in SETTINGS:
        path = root / f"{setting}.json"
        if path.exists():
            result[setting] = json.loads(path.read_text(encoding="utf-8"))
    return result


def aggregate(root: Path) -> dict[str, Any]:
    evaluations = load_eval(root)
    setting_summary: dict[str, Any] = {}
    records_by_setting: dict[str, dict[str, dict[str, Any]]] = {}
    for setting, payload in evaluations.items():
        records = {str(record["group_id"]): record for record in payload.get("records", []) if record.get("status") == "ok"}
        records_by_setting[setting] = records
        setting_summary[setting] = {
            "manifest_count": payload.get("manifest_count"),
            "ok_count": payload.get("ok_count"),
            "error_count": payload.get("error_count"),
            "metrics": {
                metric: _quantiles([float(record[metric]) for record in records.values()])
                for metric in METRICS
            },
        }

    anchor = records_by_setting.get("c4_s5", {})
    paired: dict[str, Any] = {}
    for setting, records in records_by_setting.items():
        common = sorted(set(records) & set(anchor))
        if not common:
            continue
        deltas: dict[str, Any] = {}
        for metric in METRICS:
            values = [float(records[group][metric]) - float(anchor[group][metric]) for group in common]
            deltas[metric] = _quantiles(values)
            if metric == "tm_score_ca":
                deltas["tm_drop_lt_005"] = sum(value < -0.05 for value in values) / len(values)
                deltas["tm_drop_lt_010"] = sum(value < -0.10 for value in values) / len(values)
        paired[setting] = {"common_count": len(common), "deltas_vs_c4_s5": deltas}
    return {
        "settings_present": list(evaluations),
        "setting_summary": setting_summary,
        "paired_vs_c4_s5": paired,
    }


def _fmt(value: float | None, digits: int = 4) -> str:
    return "NA" if value is None else f"{value:.{digits}f}"


def write_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Stage 0B GT-Backed Evaluation",
        "",
        "Metrics use exact sequence-group pairing against the frozen `temporal_dev_v1` Stage B GT. Coordinates are Kabsch-aligned on common Cα atoms; lDDT uses reference atom pairs within 15 Å and the standard 0.5/1/2/4 Å thresholds.",
        "",
        "## Mean / Median Surface",
        "",
        "| cycles \\ steps | 1 TM / lDDT | 2 TM / lDDT | 5 TM / lDDT |",
        "| --- | ---: | ---: | ---: |",
    ]
    for cycles in (1, 2, 4):
        cells = []
        for steps in (1, 2, 5):
            setting = f"c{cycles}_s{steps}"
            metrics = result["setting_summary"].get(setting, {}).get("metrics", {})
            tm = metrics.get("tm_score_ca", {})
            lddt = metrics.get("all_atom_lddt", {})
            cells.append(f"{_fmt(tm.get('mean'))} / {_fmt(lddt.get('mean'))}")
        lines.append(f"| {cycles} | " + " | ".join(cells) + " |")
    lines.extend([
        "",
        "Values are mean `TM-score Cα / all-atom lDDT`; full quantiles and all metrics are in the JSON artifact.",
        "",
        "## Paired Degradation vs `c4_s5`",
        "",
        "| setting | common | median ΔTM | P(ΔTM < -0.05) | P(ΔTM < -0.10) | median Δall-atom lDDT |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ])
    for setting in SETTINGS:
        if setting not in result["paired_vs_c4_s5"]:
            continue
        row = result["paired_vs_c4_s5"][setting]
        delta = row["deltas_vs_c4_s5"]
        lines.append(
            f"| {setting} | {row['common_count']} | {_fmt(delta['tm_score_ca']['median'])} | "
            f"{_fmt(delta['tm_drop_lt_005'], 3)} | {_fmt(delta['tm_drop_lt_010'], 3)} | "
            f"{_fmt(delta['all_atom_lddt']['median'])} |"
        )
    lines.extend([
        "",
        "This is a collapse-surface diagnostic, not a final benchmark: the dev view was used to select operating points, and the frozen temporal test remains untouched.",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-markdown", type=Path, required=True)
    args = parser.parse_args()
    result = aggregate(args.input_root)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(args.output_markdown, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
