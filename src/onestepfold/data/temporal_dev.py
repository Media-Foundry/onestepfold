#!/usr/bin/env python3
"""Freeze a stratified temporal-dev view and its untouched test complement."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

LENGTH_BINS = (
    (20, 127, "20-127"),
    (128, 255, "128-255"),
    (256, 511, "256-511"),
    (512, 768, "512-768"),
    (769, 1024, "769-1024"),
)
RESOLUTION_BINS = (
    (0.0, 2.0, "<=2.0"),
    (2.0, 2.5, "2.0-2.5"),
    (2.5, 3.0, "2.5-3.0"),
)


def _read_jsonl_gz(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _write_jsonl_gz(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed:
            for row in rows:
                compressed.write((json.dumps(row, sort_keys=True) + "\n").encode("utf-8"))


def _number(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _length_bin(length: int) -> str:
    for lower, upper, label in LENGTH_BINS:
        if lower <= length <= upper:
            return label
    return "out_of_range"


def _resolution_bin(value: Any) -> str:
    resolution = _number(value, default=math.inf)
    for lower, upper, label in RESOLUTION_BINS:
        if lower <= resolution <= upper:
            return label
    return "out_of_range"


def _method_bin(methods: list[str] | tuple[str, ...]) -> str:
    normalized = {str(method).upper() for method in methods}
    if "ELECTRON MICROSCOPY" in normalized:
        return "electron_microscopy"
    if "NEUTRON DIFFRACTION" in normalized:
        return "neutron"
    if "X-RAY DIFFRACTION" in normalized:
        return "xray"
    return "other"


def _is_apo_like(row: dict[str, Any]) -> bool:
    return bool(row.get("apo_like", False)) or "monomer_apo_like" in row.get("views", [])


def _best_record_key(row: dict[str, Any]) -> tuple[float, float, float, str]:
    qa = row.get("qa", {})
    resolution = _number(row.get("resolution_high_angstrom"), default=math.inf)
    return (
        -_number(qa.get("frame_coverage")),
        -_number(qa.get("heavy_atom_coverage")),
        resolution,
        str(row.get("pdb_id", "")),
    )


def _stable_group_key(group_id: str, seed: int) -> str:
    return hashlib.sha256(f"{seed}:{group_id}".encode("ascii")).hexdigest()


def _stratify(row: dict[str, Any]) -> tuple[str, str, bool, str]:
    return (
        _length_bin(int(row.get("sequence_length", 0) or 0)),
        _resolution_bin(row.get("resolution_high_angstrom")),
        _is_apo_like(row),
        _method_bin(row.get("experimental_methods", [])),
    )


def _proportional_allocation(
    buckets: dict[tuple[str, str, bool, str], list[dict[str, Any]]], target: int
) -> dict[tuple[str, str, bool, str], int]:
    total = sum(len(rows) for rows in buckets.values())
    if target < 0 or target > total:
        raise ValueError(f"dev size {target} is outside candidate count {total}")
    exact = {key: target * len(rows) / total for key, rows in buckets.items()}
    allocation = {key: min(len(buckets[key]), math.floor(value)) for key, value in exact.items()}
    remaining = target - sum(allocation.values())
    order = sorted(
        buckets,
        key=lambda key: (-(exact[key] - math.floor(exact[key])), key),
    )
    for key in order:
        if remaining == 0:
            break
        if allocation[key] < len(buckets[key]):
            allocation[key] += 1
            remaining -= 1
    if remaining:
        raise AssertionError(f"could not allocate {remaining} dev samples")
    return allocation


def select_temporal_dev(
    groups_path: Path,
    quality_index_path: Path,
    output_root: Path,
    dev_size: int = 1024,
    variance_size: int = 128,
    seed: int = 101,
) -> dict[str, Any]:
    groups = _read_jsonl_gz(groups_path)
    test_groups = {
        str(row["group_id"]): row
        for row in groups
        if row.get("split") == "test_candidate"
    }
    if not test_groups:
        raise ValueError("no temporal test-candidate groups found")

    quality_rows = _read_jsonl_gz(quality_index_path)
    reserved_low_homology = {
        group_id for group_id, row in test_groups.items() if row.get("low_homology_pass")
    }
    hq_by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in quality_rows:
        group_id = str(row.get("group_id", ""))
        if group_id in test_groups and row.get("hq_eval_valid"):
            hq_by_group[group_id].append(row)

    targets: list[dict[str, Any]] = []
    for group_id, rows in sorted(hq_by_group.items()):
        target = min(rows, key=_best_record_key)
        target = dict(target)
        target["stage0_group_id"] = group_id
        target["stage0_target_rank"] = 1
        target["stage0_selection_key"] = list(_best_record_key(target))
        target["stage0_stratum"] = {
            "length": _length_bin(int(target.get("sequence_length", 0) or 0)),
            "resolution": _resolution_bin(target.get("resolution_high_angstrom")),
            "apo_like": _is_apo_like(target),
            "method": _method_bin(target.get("experimental_methods", [])),
        }
        targets.append(target)

    if dev_size > len(targets):
        raise ValueError(f"dev size {dev_size} exceeds HQ group count {len(targets)}")

    eligible_targets = [
        row for row in targets if str(row["stage0_group_id"]) not in reserved_low_homology
    ]
    buckets: dict[tuple[str, str, bool, str], list[dict[str, Any]]] = defaultdict(list)
    for row in eligible_targets:
        buckets[_stratify(row)].append(row)
    for rows in buckets.values():
        rows.sort(
            key=lambda row: (
                _stable_group_key(str(row["stage0_group_id"]), seed),
                str(row["stage0_group_id"]),
            )
        )
    allocation = _proportional_allocation(buckets, dev_size)
    dev: list[dict[str, Any]] = []
    for key in sorted(buckets):
        dev.extend(buckets[key][: allocation[key]])
    dev_ids = {str(row["stage0_group_id"]) for row in dev}
    frozen = [row for row in targets if str(row["stage0_group_id"]) not in dev_ids]
    dev.sort(key=lambda row: str(row["stage0_group_id"]))
    frozen.sort(key=lambda row: str(row["stage0_group_id"]))

    variance_buckets: dict[tuple[str, str, bool, str], list[dict[str, Any]]] = defaultdict(list)
    for row in dev:
        variance_buckets[_stratify(row)].append(row)
    for rows in variance_buckets.values():
        rows.sort(
            key=lambda row: (
                _stable_group_key(str(row["stage0_group_id"]), seed + 1),
                str(row["stage0_group_id"]),
            )
        )
    variance_allocation = _proportional_allocation(variance_buckets, variance_size)
    variance: list[dict[str, Any]] = []
    for key in sorted(variance_buckets):
        variance.extend(variance_buckets[key][: variance_allocation[key]])
    variance.sort(key=lambda row: str(row["stage0_group_id"]))

    def annotate(rows: list[dict[str, Any]], view: str) -> list[dict[str, Any]]:
        result = []
        for row in rows:
            item = dict(row)
            item["stage0_view"] = view
            item["stage0_group_id"] = str(item["stage0_group_id"])
            result.append(item)
        return result

    dev = annotate(dev, "temporal_dev_v1")
    frozen = annotate(frozen, "frozen_temporal_test_v1")
    variance = annotate(variance, "temporal_variance_v1")
    dev_group_rows = []
    frozen_group_rows = []
    variance_group_rows = []
    for row in dev:
        group = dict(test_groups[row["stage0_group_id"]])
        group["stage0_view"] = "temporal_dev_v1"
        group["selected_pdb_id"] = row["pdb_id"]
        group["selected_sample_id"] = row.get("sample_id")
        group["stage0_stratum"] = row["stage0_stratum"]
        dev_group_rows.append(group)
    for row in frozen:
        group = dict(test_groups[row["stage0_group_id"]])
        group["stage0_view"] = "frozen_temporal_test_v1"
        group["selected_pdb_id"] = row["pdb_id"]
        group["selected_sample_id"] = row.get("sample_id")
        group["stage0_stratum"] = row["stage0_stratum"]
        frozen_group_rows.append(group)
    for row in variance:
        group = dict(test_groups[row["stage0_group_id"]])
        group["stage0_view"] = "temporal_variance_v1"
        group["selected_pdb_id"] = row["pdb_id"]
        group["selected_sample_id"] = row.get("sample_id")
        group["stage0_stratum"] = row["stage0_stratum"]
        variance_group_rows.append(group)
    low_homology_group_rows = []
    for group_id in sorted(reserved_low_homology):
        group = dict(test_groups[group_id])
        group["stage0_view"] = "frozen_temporal_low_homology_v1"
        group["selected_pdb_id"] = None
        group["selected_sample_id"] = None
        low_homology_group_rows.append(group)

    _write_jsonl_gz(output_root / "temporal_dev_v1.jsonl.gz", dev)
    _write_jsonl_gz(output_root / "temporal_variance_v1.jsonl.gz", variance)
    _write_jsonl_gz(output_root / "frozen_temporal_test_v1.jsonl.gz", frozen)
    _write_jsonl_gz(output_root / "temporal_dev_groups_v1.jsonl.gz", dev_group_rows)
    _write_jsonl_gz(output_root / "temporal_variance_groups_v1.jsonl.gz", variance_group_rows)
    _write_jsonl_gz(output_root / "frozen_temporal_test_groups_v1.jsonl.gz", frozen_group_rows)
    _write_jsonl_gz(
        output_root / "frozen_temporal_low_homology_groups_v1.jsonl.gz",
        low_homology_group_rows,
    )
    summary = {
        "groups_input": len(groups),
        "temporal_candidate_group_count": len(test_groups),
        "hq_candidate_group_count": len(targets),
        "hq_dev_candidate_group_count": len(eligible_targets),
        "reserved_low_homology_group_count": len(reserved_low_homology),
        "reserved_low_homology_hq_target_count": len(
            reserved_low_homology.intersection(hq_by_group)
        ),
        "non_hq_temporal_group_count": len(test_groups) - len(targets),
        "dev_group_count": len(dev),
        "frozen_test_group_count": len(frozen),
        "dev_size_requested": dev_size,
        "variance_size_requested": variance_size,
        "variance_group_count": len(variance),
        "seed": seed,
        "target_policy": (
            "frame_coverage desc, heavy_atom_coverage desc, "
            "resolution asc, pdb_id asc"
        ),
        "stratum_counts_candidates": {
            "|".join(map(str, key)): len(rows) for key, rows in sorted(buckets.items())
        },
        "stratum_counts_dev": dict(
            sorted(Counter("|".join(map(str, _stratify(row))) for row in dev).items())
        ),
        "stratum_counts_variance": dict(
            sorted(Counter("|".join(map(str, _stratify(row))) for row in variance).items())
        ),
        "output": str(output_root),
    }
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "temporal_dev_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_root / "temporal_dev_protocol.json").write_text(
        json.dumps(
            {
                "version": "temporal_dev_v1",
                "groups": str(groups_path),
                "quality_index": str(quality_index_path),
                "dev_size": dev_size,
                "variance_size": variance_size,
                "seed": seed,
                "length_bins": [label for _, _, label in LENGTH_BINS],
                "resolution_bins": [label for _, _, label in RESOLUTION_BINS],
                "frozen_test_is_untouched_complement": True,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--groups", type=Path, required=True)
    parser.add_argument("--quality-index", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--dev-size", type=int, default=1024)
    parser.add_argument("--variance-size", type=int, default=128)
    parser.add_argument("--seed", type=int, default=101)
    args = parser.parse_args()
    select_temporal_dev(
        args.groups,
        args.quality_index,
        args.output_root,
        args.dev_size,
        args.variance_size,
        args.seed,
    )


if __name__ == "__main__":
    main()
