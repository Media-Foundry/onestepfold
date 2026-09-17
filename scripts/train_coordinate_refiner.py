#!/usr/bin/env python3
"""Train the first C-alpha c2-to-c4 coordinate-refiner baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import random
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import torch

from onestepfold.data.teacher_pair_training import (
    CoordinateRefinerDataset,
    ESMCShardStore,
    LengthAwareCollator,
)
from onestepfold.data.teacher_pairs import load_teacher_pair_manifest
from onestepfold.models import CoordinateRefinerConfig, GlobalCoordinateRefiner


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _seed_everything(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _masked_squared_error(prediction: torch.Tensor, target: torch.Tensor, mask: torch.Tensor):
    squared_distance = (prediction - target).square().sum(dim=-1)
    valid_count = mask.sum().clamp_min(1)
    distance_mse = (squared_distance * mask).sum() / valid_count
    coordinate_mse = distance_mse / 3.0
    return coordinate_mse, distance_mse


def _to_device(batch: dict[str, Any], device: torch.device) -> dict[str, Any]:
    return {
        **batch,
        "residue_features": batch["residue_features"].to(device=device, dtype=torch.float32),
        "backbone_positions": batch["backbone_positions"].to(device),
        "target_ca": batch["target_ca"].to(device),
        "residue_mask": batch["residue_mask"].to(device),
    }


@torch.no_grad()
def evaluate(
    model: GlobalCoordinateRefiner,
    batches: list[dict[str, Any]],
    device: torch.device,
) -> dict[str, float]:
    model.eval()
    prediction_squared = 0.0
    baseline_squared = 0.0
    valid_residues = 0
    max_delta = 0.0
    for cpu_batch in batches:
        batch = _to_device(cpu_batch, device)
        output = model(
            batch["residue_features"],
            batch["backbone_positions"],
            batch["residue_mask"],
        )
        mask = batch["residue_mask"]
        prediction_squared += float(
            (((output["corrected_ca"] - batch["target_ca"]).square().sum(-1)) * mask)
            .sum()
            .item()
        )
        c2_ca = batch["backbone_positions"][..., 1, :]
        baseline_squared += float(
            (((c2_ca - batch["target_ca"]).square().sum(-1)) * mask).sum().item()
        )
        valid_residues += int(mask.sum().item())
        if bool(mask.any()):
            max_delta = max(
                max_delta,
                float(torch.linalg.vector_norm(output["delta_ca"][mask], dim=-1).max().item()),
            )
    if valid_residues == 0:
        raise RuntimeError("evaluation has no valid residues")
    return {
        "valid_residues": float(valid_residues),
        "coordinate_mse": prediction_squared / (3.0 * valid_residues),
        "ca_rmsd": math.sqrt(prediction_squared / valid_residues),
        "baseline_ca_rmsd": math.sqrt(baseline_squared / valid_residues),
        "max_predicted_delta": max_delta,
    }


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--teacher-root", type=Path, required=True)
    parser.add_argument("--esmc-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--split", choices=("train", "validation"), default="train")
    parser.add_argument("--limit", type=int, default=32)
    parser.add_argument("--selection", choices=("shortest", "manifest"), default="shortest")
    parser.add_argument("--epochs", type=int, default=400)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=3e-3)
    parser.add_argument("--hidden-dim", type=int, default=128)
    parser.add_argument("--num-layers", type=int, default=2)
    parser.add_argument("--num-heads", type=int, default=8)
    parser.add_argument("--max-delta-angstrom", type=float, default=8.0)
    parser.add_argument("--seed", type=int, default=101)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--log-every", type=int, default=25)
    parser.add_argument("--require-overfit", action="store_true")
    args = parser.parse_args()
    if args.limit < 1 or args.epochs < 1 or args.batch_size < 1:
        parser.error("limit, epochs, and batch size must be positive")

    _seed_everything(args.seed)
    torch.set_float32_matmul_precision("high")
    device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is not available")

    records = load_teacher_pair_manifest(args.manifest, split=args.split)
    if args.selection == "shortest":
        records.sort(key=lambda record: (record.sequence_length, record.group_id))
    selected = records[: args.limit]
    if len(selected) != args.limit:
        raise ValueError(f"requested {args.limit} records but selected {len(selected)}")

    started = time.monotonic()
    esmc_store = ESMCShardStore(args.esmc_root)
    dataset = CoordinateRefinerDataset(selected, args.teacher_root, esmc_store)
    examples = []
    for index in range(len(dataset)):
        example = dataset[index]
        examples.append(example)
        print(
            f"loaded {index + 1}/{len(dataset)} {example.group_id} "
            f"L={example.sequence_length} baseline_ca_rmsd={example.baseline_ca_rmsd:.6f}",
            flush=True,
        )
    collator = LengthAwareCollator(pad_to_multiple=8)
    batches = [
        collator(examples[start : start + args.batch_size])
        for start in range(0, len(examples), args.batch_size)
    ]
    max_length = max(example.sequence_length for example in examples)
    config = CoordinateRefinerConfig(
        input_dim=int(esmc_store.feature_spec["hidden_dim"]),
        hidden_dim=args.hidden_dim,
        num_layers=args.num_layers,
        num_heads=args.num_heads,
        dropout=0.0,
        max_length=max(1024, max_length),
        max_delta_angstrom=args.max_delta_angstrom,
    )
    model = GlobalCoordinateRefiner(config).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=args.learning_rate, weight_decay=0.0
    )
    initial = evaluate(model, batches, device)
    best_metrics = dict(initial)
    best_epoch = 0
    best_state = {
        name: tensor.detach().cpu().clone() for name, tensor in model.state_dict().items()
    }
    history: list[dict[str, float | int]] = []
    maximum_gradient_norm = 0.0
    for epoch in range(1, args.epochs + 1):
        model.train()
        order = list(range(len(batches)))
        random.Random(args.seed + epoch).shuffle(order)
        epoch_loss = 0.0
        for batch_index in order:
            batch = _to_device(batches[batch_index], device)
            optimizer.zero_grad(set_to_none=True)
            output = model(
                batch["residue_features"],
                batch["backbone_positions"],
                batch["residue_mask"],
            )
            loss, _ = _masked_squared_error(
                output["corrected_ca"], batch["target_ca"], batch["residue_mask"]
            )
            if not bool(torch.isfinite(loss)):
                raise RuntimeError(f"non-finite loss at epoch {epoch}")
            loss.backward()
            gradient_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=10.0)
            if not bool(torch.isfinite(gradient_norm)):
                raise RuntimeError(f"non-finite gradient at epoch {epoch}")
            maximum_gradient_norm = max(maximum_gradient_norm, float(gradient_norm.item()))
            optimizer.step()
            epoch_loss += float(loss.item())
        metrics = evaluate(model, batches, device)
        metrics["epoch"] = epoch
        metrics["mean_batch_loss"] = epoch_loss / len(batches)
        history.append(metrics)
        if metrics["coordinate_mse"] < best_metrics["coordinate_mse"]:
            best_metrics = dict(metrics)
            best_epoch = epoch
            best_state = {
                name: tensor.detach().cpu().clone() for name, tensor in model.state_dict().items()
            }
        if epoch == 1 or epoch % args.log_every == 0 or epoch == args.epochs:
            print(json.dumps(metrics, sort_keys=True), flush=True)

    model.load_state_dict(best_state)
    final = evaluate(model, batches, device)
    mse_ratio = final["coordinate_mse"] / max(initial["coordinate_mse"], 1e-12)
    rmsd_ratio = final["ca_rmsd"] / max(final["baseline_ca_rmsd"], 1e-12)
    overfit_pass = mse_ratio <= 0.10 and rmsd_ratio <= 0.50
    args.output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = args.output_dir / "best.pt"
    torch.save(
        {
            "schema_version": "coordinate-refiner-checkpoint-v1",
            "model_config": asdict(config),
            "model_state_dict": best_state,
            "best_epoch": best_epoch,
            "selected_group_ids": [record.group_id for record in selected],
            "teacher_manifest_sha256": _sha256(args.manifest),
            "esmc_manifest_sha256": _sha256(args.esmc_root / "manifest.jsonl.gz"),
        },
        checkpoint_path,
    )
    report = {
        "schema_version": "coordinate-refiner-overfit-v1",
        "complete": True,
        "overfit_pass": overfit_pass,
        "criteria": {
            "maximum_final_to_initial_coordinate_mse_ratio": 0.10,
            "maximum_final_to_c2_baseline_ca_rmsd_ratio": 0.50,
        },
        "selection": {
            "split": args.split,
            "strategy": args.selection,
            "count": len(selected),
            "group_ids": [record.group_id for record in selected],
            "lengths": [record.sequence_length for record in selected],
        },
        "data": {
            "teacher_manifest": str(args.manifest),
            "teacher_manifest_sha256": _sha256(args.manifest),
            "teacher_root": str(args.teacher_root),
            "esmc_root": str(args.esmc_root),
            "esmc_manifest_sha256": _sha256(args.esmc_root / "manifest.jsonl.gz"),
            "target": "c4 CA rigidly Kabsch-aligned into the c2 CA frame",
        },
        "model_config": asdict(config),
        "optimization": {
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "learning_rate": args.learning_rate,
            "seed": args.seed,
            "maximum_preclip_gradient_norm": maximum_gradient_norm,
        },
        "initial": initial,
        "best": best_metrics,
        "best_epoch": best_epoch,
        "final_best_checkpoint": final,
        "final_to_initial_coordinate_mse_ratio": mse_ratio,
        "final_to_c2_baseline_ca_rmsd_ratio": rmsd_ratio,
        "checkpoint": str(checkpoint_path),
        "checkpoint_sha256": _sha256(checkpoint_path),
        "runtime": {
            "elapsed_seconds": time.monotonic() - started,
            "python": platform.python_version(),
            "torch": torch.__version__,
            "device": str(device),
            "device_name": torch.cuda.get_device_name(device) if device.type == "cuda" else "cpu",
        },
        "history": history,
    }
    _write_json_atomic(args.output_dir / "overfit_report.json", report)
    print(json.dumps({key: value for key, value in report.items() if key != "history"}, indent=2))
    if args.require_overfit and not overfit_pass:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
