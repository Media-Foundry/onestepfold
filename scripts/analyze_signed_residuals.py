#!/usr/bin/env python3
"""Summarize signed recycle-residual direction diagnostics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np


def _rows(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _summary(values: list[float]) -> dict[str, float | int]:
    array = np.asarray(values, dtype=np.float64)
    array = array[np.isfinite(array)]
    if not len(array):
        return {
            "count": 0,
            "mean": float("nan"),
            "median": float("nan"),
            "p05": float("nan"),
            "p95": float("nan"),
        }
    return {
        "count": int(len(array)),
        "mean": float(np.mean(array)),
        "median": float(np.median(array)),
        "p05": float(np.quantile(array, 0.05)),
        "p95": float(np.quantile(array, 0.95)),
    }


def analyze(path: Path) -> dict[str, Any]:
    transition_values: dict[str, dict[str, list[float]]] = {}
    sketch_counts: dict[str, int] = {}
    for row in _rows(path):
        for cycle in row.get("cycles", []):
            residual = cycle.get("residual", {})
            transition = residual.get("transition")
            if not transition:
                continue
            fields = transition_values.setdefault(transition, {})
            for key in ("single_delta_direction_cosine", "pair_delta_direction_cosine"):
                if key in residual:
                    fields.setdefault(key, []).append(float(residual[key]))
            if residual.get("signed_pair_delta_sketch_path"):
                sketch_counts[transition] = sketch_counts.get(transition, 0) + 1
    return {
        "residual_file": str(path),
        "transitions": {
            transition: {key: _summary(values) for key, values in fields.items()}
            for transition, fields in sorted(transition_values.items())
        },
        "signed_pair_delta_sketch_counts": sketch_counts,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--residuals", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.residuals)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
