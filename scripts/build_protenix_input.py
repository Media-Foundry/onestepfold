#!/usr/bin/env python3
"""Convert a frozen Stage 0 manifest into Protenix's list-of-targets JSON."""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
from typing import Any

STANDARD_AMINO_ACIDS = set("ACDEFGHIKLMNPQRSTVWYX")


def _read_manifest(path: Path, limit: int | None) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle if line.strip()]
    rows.sort(key=lambda row: str(row["stage0_group_id"]))
    return rows if limit is None else rows[:limit]


def build_input(manifest: Path, output: Path, index_output: Path, limit: int | None = None) -> int:
    rows = _read_manifest(manifest, limit)
    targets = []
    index_rows = []
    seen: set[str] = set()
    for row in rows:
        group_id = str(row["stage0_group_id"])
        sequence = str(row.get("sequence", ""))
        if group_id in seen:
            raise ValueError(f"duplicate Stage 0 group: {group_id}")
        if not sequence or any(letter not in STANDARD_AMINO_ACIDS for letter in sequence):
            raise ValueError(f"unsupported protein sequence for {group_id}")
        if len(sequence) > 1024:
            raise ValueError(f"sequence exceeds Stage 0 max length: {group_id}")
        seen.add(group_id)
        targets.append(
            {
                "name": group_id,
                "sequences": [{"proteinChain": {"sequence": sequence, "count": 1}}],
            }
        )
        index_rows.append(
            {
                "name": group_id,
                "group_id": group_id,
                "pdb_id": row.get("pdb_id"),
                "sample_id": row.get("sample_id"),
                "sequence_sha256": row.get("sequence_sha256"),
                "sequence_length": len(sequence),
                "stage0_view": row.get("stage0_view"),
            }
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(targets, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    index_output.parent.mkdir(parents=True, exist_ok=True)
    with index_output.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed:
            for row in index_rows:
                compressed.write((json.dumps(row, sort_keys=True) + "\n").encode("utf-8"))
    print(json.dumps({"manifest": str(manifest), "targets": len(targets), "output": str(output)}))
    return len(targets)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--index-output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    build_input(args.manifest, args.output, args.index_output, args.limit)


if __name__ == "__main__":
    main()
