#!/usr/bin/env python3
"""Estimate signed sketch spatial rank without materializing pair tensors."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

TRANSITIONS = ("c1_to_c2", "c2_to_c3", "c3_to_c4")


def _summary(values: list[float]) -> dict[str, float | int]:
    array = np.asarray(values, dtype=np.float64)
    return {
        "count": int(array.size),
        "median": float(np.median(array)),
        "p05": float(np.quantile(array, 0.05)),
        "p95": float(np.quantile(array, 0.95)),
    }


def analyze(root: Path) -> dict[str, Any]:
    transitions: dict[str, Any] = {}
    for transition in TRANSITIONS:
        paths = sorted(root.glob(f"*_{transition}_pair_delta.npz"))
        rank_values = {rank: [] for rank in (1, 4, 8, 16)}
        for path in paths:
            sketch = np.asarray(np.load(path)["sketch"], dtype=np.float32)
            matrix = sketch.reshape(sketch.shape[0], -1)
            singular = np.linalg.svd(matrix, compute_uv=False)
            energy = np.square(singular)
            total = max(float(energy.sum()), 1e-12)
            cumulative = np.cumsum(energy) / total
            for rank in rank_values:
                rank_values[rank].append(float(cumulative[min(rank, len(cumulative)) - 1]))
        transitions[transition] = {
            "file_count": len(paths),
            "spatial_rank_energy": {
                f"rank{rank}": _summary(values) for rank, values in rank_values.items()
            },
        }
    return {"sketch_root": str(root), "transitions": transitions}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sketch-root", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.sketch_root)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
