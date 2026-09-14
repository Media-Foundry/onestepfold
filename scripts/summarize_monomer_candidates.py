#!/usr/bin/env python3
"""Summarize the catalog-only monomer candidate table."""

from __future__ import annotations

import argparse
import collections
import gzip
import json
from pathlib import Path
from typing import Any


def _quantiles(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"p05": None, "p25": None, "p50": None, "p75": None, "p95": None}
    ordered = sorted(values)
    return {
        f"p{int(fraction * 100):02d}": ordered[
            min(len(ordered) - 1, int(round(fraction * (len(ordered) - 1))))
        ]
        for fraction in (0.05, 0.25, 0.5, 0.75, 0.95)
    }


def summarize(path: Path, cutoff: str = "2021-09-30") -> dict[str, Any]:
    methods: collections.Counter[str] = collections.Counter()
    date_buckets: collections.Counter[str] = collections.Counter()
    lengths: list[float] = []
    resolutions: list[float] = []
    missing_resolution = 0
    apo_like = 0
    total = 0
    unique_ids: set[str] = set()
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            total += 1
            pdb_id = str(row["pdb_id"])
            unique_ids.add(pdb_id)
            methods.update(row.get("experimental_methods", []))
            lengths.append(float(row["sequence_length"]))
            resolution = row.get("resolution_high_angstrom")
            if resolution is None:
                missing_resolution += 1
            else:
                resolutions.append(float(resolution))
            if "monomer_apo_like" in row.get("views", []):
                apo_like += 1
            release_date = row.get("initial_release_date")
            if not release_date:
                date_buckets["missing"] += 1
            elif str(release_date) <= cutoff:
                date_buckets["pre_or_on_cutoff"] += 1
            else:
                date_buckets["post_cutoff"] += 1
    return {
        "input": str(path),
        "entry_count": total,
        "unique_pdb_id_count": len(unique_ids),
        "duplicate_pdb_id_count": total - len(unique_ids),
        "apo_like_eligible_count": apo_like,
        "date_cutoff": cutoff,
        "release_date_counts": dict(sorted(date_buckets.items())),
        "method_counts": dict(sorted(methods.items())),
        "sequence_length_quantiles": _quantiles(lengths),
        "resolution_quantiles_angstrom": _quantiles(resolutions),
        "missing_resolution_count": missing_resolution,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cutoff", default="2021-09-30")
    args = parser.parse_args()
    summary = summarize(args.input, args.cutoff)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
