#!/usr/bin/env python3
"""Select deterministic pre-cutoff teacher-pair records.

The output is a set of Protenix input JSON files plus JSONL metadata. Each
exact sequence group contributes at most one record, preventing repeated PDB
records from dominating the c2->c4 teacher corpus.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any

STANDARD_PROTEIN_ALPHABET = frozenset("ACDEFGHIKLMNPQRSTVWY")


def read_jsonl_gz(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def record_key(row: dict[str, Any]) -> tuple[Any, ...]:
    resolution = row.get("resolution_high_angstrom")
    return (
        0 if row.get("hq_eval_valid") else 1,
        float(resolution) if resolution is not None else float("inf"),
        -int(row.get("sequence_length", 0)),
        str(row.get("sample_id", "")),
    )


def shard_for(group_id: str, shard_count: int) -> int:
    if shard_count < 1:
        raise ValueError("shard_count must be positive")
    return int(hashlib.sha256(group_id.encode("ascii")).hexdigest()[:8], 16) % shard_count


def select_records(rows: list[dict[str, Any]], limit: int | None) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        # The frozen train artifact is already train-only and omits a split
        # field; accept an explicit split field when reading a combined table.
        if row.get("split") is not None and row.get("split") != "train":
            continue
        grouped.setdefault(str(row["group_id"]), []).append(row)
    selected = [min(members, key=record_key) for members in grouped.values()]
    selected.sort(key=lambda row: str(row["group_id"]))
    return selected if limit is None else selected[:limit]


def attach_sequences(
    rows: list[dict[str, Any]], group_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    sequences = {str(row["group_id"]): str(row["sequence"]) for row in group_rows}
    attached: list[dict[str, Any]] = []
    for row in rows:
        group_id = str(row["group_id"])
        sequence = sequences.get(group_id)
        if not sequence:
            raise ValueError(f"missing sequence for selected group {group_id}")
        enriched = dict(row)
        enriched["sequence"] = sequence
        attached.append(enriched)
    return attached


def filter_supported_sequences(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Keep sequences representable by Protenix's canonical protein parser."""
    supported: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for row in rows:
        sequence = str(row["sequence"])
        unsupported = sorted(set(sequence) - STANDARD_PROTEIN_ALPHABET)
        if unsupported:
            excluded.append(
                {
                    "group_id": str(row["group_id"]),
                    "sample_id": str(row.get("sample_id", "")),
                    "sequence_length": len(sequence),
                    "unsupported_symbols": unsupported,
                    "reason": "protenix_canonical_protein_alphabet",
                }
            )
        else:
            supported.append(row)
    return supported, excluded


def write_jsonl_gz(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed:
            for row in rows:
                compressed.write((json.dumps(row, sort_keys=True) + "\n").encode("utf-8"))


def build_inputs(
    rows: list[dict[str, Any]],
    output_root: Path,
    shard_count: int,
    excluded: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    output_root.mkdir(parents=True, exist_ok=True)
    buckets: list[list[dict[str, Any]]] = [[] for _ in range(shard_count)]
    for row in rows:
        buckets[shard_for(str(row["group_id"]), shard_count)].append(row)
    shard_rows: list[dict[str, Any]] = []
    for shard_id, members in enumerate(buckets):
        members.sort(key=lambda row: str(row["group_id"]))
        shard_dir = output_root / f"shard-{shard_id:04d}"
        shard_dir.mkdir(parents=True, exist_ok=True)
        metadata_path = shard_dir / "metadata.jsonl.gz"
        write_jsonl_gz(metadata_path, members)
        targets = [
            {
                "name": str(row["group_id"]),
                "sequences": [{"proteinChain": {"sequence": str(row["sequence"]), "count": 1}}],
            }
            for row in members
        ]
        input_path = shard_dir / "input.json"
        input_path.write_text(
            json.dumps(targets, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        shard_rows.append(
            {
                "shard_id": shard_id,
                "count": len(members),
                "input_json": str(input_path),
                "metadata_jsonl": str(metadata_path),
            }
        )
    manifest = {
        "record_count": len(rows),
        "shard_count": shard_count,
        "shards": shard_rows,
        "selection": "one deterministic best train-valid record per exact sequence group",
        "sequence_alphabet": "ACDEFGHIKLMNPQRSTVWY",
        "excluded_unsupported_sequence_count": len(excluded or []),
    }
    (output_root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    write_jsonl_gz(output_root / "excluded_unsupported_sequences.jsonl.gz", excluded or [])
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-manifest", type=Path, required=True)
    parser.add_argument("--groups-manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--shard-count", type=int, default=8)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    rows = select_records(read_jsonl_gz(args.train_manifest), None)
    rows = attach_sequences(rows, read_jsonl_gz(args.groups_manifest))
    rows, excluded = filter_supported_sequences(rows)
    if args.limit is not None:
        rows = rows[: args.limit]
    manifest = build_inputs(rows, args.output_root, args.shard_count, excluded)
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
