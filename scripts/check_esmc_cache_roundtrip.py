#!/usr/bin/env python3
"""Recompute one ESMC sequence and compare it with a cached BF16 slice."""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
from typing import Any

import torch
from build_esmc_cache import _extract_batch, _load_model
from safetensors import safe_open


def read_rows(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-root", type=Path, required=True)
    parser.add_argument("--groups", type=Path, required=True)
    parser.add_argument("--group-id", default=None)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--local-files-only", action="store_true")
    args = parser.parse_args()

    spec = json.loads((args.cache_root / "feature_spec.json").read_text())
    manifests = read_rows(args.cache_root / "manifest.jsonl.gz")
    if args.group_id is None:
        row = manifests[len(manifests) // 2]
    else:
        row = next(item for item in manifests if str(item["group_id"]) == args.group_id)
    groups = {str(item["group_id"]): item for item in read_rows(args.groups)}
    sequence = str(groups[str(row["group_id"])]["sequence"])

    shard = args.cache_root / str(row["shard"])
    with safe_open(str(shard), framework="pt", device="cpu") as handle:
        cached = handle.get_tensor("final")[
            int(row["offset_start"]) : int(row["offset_end"])
        ].float()
    model, tokenizer = _load_model(
        spec["model_id"], spec["hf_revision"], args.device, args.local_files_only
    )
    recomputed = _extract_batch(model, tokenizer, [sequence], args.device, "final")[0][
        "final"
    ].float()
    if cached.shape != recomputed.shape:
        raise ValueError(f"shape mismatch: cached={cached.shape} recomputed={recomputed.shape}")
    result = {
        "group_id": row["group_id"],
        "sequence_length": len(sequence),
        "shape": list(cached.shape),
        "cosine_similarity": float(
            torch.nn.functional.cosine_similarity(cached.reshape(1, -1), recomputed.reshape(1, -1))
        ),
        "maximum_absolute_error": float(torch.max(torch.abs(cached - recomputed))),
        "model_id": spec["model_id"],
        "hf_revision": spec["hf_revision"],
        "code_revision": spec["code_revision"],
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
