#!/usr/bin/env python3
"""Validate matching c2/c4 Protenix teacher-pair outputs."""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
from typing import Any


def _metadata(input_root: Path) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for path in sorted(input_root.glob("shard-*/metadata.jsonl.gz")):
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            rows.extend((str(row["group_id"]), path.parent.name) for row in map(json.loads, handle))
    return rows


def _prediction(output_root: Path, setting: str, shard: str, group_id: str, seed: int) -> Path:
    return (
        output_root
        / setting
        / shard
        / f"seed-{seed}"
        / group_id
        / f"seed_{seed}"
        / "predictions"
        / f"{group_id}_sample_0.cif"
    )


def validate(
    input_root: Path, output_root: Path, settings: tuple[str, ...], seed: int
) -> dict[str, Any]:
    rows = _metadata(input_root)
    missing = {setting: [] for setting in settings}
    present = {setting: 0 for setting in settings}
    for group_id, shard in rows:
        for setting in settings:
            path = _prediction(output_root, setting, shard, group_id, seed)
            if path.is_file() and path.stat().st_size > 0:
                present[setting] += 1
            else:
                missing[setting].append({"group_id": group_id, "shard": shard, "path": str(path)})
    return {
        "input_record_count": len(rows),
        "settings": list(settings),
        "seed": seed,
        "present": present,
        "missing_counts": {setting: len(paths) for setting, paths in missing.items()},
        "missing_examples": {setting: paths[:10] for setting, paths in missing.items()},
        "complete": all(not paths for paths in missing.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=101)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.input_root, args.output_root, ("c2_s2", "c4_s2"), args.seed)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["complete"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
