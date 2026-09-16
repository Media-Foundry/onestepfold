#!/usr/bin/env python3
"""Summarize completed Protenix Stage 0 runs.

The script intentionally reads only lightweight prediction metadata and run logs.
Large CIF/JSON structure outputs stay on the compute filesystem.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
from pathlib import Path
from typing import Any


SETTING_RE = re.compile(r"^c(?P<cycles>\d+)_s(?P<steps>\d+)$")
WALL_RE = re.compile(
    r"Elapsed \(wall clock\) time \([^)]*\):\s*(?P<value>\d+(?::\d+){0,2}(?:\.\d+)?)"
)
RSS_RE = re.compile(r"Maximum resident set size \(kbytes\):\s*(?P<value>\d+)")
EXIT_RE = re.compile(r"Exit status:\s*(?P<value>\d+)")
INTERNAL_RE = re.compile(r"Job completed in (?P<value>[0-9.]+)s")


def _number_summary(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"mean": None, "median": None, "p05": None, "p95": None}
    ordered = sorted(values)

    def percentile(fraction: float) -> float:
        index = min(len(ordered) - 1, round(fraction * (len(ordered) - 1)))
        return float(ordered[index])

    return {
        "mean": float(statistics.fmean(values)),
        "median": float(statistics.median(values)),
        "p05": percentile(0.05),
        "p95": percentile(0.95),
    }


def _last_float(pattern: re.Pattern[str], text: str) -> float | None:
    matches = list(pattern.finditer(text))
    return float(matches[-1].group("value")) if matches else None


def _last_int(pattern: re.Pattern[str], text: str) -> int | None:
    matches = list(pattern.finditer(text))
    return int(matches[-1].group("value")) if matches else None


def _wall_seconds(text: str) -> float | None:
    matches = list(WALL_RE.finditer(text))
    if not matches:
        return None
    parts = [float(part) for part in matches[-1].group("value").split(":")]
    seconds = 0.0
    for part in parts:
        seconds = seconds * 60.0 + part
    return seconds


def summarize_setting(path: Path, expected_targets: int | None = None) -> dict[str, Any]:
    match = SETTING_RE.match(path.name)
    if not match:
        raise ValueError(f"unexpected setting directory name: {path.name}")
    log_path = path / "seed-101" / "run.log"
    log_text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
    confidence_paths = sorted(
        (path / "seed-101").rglob("*_summary_confidence_sample_0.json")
    )
    plddt: list[float] = []
    ptm: list[float] = []
    gpde: list[float] = []
    parse_errors = 0
    clash_count = 0
    for confidence_path in confidence_paths:
        try:
            value = json.loads(confidence_path.read_text(encoding="utf-8"))
            plddt.append(float(value["plddt"]))
            ptm.append(float(value["ptm"]))
            gpde.append(float(value["gpde"]))
            clash_count += int(bool(value.get("has_clash", False)))
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            parse_errors += 1

    cif_count = sum(1 for _ in (path / "seed-101").rglob("*.cif"))
    json_count = sum(1 for _ in (path / "seed-101").rglob("*.json"))
    rss_kb = _last_int(RSS_RE, log_text)
    return {
        "setting": path.name,
        "cycles": int(match.group("cycles")),
        "steps": int(match.group("steps")),
        "expected_targets": expected_targets,
        "cif_count": cif_count,
        "json_count": json_count,
        "confidence_count": len(confidence_paths) - parse_errors,
        "confidence_parse_errors": parse_errors,
        "all_targets_have_cif": expected_targets is None or cif_count == expected_targets,
        "all_targets_have_confidence": expected_targets is None or len(confidence_paths) == expected_targets,
        "error_parts_empty": bool(re.search(r"Error parts:\s*\[\s*\]", log_text)),
        "exit_status": _last_int(EXIT_RE, log_text),
        "wall_seconds": _wall_seconds(log_text),
        "internal_seconds": _last_float(INTERNAL_RE, log_text),
        "max_rss_gib": rss_kb / (1024**2) if rss_kb is not None else None,
        "has_clash_count": clash_count,
        "plddt": _number_summary(plddt),
        "ptm": _number_summary(ptm),
        "gpde": _number_summary(gpde),
    }


def summarize(root: Path, expected_targets: int | None = None) -> dict[str, Any]:
    rows = [
        summarize_setting(path, expected_targets)
        for path in sorted(root.glob("c*_s*"))
        if path.is_dir() and SETTING_RE.match(path.name)
    ]
    return {
        "root": str(root),
        "setting_count": len(rows),
        "expected_targets_per_setting": expected_targets,
        "settings": rows,
    }


def write_csv(path: Path, summary: dict[str, Any]) -> None:
    rows = summary["settings"]
    fields = [
        "setting", "cycles", "steps", "expected_targets", "cif_count", "json_count",
        "confidence_count", "confidence_parse_errors", "all_targets_have_cif",
        "all_targets_have_confidence", "error_parts_empty", "exit_status", "wall_seconds",
        "internal_seconds", "max_rss_gib", "has_clash_count",
        "plddt_mean", "plddt_median", "plddt_p05", "plddt_p95",
        "ptm_mean", "ptm_median", "ptm_p05", "ptm_p95",
        "gpde_mean", "gpde_median", "gpde_p05", "gpde_p95",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            flat = {key: row.get(key) for key in fields if key in row}
            for metric in ("plddt", "ptm", "gpde"):
                for stat in ("mean", "median", "p05", "p95"):
                    flat[f"{metric}_{stat}"] = row[metric][stat]
            writer.writerow(flat)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--expected-targets", type=int, default=None)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    args = parser.parse_args()
    summary = summarize(args.root, args.expected_targets)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_csv(args.output_csv, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
