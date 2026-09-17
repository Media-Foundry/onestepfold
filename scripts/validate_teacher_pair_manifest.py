#!/usr/bin/env python3
"""Exhaustively validate the frozen manifest through the training-data loader."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

from onestepfold.data.teacher_pairs import (
    TeacherPairRecord,
    load_teacher_pair,
    load_teacher_pair_manifest,
)


def validate_record(payload: tuple[TeacherPairRecord, Path]) -> dict[str, Any]:
    record, output_root = payload
    try:
        example = load_teacher_pair(record, output_root)
        return {
            "group_id": record.group_id,
            "split": record.split,
            "c2_source": record.c2_source,
            "atom_count": len(example.c2.atom_keys),
            "c2_missing_backbone": int(example.c2.backbone_mask.size)
            - int(example.c2.backbone_mask.sum()),
            "c4_missing_backbone": int(example.c4.backbone_mask.size)
            - int(example.c4.backbone_mask.sum()),
            "error": None,
        }
    except Exception as exc:
        return {
            "group_id": record.group_id,
            "split": record.split,
            "c2_source": record.c2_source,
            "error": f"{type(exc).__name__}: {exc}",
        }


def validate_manifest(
    manifest: Path, output_root: Path, *, workers: int, limit: int | None = None
) -> dict[str, Any]:
    records = load_teacher_pair_manifest(manifest)
    if limit is not None:
        records = records[:limit]
    payloads = ((record, output_root) for record in records)
    if workers == 1:
        results = [validate_record(payload) for payload in payloads]
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            results = list(executor.map(validate_record, payloads, chunksize=16))
    failures = [result for result in results if result["error"] is not None]
    successes = [result for result in results if result["error"] is None]
    return {
        "complete": len(results) == len(records) and not failures,
        "manifest": str(manifest),
        "record_count": len(records),
        "validated_count": len(successes),
        "failure_count": len(failures),
        "failure_examples": failures[:20],
        "split_counts": dict(sorted(Counter(result["split"] for result in successes).items())),
        "c2_source_counts": dict(
            sorted(Counter(result["c2_source"] for result in successes).items())
        ),
        "total_aligned_atom_count": sum(result["atom_count"] for result in successes),
        "c2_missing_backbone_atom_count": sum(
            result["c2_missing_backbone"] for result in successes
        ),
        "c4_missing_backbone_atom_count": sum(
            result["c4_missing_backbone"] for result in successes
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be positive")
    result = validate_manifest(
        args.manifest, args.output_root, workers=args.workers, limit=args.limit
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output_json.with_name(args.output_json.name + ".part")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.output_json)
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["complete"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
