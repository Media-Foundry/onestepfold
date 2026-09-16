#!/usr/bin/env python3
"""Merge deterministic ESMC cache partitions without rewriting tensors."""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
from typing import Any


def read_jsonl_gz(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl_gz(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed:
            for row in sorted(rows, key=lambda item: str(item["group_id"])):
                compressed.write((json.dumps(row, sort_keys=True) + "\n").encode())


def merge(parts_root: Path, groups_path: Path) -> dict[str, Any]:
    expected = {str(row["group_id"]) for row in read_jsonl_gz(groups_path)}
    parts = sorted(path for path in parts_root.glob("part-*") if path.is_dir())
    if not parts:
        raise ValueError(f"no cache partitions found under {parts_root}")
    specs = [json.loads((part / "feature_spec.json").read_text()) for part in parts]
    canonical_spec = specs[0]
    if any(spec != canonical_spec for spec in specs[1:]):
        raise ValueError("feature specs differ across cache partitions")

    rows: list[dict[str, Any]] = []
    summaries = []
    for part in parts:
        summaries.append(json.loads((part / "summary.json").read_text()))
        for row in read_jsonl_gz(part / "manifest.jsonl.gz"):
            row["shard"] = str(Path(part.name) / str(row["shard"]))
            rows.append(row)
    actual = [str(row["group_id"]) for row in rows]
    if len(set(actual)) != len(actual):
        raise ValueError("duplicate group IDs across cache partitions")
    if set(actual) != expected:
        raise ValueError(
            f"group coverage mismatch: expected={len(expected)} actual={len(set(actual))}"
        )

    (parts_root / "feature_spec.json").write_text(
        json.dumps(canonical_spec, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    write_jsonl_gz(parts_root / "manifest.jsonl.gz", rows)
    summary = {
        "groups_expected": len(expected),
        "groups_processed": len(rows),
        "total_residues": sum(int(item["total_residues"]) for item in summaries),
        "shard_count": sum(int(item["shard_count"]) for item in summaries),
        "partition_count": len(parts),
        "parts": [part.name for part in parts],
        "feature_variant": canonical_spec["feature_variant"],
        "model_id": canonical_spec["model_id"],
        "hf_revision": canonical_spec["hf_revision"],
        "code_revision": canonical_spec["code_revision"],
        "dtype": canonical_spec["dtype"],
    }
    (parts_root / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parts-root", type=Path, required=True)
    parser.add_argument("--groups", type=Path, required=True)
    args = parser.parse_args()
    merge(args.parts_root, args.groups)


if __name__ == "__main__":
    main()
