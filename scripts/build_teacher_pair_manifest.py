#!/usr/bin/env python3
"""Freeze an exact-group train/validation manifest for accepted teacher pairs."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from onestepfold.data.teacher_pairs import (
    TEACHER_PAIR_SCHEMA_VERSION,
    TeacherPairDataError,
    build_teacher_pair_records,
    write_teacher_pair_manifest,
)

RANGE_PATTERN = re.compile(r"^shards_(\d{4})_(\d{4})$")


def read_input_metadata(input_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(input_root.glob("shard-*/metadata.jsonl.gz")):
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    row = json.loads(line)
                    row["teacher_shard"] = path.parent.name
                    rows.append(row)
    if not rows:
        raise TeacherPairDataError(f"no teacher metadata found below {input_root}")
    return rows


def source_map(provenance: dict[str, Any], setting: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for label, payload in provenance["sources"][setting].items():
        match = RANGE_PATTERN.match(label)
        if not match:
            raise TeacherPairDataError(f"invalid provenance shard range {label!r}")
        lower, upper = map(int, match.groups())
        for shard_id in range(lower, upper + 1):
            shard = f"shard-{shard_id:04d}"
            if shard in mapping:
                raise TeacherPairDataError(f"overlapping provenance for {shard}")
            mapping[shard] = str(payload["system"])
    return mapping


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _length_band(length: int) -> str:
    if length <= 127:
        return "20-127"
    if length <= 255:
        return "128-255"
    if length <= 511:
        return "256-511"
    if length <= 768:
        return "512-768"
    return "769-1024"


def build_summary(
    records: list[Any],
    *,
    seed: int,
    manifest_path: Path,
    manifest_sha256: str,
    provenance_path: Path,
    pair_validation_path: Path,
    deep_qa_path: Path,
) -> dict[str, Any]:
    return {
        "schema_version": TEACHER_PAIR_SCHEMA_VERSION,
        "complete": True,
        "record_count": len(records),
        "unique_group_count": len({record.group_id for record in records}),
        "seed": seed,
        "split_counts": dict(sorted(Counter(record.split for record in records).items())),
        "split_length_bands": {
            split: dict(
                sorted(
                    Counter(
                        _length_band(record.sequence_length)
                        for record in records
                        if record.split == split
                    ).items()
                )
            )
            for split in ("train", "validation")
        },
        "source_counts": {
            "c2_s2": dict(sorted(Counter(record.c2_source for record in records).items())),
            "c4_s2": dict(sorted(Counter(record.c4_source for record in records).items())),
        },
        "manifest": str(manifest_path),
        "manifest_sha256": manifest_sha256,
        "acceptance_inputs": {
            "provenance": {"path": str(provenance_path), "sha256": _sha256(provenance_path)},
            "pair_validation": {
                "path": str(pair_validation_path),
                "sha256": _sha256(pair_validation_path),
            },
            "deep_qa": {"path": str(deep_qa_path), "sha256": _sha256(deep_qa_path)},
        },
        "contract": {
            "group_atomic": True,
            "selection": "stable SHA256 rank over exact sequence group IDs",
            "coordinate_loading": "lazy; strict c2/c4 atom-key alignment; no imputation",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--provenance-json", type=Path, required=True)
    parser.add_argument("--pair-validation-json", type=Path, required=True)
    parser.add_argument("--deep-qa-json", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path, required=True)
    parser.add_argument("--validation-count", type=int, default=1600)
    parser.add_argument("--seed", type=int, default=101)
    args = parser.parse_args()

    provenance = json.loads(args.provenance_json.read_text(encoding="utf-8"))
    pair_validation = json.loads(args.pair_validation_json.read_text(encoding="utf-8"))
    deep_qa = json.loads(args.deep_qa_json.read_text(encoding="utf-8"))
    if not pair_validation.get("complete") or not deep_qa.get("complete"):
        raise TeacherPairDataError("teacher-pair acceptance inputs are not complete")

    records = build_teacher_pair_records(
        read_input_metadata(args.input_root),
        validation_count=args.validation_count,
        seed=args.seed,
        c2_sources=source_map(provenance, "c2_s2"),
        c4_sources=source_map(provenance, "c4_s2"),
    )
    for record in records:
        for relative_path in (
            record.c2_cif,
            record.c4_cif,
            record.c2_confidence,
            record.c4_confidence,
        ):
            path = args.output_root / relative_path
            if not path.is_file() or path.stat().st_size == 0:
                raise TeacherPairDataError(f"missing accepted artifact {path}")

    manifest_sha256 = write_teacher_pair_manifest(args.manifest, records)
    summary = build_summary(
        records,
        seed=args.seed,
        manifest_path=args.manifest,
        manifest_sha256=manifest_sha256,
        provenance_path=args.provenance_json,
        pair_validation_path=args.pair_validation_json,
        deep_qa_path=args.deep_qa_json,
    )
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.summary_json.with_name(args.summary_json.name + ".part")
    temporary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.summary_json)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
