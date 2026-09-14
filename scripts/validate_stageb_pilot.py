#!/usr/bin/env python3
"""Validate and summarize Stage B NPZ/JSON tar shards."""

from __future__ import annotations

import argparse
import collections
import gzip
import io
import json
import tarfile
from pathlib import Path
from typing import Any

import numpy as np


def _quantiles(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"p05": None, "p25": None, "p50": None, "p75": None, "p95": None}
    ordered = sorted(values)
    return {
        f"p{int(fraction * 100):02d}": ordered[
            min(len(ordered) - 1, int(round(fraction * (len(ordered) - 1))))
        ]
        for fraction in (0.05, 0.25, 0.5, 0.75, 0.95)
    }


def validate(root: Path) -> dict[str, Any]:
    index_paths = sorted(root.glob("index-worker-*.jsonl.gz"))
    summary_paths = sorted(root.glob("summary-worker-*.json"))
    rows: list[dict[str, Any]] = []
    for path in index_paths:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            rows.extend(json.loads(line) for line in handle if line.strip())
    errors = []
    for path in sorted((root / "errors").glob("worker-*.jsonl")):
        errors.extend(json.loads(line) for line in path.read_text().splitlines() if line.strip())
    tar_member_count = 0
    missing_npz = 0
    missing_metadata = 0
    npz_shape_errors = 0
    metadata_length_errors = 0
    nonfinite_valid_atom_count = 0
    residue_mask_errors = 0
    for path in sorted((root / "shards").glob("*.tar")):
        with tarfile.open(path, "r") as archive:
            member_objects = {member.name: member for member in archive if member.isfile()}
            members = set(member_objects)
        tar_member_count += len(members)
        for name in members:
            if name.endswith(".npz") and name[:-4] + ".json" not in members:
                missing_metadata += 1
            if name.endswith(".json") and name[:-5] + ".npz" not in members:
                missing_npz += 1
        with tarfile.open(path, "r") as archive:
            for name, member in member_objects.items():
                if not name.endswith(".npz"):
                    continue
                payload = archive.extractfile(member)
                metadata_member = archive.extractfile(name[:-4] + ".json")
                if payload is None or metadata_member is None:
                    continue
                with np.load(io.BytesIO(payload.read())) as arrays:
                    required = {
                        "aatype",
                        "residue_index",
                        "atom37_positions",
                        "atom37_mask",
                        "residue_mask",
                        "chain_index",
                    }
                    if set(arrays.files) != required:
                        npz_shape_errors += 1
                        continue
                    length = int(arrays["aatype"].shape[0])
                    if (
                        arrays["residue_index"].shape != (length,)
                        or arrays["atom37_positions"].shape != (length, 37, 3)
                        or arrays["atom37_mask"].shape != (length, 37)
                        or arrays["residue_mask"].shape != (length,)
                        or arrays["chain_index"].shape != (length,)
                    ):
                        npz_shape_errors += 1
                    if not np.isfinite(arrays["atom37_positions"][arrays["atom37_mask"]]).all():
                        nonfinite_valid_atom_count += 1
                    if not np.array_equal(
                        arrays["residue_mask"], arrays["atom37_mask"].any(axis=1)
                    ):
                        residue_mask_errors += 1
                    metadata = json.loads(metadata_member.read())
                    if metadata["chains"][0]["sequence_length"] != length:
                        metadata_length_errors += 1

    qa_values: dict[str, list[float]] = collections.defaultdict(list)
    component_counts: collections.Counter[str] = collections.Counter()
    stratum_counts: collections.Counter[str] = collections.Counter()
    modified = 0
    for row in rows:
        component_counts[str(row.get("pilot_component"))] += 1
        stratum_counts[str(row.get("pilot_stratum"))] += 1
        qa = row.get("qa", {})
        modified += int(qa.get("modified_residue_count", 0) > 0)
        for key in (
            "observed_residue_fraction",
            "frame_coverage",
            "backbone4_coverage",
            "heavy_atom_coverage",
            "terminal_missing_fraction",
            "internal_missing_fraction",
        ):
            if qa.get(key) is not None:
                qa_values[key].append(float(qa[key]))

    worker_counts = []
    for path in summary_paths:
        worker_counts.append(json.loads(path.read_text()).get("counts", {}))
    aggregate_counts: collections.Counter[str] = collections.Counter()
    for counts in worker_counts:
        aggregate_counts.update(counts)
    result = {
        "worker_count": len(summary_paths),
        "index_worker_count": len(index_paths),
        "tar_shard_count": len(list((root / "shards").glob("*.tar"))),
        "input_count": sum(
            int(json.loads(path.read_text()).get("input_count", 0)) for path in summary_paths
        ),
        "index_record_count": len(rows),
        "success_count": aggregate_counts.get("success", 0),
        "error_count": sum(aggregate_counts[key] for key in aggregate_counts if key != "success"),
        "error_file_record_count": len(errors),
        "tar_member_count": tar_member_count,
        "expected_tar_member_count": len(rows) * 2,
        "missing_npz_count": missing_npz,
        "missing_metadata_count": missing_metadata,
        "npz_shape_error_count": npz_shape_errors,
        "metadata_length_error_count": metadata_length_errors,
        "nonfinite_valid_atom_count": nonfinite_valid_atom_count,
        "residue_mask_error_count": residue_mask_errors,
        "component_counts": dict(sorted(component_counts.items())),
        "stratum_count": len(stratum_counts),
        "modified_residue_structure_count": modified,
        "qa_quantiles": {key: _quantiles(values) for key, values in sorted(qa_values.items())},
        "geometry_outlier_totals": {
            key: sum(int(row.get("qa", {}).get(key, 0)) for row in rows)
            for key in (
                "bond_length_outlier_count",
                "peptide_bond_outlier_count",
                "chirality_violation_count",
                "steric_clash_count",
                "chain_break_count",
                "finite_coordinate_violation_count",
            )
        },
        "errors": errors,
        "strata_population": dict(sorted(stratum_counts.items())),
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {key: value for key, value in result.items() if key != "errors"},
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
