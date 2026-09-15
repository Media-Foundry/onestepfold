#!/usr/bin/env python3
"""Aggregate quality and near-SI blocks into frozen split manifests."""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
from typing import Any


def _read_gz(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _write_gz(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed:
            for row in rows:
                compressed.write((json.dumps(row, sort_keys=True) + "\n").encode("utf-8"))


def aggregate(quality_root: Path, si_root: Path, output_root: Path) -> dict[str, Any]:
    quality_rows = _read_gz(quality_root / "quality_index.jsonl.gz")
    group_rows = _read_gz(quality_root / "exact_sequence_groups_quality_v1.jsonl.gz")
    si_rows: list[dict[str, Any]] = []
    for path in sorted(si_root.glob("block-*.jsonl")):
        with path.open(encoding="utf-8") as handle:
            si_rows.extend(json.loads(line) for line in handle if line.strip())
    si_rows.sort(key=lambda row: str(row["group_id"]))
    expected = {
        str(row["group_id"]): row for row in group_rows if row.get("split") == "test_candidate"
    }
    if len(si_rows) != len(expected) or {str(row["group_id"]) for row in si_rows} != set(expected):
        raise ValueError(
            f"near-SI coverage mismatch: blocks={len(si_rows)} test_candidates={len(expected)}"
        )
    si_by_group = {str(row["group_id"]): row for row in si_rows}
    for row in group_rows:
        group_id = str(row["group_id"])
        if group_id in si_by_group:
            row["low_homology_pass"] = bool(si_by_group[group_id]["low_homology_pass"])
            row["near_pair_count"] = int(si_by_group[group_id]["near_pair_count"])
            row["max_covered_alignment_identity"] = si_by_group[group_id][
                "max_covered_alignment_identity"
            ]
            row["closest_pair"] = si_by_group[group_id]["closest_pair"]
        elif row.get("split") == "test_candidate":
            raise ValueError(f"missing near-SI result for {group_id}")

    split_rows: dict[str, list[dict[str, Any]]] = {
        "train": [],
        "post_cutoff_same_sequence": [],
        "test_temporal": [],
        "test_low_homology": [],
        "hq_eval": [],
    }
    group_split = {str(row["group_id"]): row for row in group_rows}
    for row in quality_rows:
        if not row.get("train_valid"):
            continue
        group_id = str(row.get("group_id"))
        group = group_split.get(group_id, {})
        record = {
            "pdb_id": row["pdb_id"],
            "sample_id": row.get("sample_id"),
            "group_id": group_id,
            "sequence_sha256": row.get("sequence_sha256"),
            "sequence_length": row.get("sequence_length"),
            "resolution_high_angstrom": row.get("resolution_high_angstrom"),
            "initial_release_date": row.get("initial_release_date"),
            "shard": row.get("shard"),
            "npz": row.get("npz"),
            "metadata": row.get("metadata"),
            "apo_like": "monomer_apo_like" in row.get("views", []),
            "hq_eval_valid": bool(row.get("hq_eval_valid")),
        }
        if row.get("split") == "train":
            split_rows["train"].append(record)
        elif row.get("split") == "leakage_excluded":
            split_rows["post_cutoff_same_sequence"].append(record)
        elif row.get("split") == "test_candidate":
            split_rows["test_temporal"].append(record)
            if group.get("low_homology_pass"):
                split_rows["test_low_homology"].append(record)
        if row.get("hq_eval_valid"):
            split_rows["hq_eval"].append(record)
    for rows in split_rows.values():
        rows.sort(key=lambda row: (str(row.get("group_id")), str(row["pdb_id"])))
    for name, rows in split_rows.items():
        _write_gz(output_root / f"{name}.jsonl.gz", rows)
    _write_gz(output_root / "groups.jsonl.gz", sorted(group_rows, key=lambda r: str(r["group_id"])))
    summary = {
        "quality_record_count": len(quality_rows),
        "quality_group_count": len(group_rows),
        "near_si_result_count": len(si_rows),
        "split_record_counts": {name: len(rows) for name, rows in split_rows.items()},
        "split_group_counts": {
            name: len({str(row["group_id"]) for row in rows}) for name, rows in split_rows.items()
        },
        "low_homology_pass_group_count": sum(
            bool(row.get("low_homology_pass"))
            for row in group_rows
            if row.get("split") == "test_candidate"
        ),
        "near_homology_group_count": sum(
            int(row.get("near_pair_count", 0) > 0)
            for row in group_rows
            if row.get("split") == "test_candidate"
        ),
        "output": str(output_root),
    }
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "split_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quality-root", type=Path, required=True)
    parser.add_argument("--si-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    aggregate(args.quality_root, args.si_root, args.output_root)


if __name__ == "__main__":
    main()
