#!/usr/bin/env python3
"""Measure structural disagreement among exact-sequence pilot records."""

from __future__ import annotations

import argparse
import gzip
import io
import json
import tarfile
from collections import defaultdict
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


def _kabsch_rmsd(first: np.ndarray, second: np.ndarray) -> float:
    first_centered = first - first.mean(axis=0)
    second_centered = second - second.mean(axis=0)
    covariance = first_centered.T @ second_centered
    left, _, right_transpose = np.linalg.svd(covariance)
    rotation = left @ right_transpose
    if np.linalg.det(rotation) < 0:
        left[:, -1] *= -1
        rotation = left @ right_transpose
    aligned = first_centered @ rotation
    return float(np.sqrt(np.mean(np.sum((aligned - second_centered) ** 2, axis=1))))


def _tm_score(first: np.ndarray, second: np.ndarray) -> float:
    first_centered = first - first.mean(axis=0)
    second_centered = second - second.mean(axis=0)
    covariance = first_centered.T @ second_centered
    left, _, right_transpose = np.linalg.svd(covariance)
    rotation = left @ right_transpose
    if np.linalg.det(rotation) < 0:
        left[:, -1] *= -1
        rotation = left @ right_transpose
    distances = np.linalg.norm(first_centered @ rotation - second_centered, axis=1)
    length = len(distances)
    d0 = max(0.5, 1.24 * (length - 15) ** (1 / 3) - 1.8) if length > 15 else 0.5
    return float(np.mean(1.0 / (1.0 + (distances / d0) ** 2)))


def audit(index_root: Path, si_manifest: Path, output: Path) -> dict[str, Any]:
    group_by_pdb: dict[str, str] = {}
    with gzip.open(si_manifest, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            group_by_pdb[str(row["pdb_id"])] = str(row["group_id"])

    structures: dict[str, list[tuple[str, np.ndarray, np.ndarray]]] = defaultdict(list)
    archive_cache: dict[str, tarfile.TarFile] = {}
    try:
        for index_path in sorted(index_root.glob("index-worker-*.jsonl.gz")):
            with gzip.open(index_path, "rt", encoding="utf-8") as handle:
                for line in handle:
                    row = json.loads(line)
                    group_id = group_by_pdb.get(str(row["pdb_id"]))
                    if group_id is None:
                        continue
                    if int(row.get("member_count", 1)) < 2:
                        continue
                    shard = str(row["shard"])
                    archive = archive_cache.get(shard)
                    if archive is None:
                        archive = tarfile.open(shard, "r")
                        archive_cache[shard] = archive
                    payload = archive.extractfile(str(row["npz"]))
                    if payload is None:
                        continue
                    with np.load(io.BytesIO(payload.read())) as arrays:
                        coordinates = np.asarray(
                            arrays["atom37_positions"][:, 1, :], dtype=np.float32
                        )
                        mask = np.asarray(arrays["atom37_mask"][:, 1], dtype=bool)
                    structures[group_id].append((str(row["pdb_id"]), coordinates, mask))
    finally:
        for archive in archive_cache.values():
            archive.close()

    rmsds: list[float] = []
    tm_scores: list[float] = []
    pair_count = 0
    disagreement_count = 0
    group_results: list[dict[str, Any]] = []
    for group_id, members in sorted(structures.items()):
        members.sort(key=lambda item: item[0])
        if len(members) < 2:
            continue
        group_rmsds: list[float] = []
        group_tm: list[float] = []
        representative = members[0]
        for _, coordinates, mask in members[1:]:
            common = representative[2] & mask
            if int(common.sum()) < 3:
                continue
            first = representative[1][common]
            second = coordinates[common]
            rmsd = _kabsch_rmsd(first, second)
            tm = _tm_score(first, second)
            group_rmsds.append(rmsd)
            group_tm.append(tm)
            rmsds.append(rmsd)
            tm_scores.append(tm)
            pair_count += 1
            disagreement_count += int(rmsd > 2.0 or tm < 0.9)
        group_results.append(
            {
                "group_id": group_id,
                "member_count": len(members),
                "compared_to_representative": len(group_rmsds),
                "rmsd_quantiles_angstrom": _quantiles(group_rmsds),
                "tm_score_quantiles": _quantiles(group_tm),
                "disagreement_pair_count": sum(
                    int(rmsd > 2.0 or tm < 0.9)
                    for rmsd, tm in zip(group_rmsds, group_tm, strict=True)
                ),
            }
        )
    result = {
        "pilot_record_count_with_replicate_group": sum(len(value) for value in structures.values()),
        "exact_groups_with_multiple_pilot_records": len(group_results),
        "compared_pair_count": pair_count,
        "disagreement_pair_count": disagreement_count,
        "disagreement_fraction": disagreement_count / pair_count if pair_count else None,
        "rmsd_quantiles_angstrom": _quantiles(rmsds),
        "tm_score_quantiles": _quantiles(tm_scores),
        "disagreement_definition": "Kabsch CA RMSD > 2.0 A or TM-score < 0.9",
        "groups": group_results,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {key: value for key, value in result.items() if key != "groups"},
            indent=2,
            sort_keys=True,
        )
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index-root", type=Path, required=True)
    parser.add_argument("--si-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit(args.index_root, args.si_manifest, args.output)


if __name__ == "__main__":
    main()
