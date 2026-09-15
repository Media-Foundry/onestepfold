#!/usr/bin/env python3
"""Apply GT quality v1 and rebuild exact-sequence groups/time views."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from onestepfold.data.quality_policy import GTQualityPolicy, classify_quality


def _read_jsonl_gz(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _write_jsonl_gz(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed:
            for row in rows:
                compressed.write((json.dumps(row, sort_keys=True) + "\n").encode("utf-8"))


def _date(row: dict[str, Any]) -> str:
    return str(row.get("initial_release_date") or "")


def build_quality_views(
    stageb_root: Path,
    si_manifest: Path,
    policy_path: Path,
    output_root: Path,
    cutoff: str | None = None,
) -> dict[str, Any]:
    policy = GTQualityPolicy.from_toml(policy_path)
    cutoff = cutoff or policy.date_cutoff
    group_by_pdb: dict[str, dict[str, Any]] = {}
    with gzip.open(si_manifest, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                group_by_pdb[str(row["pdb_id"])] = row

    index_rows: list[dict[str, Any]] = []
    for index_path in sorted(stageb_root.glob("index-worker-*.jsonl.gz")):
        index_rows.extend(_read_jsonl_gz(index_path))
    index_rows.sort(key=lambda row: str(row["pdb_id"]))
    if len({str(row["pdb_id"]) for row in index_rows}) != len(index_rows):
        raise ValueError("duplicate PDB IDs in Stage B index")

    counts: Counter[str] = Counter()
    reason_counts: Counter[str] = Counter()
    enriched: list[dict[str, Any]] = []
    valid_by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in index_rows:
        pdb_id = str(row["pdb_id"])
        decision = classify_quality(row, policy)
        group = group_by_pdb.get(pdb_id, {})
        release = _date(row)
        enriched_row = {
            "pdb_id": pdb_id,
            "sample_id": row.get("sample_id"),
            "shard": row.get("shard"),
            "npz": row.get("npz"),
            "metadata": row.get("metadata"),
            "sequence_sha256": group.get("sequence_sha256"),
            "group_id": group.get("group_id"),
            "sequence": row.get("sequence", ""),
            "sequence_length": int(row.get("sequence_length", 0) or 0),
            "resolution_high_angstrom": row.get("resolution_high_angstrom"),
            "experimental_methods": row.get("experimental_methods", []),
            "initial_release_date": release or None,
            "initial_deposition_date": row.get("initial_deposition_date"),
            "latest_revision_date": row.get("latest_revision_date"),
            "assembly_id": row.get("assembly_id"),
            "assembly_definition_source": row.get("assembly_definition_source"),
            "views": row.get("views", []),
            "qa": row.get("qa", {}),
            **decision,
        }
        if not release:
            enriched_row["split_date_status"] = "missing_release_date"
        elif release <= cutoff:
            enriched_row["split_date_status"] = "pre_or_on_cutoff"
        else:
            enriched_row["split_date_status"] = "post_cutoff"
        enriched.append(enriched_row)
        if decision["train_valid"]:
            counts["train_valid"] += 1
            if decision["hq_eval_valid"]:
                counts["hq_eval_valid"] += 1
            for reason in decision["hq_eval_reasons"]:
                reason_counts[f"hq:{reason}"] += 1
            for reason in decision["train_reject_reasons"]:
                reason_counts[f"train:{reason}"] += 1
            if group.get("group_id"):
                valid_by_group[str(group["group_id"])].append(enriched_row)
        else:
            counts["reject"] += 1
            for reason in decision["train_reject_reasons"]:
                reason_counts[reason] += 1

    group_rows: list[dict[str, Any]] = []
    for group_id, members in sorted(valid_by_group.items()):
        members.sort(key=lambda row: str(row["pdb_id"]))
        dated = [row for row in members if row.get("initial_release_date")]
        pre = [row for row in dated if str(row["initial_release_date"]) <= cutoff]
        post = [row for row in dated if str(row["initial_release_date"]) > cutoff]
        train_seen = bool(pre)
        if train_seen:
            split = "train_seen"
        elif post and len(post) == len(dated) and len(dated) == len(members):
            split = "test_candidate"
        else:
            split = "date_incomplete"
        for row in members:
            if train_seen:
                row["split"] = "train" if row in pre else "leakage_excluded"
            else:
                row["split"] = "test_candidate" if split == "test_candidate" else "split_excluded"
        representative = members[0]
        group_rows.append(
            {
                "group_id": group_id,
                "sequence_sha256": representative.get("sequence_sha256")
                or hashlib.sha256(
                    str(representative.get("sequence", "")).encode("ascii")
                ).hexdigest(),
                "sequence": representative.get("sequence", ""),
                "sequence_length": representative.get("sequence_length", 0),
                "valid_member_count": len(members),
                "valid_member_pdb_ids": [row["pdb_id"] for row in members],
                "pre_cutoff_valid_pdb_ids": [row["pdb_id"] for row in pre],
                "post_cutoff_valid_pdb_ids": [row["pdb_id"] for row in post],
                "earliest_valid_release_date": min(
                    (str(row["initial_release_date"]) for row in dated), default=None
                ),
                "train_seen": train_seen,
                "split": split,
            }
        )
    for row in enriched:
        row.setdefault("split", "quality_reject")

    _write_jsonl_gz(output_root / "quality_index.jsonl.gz", enriched)
    _write_jsonl_gz(output_root / "exact_sequence_groups_quality_v1.jsonl.gz", group_rows)
    summary = {
        "policy": str(policy_path),
        "policy_version": policy.version,
        "cutoff": cutoff,
        "input_index_records": len(index_rows),
        "counts": dict(sorted(counts.items())),
        "reason_counts": dict(sorted(reason_counts.items())),
        "quality_group_count": len(group_rows),
        "train_seen_group_count": sum(row["train_seen"] for row in group_rows),
        "test_candidate_group_count": sum(row["split"] == "test_candidate" for row in group_rows),
        "date_incomplete_group_count": sum(row["split"] == "date_incomplete" for row in group_rows),
        "output": str(output_root),
    }
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "quality_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stageb-root", type=Path, required=True)
    parser.add_argument("--si-manifest", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--cutoff", default=None)
    args = parser.parse_args()
    build_quality_views(
        args.stageb_root, args.si_manifest, args.policy, args.output_root, args.cutoff
    )


if __name__ == "__main__":
    main()
