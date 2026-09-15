#!/usr/bin/env python3
"""Audit post-cutoff test candidates against train groups with Biopython."""

from __future__ import annotations

import argparse
import gzip
import json
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

from onestepfold.data.sequence_identity import calculate_pairwise_identity

_TRAIN: list[dict[str, Any]] = []
_IDENTITY_THRESHOLD = 0.30
_COVERAGE_THRESHOLD = 0.70
_MIN_ALIGNED_RESIDUES = 50
_ALIGNER = None


def _read(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _init_worker() -> None:
    global _ALIGNER
    from onestepfold.data.sequence_identity import _new_homology_aligner

    _ALIGNER = _new_homology_aligner()


def _audit_one(query: dict[str, Any]) -> dict[str, Any]:
    sequence = str(query.get("sequence", ""))
    max_identity = 0.0
    max_covered_identity = 0.0
    max_pair: dict[str, Any] | None = None
    near_count = 0
    for reference in _TRAIN:
        reference_sequence = str(reference.get("sequence", ""))
        if not sequence or not reference_sequence:
            continue
        pair = calculate_pairwise_identity(sequence, reference_sequence, aligner=_ALIGNER)
        if pair.aligned_residue_count < _MIN_ALIGNED_RESIDUES:
            continue
        if pair.residue_identity > max_identity:
            max_identity = pair.residue_identity
            max_pair = {
                "group_id": reference["group_id"],
                "residue_identity": pair.residue_identity,
                "global_alignment_identity": pair.identity,
                "coverage": pair.shorter_sequence_coverage,
                "full_length_identity": pair.full_length_identity,
            }
        if pair.shorter_sequence_coverage >= _COVERAGE_THRESHOLD:
            max_covered_identity = max(max_covered_identity, pair.residue_identity)
        if (
            pair.residue_identity >= _IDENTITY_THRESHOLD
            and pair.shorter_sequence_coverage >= _COVERAGE_THRESHOLD
        ):
            near_count += 1
    return {
        "group_id": query["group_id"],
        "sequence_length": query.get("sequence_length"),
        "train_group_count": len(_TRAIN),
        "max_alignment_identity": max_identity,
        "max_covered_alignment_identity": max_covered_identity,
        "closest_pair": max_pair,
        "near_pair_count": near_count,
        "low_homology_pass": max_covered_identity < _IDENTITY_THRESHOLD,
    }


def audit(
    groups_path: Path,
    output: Path,
    query_start: int = 0,
    query_end: int | None = None,
    identity_threshold: float = 0.30,
    coverage_threshold: float = 0.70,
    min_aligned_residues: int = 50,
    workers: int = 1,
) -> dict[str, Any]:
    groups = _read(groups_path)
    train = [row for row in groups if row.get("train_seen")]
    queries = [row for row in groups if row.get("split") == "test_candidate"]
    queries.sort(key=lambda row: str(row["group_id"]))
    query_end = len(queries) if query_end is None else min(query_end, len(queries))
    if query_start < 0 or query_start > query_end:
        raise ValueError("invalid query range")
    results: list[dict[str, Any]] = []
    global _TRAIN, _IDENTITY_THRESHOLD, _COVERAGE_THRESHOLD, _MIN_ALIGNED_RESIDUES
    _TRAIN = train
    _IDENTITY_THRESHOLD = identity_threshold
    _COVERAGE_THRESHOLD = coverage_threshold
    _MIN_ALIGNED_RESIDUES = min_aligned_residues
    selected_queries = queries[query_start:query_end]
    if workers <= 1:
        _init_worker()
        results = [_audit_one(query) for query in selected_queries]
    else:
        context = mp.get_context("fork")
        with ProcessPoolExecutor(
            max_workers=workers,
            mp_context=context,
            initializer=_init_worker,
        ) as executor:
            results = list(executor.map(_audit_one, selected_queries, chunksize=1))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for row in results:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    summary = {
        "groups": str(groups_path),
        "query_start": query_start,
        "query_end": query_end,
        "query_count": len(results),
        "all_test_candidate_count": len(queries),
        "train_group_count": len(train),
        "identity_threshold": identity_threshold,
        "coverage_threshold": coverage_threshold,
        "min_aligned_residues": min_aligned_residues,
        "low_homology_pass_count": sum(row["low_homology_pass"] for row in results),
        "near_pair_query_count": sum(row["near_pair_count"] > 0 for row in results),
        "output": str(output),
    }
    output.with_suffix(output.suffix + ".summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--groups", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--query-start", type=int, default=0)
    parser.add_argument("--query-end", type=int, default=None)
    parser.add_argument("--identity-threshold", type=float, default=0.30)
    parser.add_argument("--coverage-threshold", type=float, default=0.70)
    parser.add_argument("--min-aligned-residues", type=int, default=50)
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()
    audit(
        args.groups,
        args.output,
        args.query_start,
        args.query_end,
        args.identity_threshold,
        args.coverage_threshold,
        args.min_aligned_residues,
        args.workers,
    )


if __name__ == "__main__":
    main()
