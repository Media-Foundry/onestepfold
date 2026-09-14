#!/usr/bin/env python3
"""Build a deterministic strict-100%-identity manifest for monomer candidates."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.metadata
import io
import json
from collections import defaultdict
from pathlib import Path

from onestepfold.data.sequence_identity import (
    calculate_pairwise_identity,
    exact_sequence_digest,
)


def _open_gzip_text(path: Path) -> io.TextIOWrapper:
    compressed = gzip.GzipFile(filename=str(path), mode="wb", mtime=0)
    return io.TextIOWrapper(compressed, encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def build_manifest(input_path: Path, output_path: Path, summary_path: Path) -> None:
    records: dict[str, str] = {}
    with gzip.open(input_path, "rt", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            record_id = str(row["pdb_id"])
            sequence = str(row["sequence"])
            if record_id in records:
                raise ValueError(f"duplicate pdb_id {record_id} at line {line_number}")
            if not sequence:
                raise ValueError(f"empty sequence for {record_id} at line {line_number}")
            records[record_id] = sequence

    buckets: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for record_id, sequence in records.items():
        buckets[exact_sequence_digest(sequence)].append((record_id, sequence))

    groups: list[dict[str, object]] = []
    mapping: list[dict[str, object]] = []
    verified_pairs = 0
    for digest, bucket in sorted(buckets.items()):
        ordered = sorted(bucket, key=lambda item: item[0])
        representative_id, representative_sequence = ordered[0]
        for _, sequence in ordered[1:]:
            result = calculate_pairwise_identity(representative_sequence, sequence)
            if result.identity != 1.0 or result.gap_columns:
                raise ValueError(f"digest bucket {digest} failed pairwise verification")
            verified_pairs += 1
        member_ids = [record_id for record_id, _ in ordered]
        groups.append(
            {
                "group_id": digest,
                "representative_pdb_id": representative_id,
                "sequence_length": len(representative_sequence),
                "member_count": len(member_ids),
                "member_pdb_ids": member_ids,
                "pairwise_identity": 1.0,
            }
        )
        for record_id in member_ids:
            mapping.append(
                {
                    "pdb_id": record_id,
                    "group_id": digest,
                    "sequence_sha256": digest,
                    "sequence_length": len(records[record_id]),
                    "member_count": len(member_ids),
                    "pairwise_identity_verified": True,
                }
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with _open_gzip_text(output_path) as handle:
        for row in mapping:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    summary = {
        "input": str(input_path),
        "input_sha256": _sha256(input_path),
        "output": str(output_path),
        "record_count": len(records),
        "identity_group_count": len(groups),
        "duplicate_record_count": len(records) - len(groups),
        "verified_pair_count": verified_pairs,
        "biopython_version": importlib.metadata.version("biopython"),
        "identity_definition": "global alignment matches / all alignment columns",
        "groups": groups,
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    compact_summary = {key: value for key, value in summary.items() if key != "groups"}
    print(json.dumps(compact_summary, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    build_manifest(args.input, args.output, args.summary)


if __name__ == "__main__":
    main()
