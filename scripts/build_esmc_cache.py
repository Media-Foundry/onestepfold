#!/usr/bin/env python3
"""Extract pinned Biohub ESMC residue features into sharded safetensors."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import time
from pathlib import Path
from typing import Any

import torch

from onestepfold.data.esmc_cache import (
    ESMCFeatureSpec,
    assert_finite_residue_tensor,
    select_feature_layers,
    sequence_sha256,
    strip_special_tokens,
)


def _read_groups(path: Path, limit: int | None) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle if line.strip()]
    rows.sort(key=lambda row: str(row["group_id"]))
    return rows if limit is None else rows[:limit]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_model(model_id: str, revision: str, device: str):
    try:
        from esm.models.esmc import EsmcForMaskedLM, EsmcTokenizer
    except ImportError as exc:  # pragma: no cover - HPC-only optional dependency
        raise RuntimeError(
            "Biohub esm is required; install the pinned Biohub/esm revision"
        ) from exc
    # Require the current Hugging-Face-compatible Biohub API. The legacy local
    # ESMC loader has a different checkpoint and hidden-state contract.
    model = EsmcForMaskedLM.from_pretrained(
        model_id, revision=revision, device=device
    ).eval()
    return model, EsmcTokenizer()


def _extract_batch(model: Any, tokenizer: Any, sequences: list[str], device: str, variant: str):
    inputs = tokenizer(sequences, return_tensors="pt", padding=True)
    attention = inputs.get("attention_mask")
    inputs = {key: value.to(device) for key, value in inputs.items()}
    need_hidden_states = variant != "final"
    with torch.inference_mode():
        output = model(
            **inputs,
            output_hidden_states=need_hidden_states,
            compute_sae=False,
        )
    if need_hidden_states:
        hidden_states = output.hidden_states
        if hidden_states is None:
            raise RuntimeError("ESMC did not return hidden states for this variant")
        selected = select_feature_layers(hidden_states, variant)
    else:
        final = getattr(output, "last_hidden_state", None)
        if final is None:
            final = getattr(output, "embeddings", None)
        if final is None:
            raise RuntimeError("ESMC output has neither last_hidden_state nor embeddings")
        selected = {"final": final}
    result: list[dict[str, torch.Tensor]] = []
    for batch_index, sequence in enumerate(sequences):
        token_length = (
            int(attention[batch_index].sum())
            if attention is not None
            else len(sequence) + 2
        )
        residue_features: dict[str, torch.Tensor] = {}
        for name, tensor in selected.items():
            unpadded = tensor[batch_index, :token_length]
            residue = strip_special_tokens(unpadded, len(sequence))
            assert_finite_residue_tensor(residue, len(sequence))
            residue_features[name] = residue.detach().to(device="cpu", dtype=torch.bfloat16)
        result.append(residue_features)
    return result


def build_cache(
    groups_path: Path,
    output_root: Path,
    model_id: str,
    hf_revision: str,
    code_revision: str,
    feature_variant: str,
    device: str = "cuda",
    batch_tokens: int = 4096,
    shard_tokens: int = 16384,
    limit: int | None = None,
    code_commit: str | None = None,
) -> dict[str, Any]:
    groups = _read_groups(groups_path, limit)
    if not groups:
        raise ValueError("no sequence groups selected")
    hidden_dim = 1152 if "600" in model_id else 960 if "300" in model_id else 2560
    num_layers = 36 if "600" in model_id else 30 if "300" in model_id else 80
    spec = ESMCFeatureSpec(
        model_id=model_id,
        hf_revision=hf_revision,
        code_revision=code_revision,
        feature_variant=feature_variant,
        hidden_dim=hidden_dim,
        num_layers=num_layers,
    )
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "feature_spec.json").write_text(
        json.dumps(spec.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    model, tokenizer = _load_model(model_id, hf_revision, device)
    writer_rows: list[dict[str, Any]] = []
    shard_tensors: dict[str, list[torch.Tensor]] = {}
    shard_rows: list[dict[str, Any]] = []
    shard_residues = 0
    shard_id = 0
    total_residues = 0
    processed = 0
    started = time.monotonic()
    batch: list[dict[str, Any]] = []
    batch_tokens_used = 0

    def flush_shard() -> None:
        nonlocal shard_id, shard_residues, shard_tensors, shard_rows
        if not shard_rows:
            return
        try:
            from safetensors.torch import save_file
        except ImportError as exc:  # pragma: no cover - HPC-only optional dependency
            raise RuntimeError("safetensors is required for the embedding cache") from exc
        tensors = {
            name: torch.cat(values, dim=0).contiguous()
            for name, values in shard_tensors.items()
        }
        path = output_root / f"shard-{shard_id:05d}.safetensors"
        save_file(
            tensors,
            str(path),
            metadata={"feature_spec": json.dumps(spec.as_dict(), sort_keys=True)},
        )
        checksum = _sha256_file(path)
        for row in shard_rows:
            row["shard"] = path.name
            row["shard_sha256"] = checksum
            writer_rows.append(row)
        shard_id += 1
        shard_residues = 0
        shard_tensors = {}
        shard_rows = []

    def add_item(group: dict[str, Any], features: dict[str, torch.Tensor]) -> None:
        nonlocal shard_residues, total_residues, processed
        length = int(group["sequence_length"])
        if any(int(t.shape[0]) != length for t in features.values()):
            raise ValueError(f"feature length mismatch for {group['group_id']}")
        if any(int(t.shape[-1]) != hidden_dim for t in features.values()):
            raise ValueError(f"feature dimension mismatch for {group['group_id']}")
        if shard_rows and shard_residues + length > shard_tokens:
            flush_shard()
        offset_start = shard_residues
        offset_end = offset_start + length
        for name, tensor in features.items():
            shard_tensors.setdefault(name, []).append(
                tensor
            )
        shard_rows.append(
            {
                "group_id": group["group_id"],
                "sequence_sha256": sequence_sha256(group["sequence"]),
                "sequence_length": length,
                "offset_start": offset_start,
                "offset_end": offset_end,
                "storage_axis": 0,
                "feature_names": sorted(features),
                "feature_variant": feature_variant,
                "model_id": model_id,
                "hf_revision": hf_revision,
                "code_revision": code_revision,
                "dtype": "bfloat16",
            }
        )
        shard_residues += length
        total_residues += length
        processed += 1

    for group in groups:
        sequence = str(group["sequence"])
        if batch and batch_tokens_used + len(sequence) > batch_tokens:
            sequences = [str(row["sequence"]) for row in batch]
            extracted = _extract_batch(model, tokenizer, sequences, device, feature_variant)
            for row, features in zip(batch, extracted, strict=True):
                add_item(row, features)
            batch = []
            batch_tokens_used = 0
        batch.append(group)
        batch_tokens_used += len(sequence)
    if batch:
        extracted = _extract_batch(
            model, tokenizer, [str(row["sequence"]) for row in batch], device, feature_variant
        )
        for row, features in zip(batch, extracted, strict=True):
            add_item(row, features)
    flush_shard()
    manifest = output_root / "manifest.jsonl.gz"
    with manifest.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed:
            for row in sorted(writer_rows, key=lambda item: str(item["group_id"])):
                compressed.write((json.dumps(row, sort_keys=True) + "\n").encode("utf-8"))
    summary = {
        "groups_input": len(groups),
        "groups_processed": processed,
        "total_residues": total_residues,
        "shard_count": shard_id,
        "feature_variant": feature_variant,
        "model_id": model_id,
        "hf_revision": hf_revision,
        "code_revision": code_revision,
        "code_commit": code_commit,
        "dtype": "bfloat16",
        "elapsed_seconds": time.monotonic() - started,
        "output": str(output_root),
    }
    (output_root / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--groups", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--model-id", default="biohub/ESMC-600M")
    parser.add_argument("--hf-revision", required=True)
    parser.add_argument("--code-revision", required=True)
    parser.add_argument("--code-commit", default=None)
    parser.add_argument(
        "--feature-variant",
        choices=("final", "layers_12_24_36", "all"),
        default="all",
    )
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--batch-tokens", type=int, default=4096)
    parser.add_argument("--shard-tokens", type=int, default=16384)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    build_cache(
        args.groups,
        args.output_root,
        args.model_id,
        args.hf_revision,
        args.code_revision,
        args.feature_variant,
        args.device,
        args.batch_tokens,
        args.shard_tokens,
        args.limit,
        args.code_commit,
    )


if __name__ == "__main__":
    main()
