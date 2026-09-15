#!/usr/bin/env python3
"""Validate an ESMC sharded-safetensors cache without loading full tensors."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def _read_jsonl_gz(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def validate(cache_root: Path, groups_path: Path) -> dict[str, Any]:
    from safetensors import safe_open

    spec = json.loads((cache_root / "feature_spec.json").read_text(encoding="utf-8"))
    groups = _read_jsonl_gz(groups_path)
    rows = _read_jsonl_gz(cache_root / "manifest.jsonl.gz")
    expected = {str(row["group_id"]): row for row in groups}
    actual = {str(row["group_id"]): row for row in rows}
    if set(expected) != set(actual):
        raise ValueError(
            f"group coverage mismatch: expected={len(expected)} actual={len(actual)}"
        )
    if len(actual) != len(rows):
        raise ValueError("duplicate group IDs in cache manifest")

    shards: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for group_id, row in actual.items():
        if int(row["sequence_length"]) != int(expected[group_id]["sequence_length"]):
            raise ValueError(f"length mismatch for {group_id}")
        if row["feature_variant"] != spec["feature_variant"]:
            raise ValueError(f"feature variant mismatch for {group_id}")
        if row["model_id"] != spec["model_id"] or row["hf_revision"] != spec["hf_revision"]:
            raise ValueError(f"model revision mismatch for {group_id}")
        shards[str(row["shard"])].append(row)

    shard_summaries: list[dict[str, Any]] = []
    for name, shard_rows in sorted(shards.items()):
        path = cache_root / name
        if not path.is_file():
            raise FileNotFoundError(path)
        checksum = _sha256_file(path)
        expected_checksums = {str(row["shard_sha256"]) for row in shard_rows}
        if expected_checksums != {checksum}:
            raise ValueError(f"checksum mismatch for {name}")
        with safe_open(str(path), framework="pt", device="cpu") as handle:
            keys = sorted(handle.keys())
            expected_keys = sorted(str(key) for key in shard_rows[0]["feature_names"])
            if keys != expected_keys:
                raise ValueError(f"feature keys mismatch for {name}: {keys} != {expected_keys}")
            shapes = {key: handle.get_slice(key).get_shape() for key in keys}
            dtypes = {key: str(handle.get_slice(key).get_dtype()) for key in keys}
        max_end = max(int(row["offset_end"]) for row in shard_rows)
        for key, shape in shapes.items():
            if shape != [max_end, int(spec["hidden_dim"])]:
                raise ValueError(f"shape mismatch for {name}/{key}: {shape}")
            if dtypes[key] != "BF16":
                raise ValueError(f"dtype mismatch for {name}/{key}: {dtypes[key]}")
        shard_summaries.append({"shard": name, "rows": len(shard_rows), "residues": max_end})

    summary = {
        "groups_expected": len(expected),
        "groups_validated": len(actual),
        "shards_validated": len(shard_summaries),
        "total_residues": sum(item["residues"] for item in shard_summaries),
        "feature_variant": spec["feature_variant"],
        "model_id": spec["model_id"],
        "hf_revision": spec["hf_revision"],
        "code_revision": spec["code_revision"],
        "dtype": spec["dtype"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-root", type=Path, required=True)
    parser.add_argument("--groups", type=Path, required=True)
    args = parser.parse_args()
    validate(args.cache_root, args.groups)


if __name__ == "__main__":
    main()
