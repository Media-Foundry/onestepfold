#!/usr/bin/env python3
"""Summarize timing records emitted by the Stage 0 timing overlay."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any


SETTINGS = ("c1_s1", "c1_s5", "c4_s1", "c4_s5")
FIELDS = ("model_forward_seconds", "pairformer_seconds", "diffusion_seconds", "confidence_seconds", "unattributed_model_seconds")


def _summary(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"mean": None, "median": None, "p05": None, "p95": None}
    values = sorted(values)
    return {
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "p05": values[min(len(values) - 1, round(0.05 * (len(values) - 1)))],
        "p95": values[min(len(values) - 1, round(0.95 * (len(values) - 1)))],
    }


def summarize(root: Path) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for setting in SETTINGS:
        path = root / setting / "seed-101" / "timing_components.jsonl"
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.exists() else []
        metrics = {field: _summary([float(record[field]) for record in records if record.get(field) is not None]) for field in FIELDS}
        total = metrics["model_forward_seconds"]["mean"]
        fractions = {
            field.removesuffix("_seconds"): (metrics[field]["mean"] / total if total else None)
            for field in ("pairformer_seconds", "diffusion_seconds", "confidence_seconds", "unattributed_model_seconds")
        }
        result[setting] = {"record_count": len(records), "metrics": metrics, "fractions_of_model_forward": fractions}
    return {"settings": result, "timing_scope": "GPU-synchronized model forward; excludes model load and CIF/JSON dump"}


def _fmt(value: float | None, digits: int = 4) -> str:
    return "NA" if value is None else f"{value:.{digits}f}"


def write_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Stage 0C Internal Timing",
        "",
        "These values come from GPU-synchronized wrappers around the pinned Protenix model. They cover model forward only; model load, input preprocessing, confidence-file serialization, and CIF writing are excluded.",
        "",
        "| setting | n | model mean / median (s) | pairformer mean / median (s) | diffusion mean / median (s) | confidence mean / median (s) | pairformer fraction | diffusion fraction |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for setting in SETTINGS:
        row = result["settings"].get(setting, {})
        metrics = row.get("metrics", {})
        fractions = row.get("fractions_of_model_forward", {})
        lines.append(
            f"| {setting} | {row.get('record_count', 0)} | {_fmt(metrics.get('model_forward_seconds', {}).get('mean'))} / {_fmt(metrics.get('model_forward_seconds', {}).get('median'))} | "
            f"{_fmt(metrics.get('pairformer_seconds', {}).get('mean'))} / {_fmt(metrics.get('pairformer_seconds', {}).get('median'))} | "
            f"{_fmt(metrics.get('diffusion_seconds', {}).get('mean'))} / {_fmt(metrics.get('diffusion_seconds', {}).get('median'))} | "
            f"{_fmt(metrics.get('confidence_seconds', {}).get('mean'))} / {_fmt(metrics.get('confidence_seconds', {}).get('median'))} | "
            f"{_fmt(fractions.get('pairformer'), 3)} | {_fmt(fractions.get('diffusion'), 3)} |"
        )
    lines.extend([
        "",
        "The four settings used the same 128-target prefix of `temporal_dev_v1`; timing is diagnostic and is not a final throughput benchmark. The c1_s5, c4_s1, and c4_s5 jobs shared one A800 node, so their paired comparisons are the cleanest same-node timing comparison.",
        "",
        "On that same node, c1_s5 -> c4_s5 increased median pairformer time by about 0.585 s and median model-forward time by about 0.587 s. c4_s1 -> c4_s5 increased median diffusion time by about 0.053 s while median pairformer time changed by about 0.002 s.",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-markdown", type=Path, required=True)
    args = parser.parse_args()
    result = summarize(args.root)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(args.output_markdown, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
