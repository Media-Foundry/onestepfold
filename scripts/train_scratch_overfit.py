#!/usr/bin/env python3
"""TRAIN4 scratch supervision comparison; no pretrained folding weights or held-out use."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import time
from pathlib import Path
from unittest.mock import patch

import numpy as np
import torch
from train_esmc_capacity import INITIAL_HASH, save_checkpoint, seed

from fastglycan.articulated_output import ArticulatedOutput
from fastglycan.capacity_b import atom_score, strict_single_pass
from fastglycan.capacity_c import (
    EVAL_SEEDS,
    MAX_EXPOSURES,
    epoch_schedule,
    select_indices,
)
from fastglycan.scratch_overfit import SMOOTH_WEIGHT, MIN_LDDT, summarize_rows
from fastglycan.smooth_lddt_supervision import build_smooth_lddt_labels, smooth_lddt_loss
from fastglycan.scaling_metrics import quality_metrics
from fastglycan.distance_supervision import build_distance_labels, observed_distance_mse
from fastglycan.experimental_geometry import compare_local_geometry
from fastglycan.experimental_metrics import compare_experimental
from fastglycan.experimental_training import map_experimental_atoms, observed_aligned_mse
from fastglycan.frame_attribution import frame_partitions
from fastglycan.frame_supervision import build_frame_labels, local_frame_mse
from fastglycan.models.esmc_core import ESMCFoldCore
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.teacher_pairing import feature_digest


def prepare(parent, parent_root, index, root):
    record, provenance = parent["selection"][index], parent["input_provenance"][index]
    group = record["group_id"]
    assert record["split"] == provenance["split"] == "train"
    assert provenance["group_id"] == group
    old, folder = Path(parent["baseline_root"]) / group, root / group
    folder.mkdir()
    for name, key in [
        ("inputs.pt", "inputs_sha256"),
        ("gt.npz", "gt_npz_sha256"),
        ("gt.json", "gt_metadata_sha256"),
    ]:
        assert sha256(old / name) == provenance[key]
    packet = torch.load(old / "inputs.pt", map_location="cpu", weights_only=True)
    features, labels = packet["features"], packet["labels"]
    assert feature_digest(features) == provenance["feature_sha256"]
    for name in ("gt.npz", "gt.json", "inventory.npz"):
        shutil.copy2(old / name, folder / name)
    with np.load(folder / "inventory.npz") as d:
        inventory = dict(d)
    with np.load(folder / "gt.npz") as d:
        arrays = dict(d)
    mapped = map_experimental_atoms(
        arrays,
        json.loads((folder / "gt.json").read_text()),
        record["sequence"],
        record["sample_id"],
        inventory,
    )
    assert feature_digest(mapped) == feature_digest(labels)
    np.savez_compressed(folder / "labels.npz", **{k: v.numpy() for k, v in labels.items()})
    frame = build_frame_labels(labels, inventory)
    same = frame_partitions(frame, inventory["residue_id"])["same_residue"]
    distances = build_distance_labels(labels, inventory)
    assert distances["category"].bincount(minlength=4).min() > 0
    supervision = {"frame": frame, "same": same, "distance": distances}
    save_checkpoint(folder / "supervision.pt", supervision)
    shutil.copy2(parent_root / "articulation_report.json", folder / "articulation_report.json")
    variants = json.loads((folder / "articulation_report.json").read_text())["variants"]
    assert features["ref_mask"].bool().all()
    adapter = ArticulatedOutput(
        features["ref_pos"].numpy(),
        inventory["atom_name"],
        inventory["residue_id"],
        record["sequence"],
        variants,
    ).float()
    adapter_hash = feature_digest(adapter.state_dict())
    assert adapter_hash == parent["adapter_provenance"][index]["state_sha256"]
    np.savez_compressed(folder / "reference.npz", reference=features["ref_pos"].numpy())
    info = {
        "parent_index": index,
        "selection": record,
        "input_provenance": provenance,
        "input_path": str(old / "inputs.pt"),
        "adapter_sha256": adapter_hash,
        "articulation_report_sha256": sha256(folder / "articulation_report.json"),
    }
    for name in ("labels", "supervision", "inventory", "reference"):
        info[name + "_sha256"] = sha256(
            folder / (name + (".pt" if name == "supervision" else ".npz"))
        )
    return {
        "features": features,
        "labels": labels,
        "inventory": inventory,
        "arrays": arrays,
        "adapter": adapter.cuda(),
        "supervision": supervision,
        "info": info,
    }


def main():
    parser = argparse.ArgumentParser()
    for name in ("parent", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--arm", choices=("baseline", "smooth_lddt"), required=True)
    parser.add_argument("--size", type=int, choices=(4,), required=True)
    parser.add_argument("--single-index", type=int)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    indices = select_indices(args.size, args.single_index)
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    os.chdir(root)
    started = time.monotonic()
    optimization_start = None
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    parent = json.loads((args.parent / "contract.json").read_text())
    prior = json.loads((args.parent / "report.json").read_text())
    qa = json.loads((args.parent / "independent_validation.json").read_text())
    assert qa["complete"] and qa["heavy_artifacts_checked"]
    assert (
        sha256(args.parent / "report.json")
        == qa["report_sha256"]
        == ("57c9863836acf674202d7e4100299a1c11c5cca07fb83964d0ebf797c3b86379")
    )
    assert sha256(args.parent / "contract.json") == prior["contract_sha256"]
    source = Path(__file__).resolve().parents[1]
    for name in (
        "models/esmc_core.py",
        "articulated_output.py",
        "articulated_reference.py",
        "frame_supervision.py",
        "frame_attribution.py",
        "distance_supervision.py",
        "experimental_training.py",
    ):
        key = "src/fastglycan/" + name
        assert sha256(source / key) == parent["source_sha256"][key]
    for name, digest in parent["runtime_source_sha256"].items():
        assert sha256(Path(name)) == digest
    packets = [prepare(parent, args.parent, i, root) for i in indices]
    for p in packets:
        p["smooth_labels"] = build_smooth_lddt_labels(p["labels"], p["inventory"])
    groups = [p["info"]["selection"]["group_id"] for p in packets]
    all_seeds = [
        noise for e in range(1, MAX_EXPOSURES + 1) for _, noise in epoch_schedule(groups, e)
    ]
    # Hash seeds and explicitly audit collisions instead of presuming uniqueness.
    collisions = len(all_seeds) - len(set(all_seeds))
    assert not set(all_seeds).intersection(EVAL_SEEDS)
    with patch("torch.load", side_effect=AssertionError("no folding checkpoint input")):
        model = ESMCFoldCore(seed=101, deterministic_capacity=True)
    assert feature_digest(model.state_dict()) == INITIAL_HASH
    assert model.config.to_dict() == parent["config"]
    assert "H100" in torch.cuda.get_device_name(), torch.cuda.get_device_name()
    assert torch.__version__ == "2.7.1+cu128", torch.__version__
    model.cuda().eval()
    for module in (model.core.confidence_head, model.core.distogram_head):
        module.requires_grad_(False)
    frozen_before = feature_digest(
        {n: p for n, p in model.named_parameters() if not p.requires_grad}
    )
    parameters = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(parameters, lr=1e-4, weight_decay=1e-4)
    counts, flags = {}, []

    def hook(name):
        def count(*_):
            counts[name] += 1
            if name == "trunk":
                flags.append(torch.is_grad_enabled())

        return count

    handles = [
        m.register_forward_pre_hook(hook(n))
        for n, m in (
            ("trunk", model.core.pairformer_stack),
            ("structure", model.core.diffusion_module),
            ("confidence", model.core.confidence_head),
        )
    ]
    last = {}

    def execute(packet, noise, train=False):
        model.train(train)
        seed(noise)
        counts.update(trunk=0, structure=0, confidence=0)
        flags.clear()
        with torch.set_grad_enabled(train):
            raw = model(packet["features"], confidence=False)["coordinate"][0]
            out = {"coordinate": raw, "fallback_counts": torch.zeros(3, dtype=torch.long)}
        assert counts == {"trunk": 1, "structure": 1, "confidence": 0} and flags == [train]
        assert torch.isfinite(raw).all() and torch.isfinite(out["coordinate"]).all()
        last.update(raw=raw, fallbacks=out["fallback_counts"].tolist())
        return out["coordinate"]

    def losses(x, p):
        lab, sup = p["labels"], p["supervision"]
        return [
            observed_aligned_mse(x, lab["coordinate"].cuda(), lab["coordinate_mask"].cuda()),
            0.1 * local_frame_mse(x, sup["frame"]),
            local_frame_mse(x, sup["same"]),
            10 * observed_distance_mse(x, sup["distance"]),
            (SMOOTH_WEIGHT if args.arm == "smooth_lddt" else 0.0)
            * smooth_lddt_loss(x, p["smooth_labels"]),
        ]

    def evaluate(epoch, save=None, replay=None):
        rows = []
        for p in packets:
            record = p["info"]["selection"]
            group = record["group_id"]
            for noise in EVAL_SEEDS:
                x = execute(p, noise)
                prediction = dict(p["inventory"]) | {"coordinate": x.cpu().numpy()}
                row = {
                    "group_id": group,
                    "noise": noise,
                    "metrics": compare_experimental(prediction, p["arrays"], record["sequence"]),
                    "geometry": compare_local_geometry(prediction, p["arrays"], record["sequence"]),
                    "quality": quality_metrics(prediction, p["arrays"], record["sequence"]),
                    "smooth_lddt_loss": float(smooth_lddt_loss(x, p["smooth_labels"])),
                    "weighted_losses": [float(v) for v in losses(x, p)],
                    "fallback_counts": last["fallbacks"],
                }
                assert row["metrics"]["predicted_gt_coverage"] == 1
                if save:
                    path = root / group / f"{save}_{noise}.npz"
                    np.savez_compressed(
                        path, **prediction, raw_coordinate=last["raw"].cpu().numpy()
                    )
                    row["prediction_sha256"] = sha256(path)
                if replay:
                    with np.load(root / group / f"{replay}_{noise}.npz") as d:
                        assert np.array_equal(x.cpu().numpy(), d["coordinate"])
                        assert np.array_equal(last["raw"].cpu().numpy(), d["raw_coordinate"])
                rows.append(row)
        return {
            "epoch": epoch,
            "step": epoch * args.size,
            "rows": rows,
            "summary": summarize_rows(rows),
            "elapsed_seconds": time.monotonic() - started,
            "optimization_elapsed_seconds": (time.monotonic() - optimization_start) if optimization_start is not None else 0.0,
        }

    # Audit train/eval identity on the longest selected example before optimization.
    a = execute(packets[-1], 12345).detach().clone()
    b = execute(packets[-1], 12345, True)
    assert torch.equal(a, b.detach())
    del a, b
    initial = evaluate(0, "initial")
    for p in packets:
        group, index = p["info"]["selection"]["group_id"], p["info"]["parent_index"]
        for noise in EVAL_SEEDS:
            path = args.parent / group / f"initial_{noise}.npz"
            assert (
                sha256(path)
                == prior["initial"]["conditions"][str(noise)]["examples"][index][
                    "prediction_sha256"
                ]
            )
            with np.load(path) as old, np.load(root / group / f"initial_{noise}.npz") as new:
                assert np.array_equal(old["raw_coordinate"], new["raw_coordinate"])
    soft_seconds = {1: 2700, 4: 7200, 32: 36000}[args.size]
    contract = {
        "schema": "scratch-overfit-v1",
        "objective_arm": args.arm,
        "smooth_lddt_weight": SMOOTH_WEIGHT if args.arm == "smooth_lddt" else 0.0,
        "smooth_lddt_temperature_angstrom": 0.1,
        "minimum_all_atom_lddt": MIN_LDDT,
        "folding_checkpoint_load_calls": 0,
        "gpu_name": torch.cuda.get_device_name(),
        "arm": "raw",
        "size": args.size,
        "indices": indices,
        "examples": [p["info"] for p in packets],
        "parent_root": str(args.parent),
        "parent_report_sha256": sha256(args.parent / "report.json"),
        "parent_contract_sha256": sha256(args.parent / "contract.json"),
        "source_root": str(source),
        "source_manifest_sha256": sha256(source / "source_manifest.json"),
        "runtime_source_sha256": parent["runtime_source_sha256"],
        "initial_weights_sha256": INITIAL_HASH,
        "config": model.config.to_dict(),
        "optimizer": {
            "name": "AdamW",
            "lr": 1e-4,
            "weight_decay": 1e-4,
            "clip": 10,
            "batch_size": 1,
        },
        "max_exposures": MAX_EXPOSURES,
        "soft_seconds": soft_seconds,
        "evaluation_seeds": list(EVAL_SEEDS),
        "evaluation_every_exposures": 50,
        "training_seed_sha256": feature_digest(all_seeds),
        "training_seed_collisions": collisions,
        "selection": "minimum joint normalized score; earliest tie",
        "initial_train_eval_exact": True,
        "initial_raw_exact_parent": True,
        "frozen_parameter_sha256": frozen_before,
        "job_id": os.environ.get("SLURM_JOB_ID"),
        "torch": torch.__version__,
        "matmul_tf32": torch.backends.cuda.matmul.allow_tf32,
        "cudnn_tf32": torch.backends.cudnn.allow_tf32,
    }
    write_json(root / "contract.json", contract)
    assert not initial["summary"]["joint_capacity_pass"]
    history = [initial]
    best_epoch, best_score = 0, initial["summary"]["selection_score"]

    def save(name, epoch, optimizer_state=False):
        data = {
            "model": model.state_dict(),
            "epoch": epoch,
            "step": epoch * args.size,
            "contract_sha256": sha256(root / "contract.json"),
        }
        if optimizer_state:
            data["optimizer"] = optimizer.state_dict()
        save_checkpoint(root / name, data)

    save("best.pt", 0)
    write_json(root / "history.json", history)
    print(
        json.dumps(
            {
                "preflight_complete": True,
                "size": args.size,
                "arm": "raw",
                "indices": indices,
                "seed_collisions": collisions,
            }
        ),
        flush=True,
    )
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    optimization_start = time.monotonic()
    stop, gradient_probe, step = "exposure_budget", None, 0
    for epoch in range(1, MAX_EXPOSURES + 1):
        schedule = epoch_schedule(groups, epoch)
        if args.preflight_only:
            schedule = [(i, noise) for i, noise in schedule if i == len(packets) - 1]
        for index, noise in schedule:
            optimizer.zero_grad(set_to_none=True)
            x = execute(packets[index], noise, True)
            values = losses(x, packets[index])
            loss = sum(values)
            assert torch.isfinite(loss)
            loss.backward()
            norm = torch.nn.utils.clip_grad_norm_(parameters, 10, error_if_nonfinite=True)
            if gradient_probe is None:
                front = model.core.input_embedder.linear_esm.weight
                head = model.core.diffusion_module.atom_attention_decoder.linear_no_bias_out.weight
                assert front.grad is not None and front.grad.norm() > 0
                assert head.grad is not None and head.grad.norm() > 0
                gradient_probe = {
                    "front_norm": float(front.grad.norm()),
                    "head_norm": float(head.grad.norm()),
                    "preclip_norm": float(norm),
                    "cycle_grad_flags": [True],
                }
                write_json(root / "gradient_probe.json", gradient_probe)
            if args.preflight_only:
                write_json(
                    root / "preflight.json",
                    {
                        "complete": True,
                        "optimizer_updates": 0,
                        "initial_predictions_checked": 2 * args.size,
                        "gradient_probe": gradient_probe,
                        "longest_group": groups[index],
                        "contract_sha256": sha256(root / "contract.json"),
                    },
                )
                print("GPU preflight passed; zero optimizer updates", flush=True)
                return
            optimizer.step()
            step += 1
            row = {
                "objective_arm": args.arm,
                "epoch": epoch,
                "step": step,
                "group_id": groups[index],
                "noise": noise,
                "weighted_losses": [float(v.detach()) for v in values],
                "preclip_norm": float(norm),
                "fallback_counts": last["fallbacks"],
                "elapsed_seconds": time.monotonic() - started,
            }
            with (root / "training.jsonl").open("a") as handle:
                handle.write(json.dumps(row) + "\n")
            del x, values, loss
        write_json(root / "progress.json", row)
        exceeded = time.monotonic() - optimization_start >= soft_seconds
        if epoch % 50 and not exceeded:
            continue
        optimizer.zero_grad(set_to_none=True)
        evaluation = evaluate(epoch)
        history.append(evaluation)
        score = evaluation["summary"]["selection_score"]
        if score < best_score:
            best_epoch, best_score = epoch, score
            save("best.pt", epoch)
        save("last.pt", epoch, True)
        write_json(root / "history.json", history)
        print(
            json.dumps({k: evaluation[k] for k in ("epoch", "step", "summary", "elapsed_seconds")}),
            flush=True,
        )
        if evaluation["summary"]["joint_capacity_pass"] or exceeded:
            stop = (
                "joint_capacity_pass"
                if evaluation["summary"]["joint_capacity_pass"]
                else "soft_time_budget"
            )
            break
    final_last = evaluate(epoch, "last")
    saved = torch.load(root / "best.pt", map_location="cpu", weights_only=True)
    assert saved["epoch"] == best_epoch and saved["contract_sha256"] == sha256(
        root / "contract.json"
    )
    model.load_state_dict(saved["model"], strict=True)
    del saved
    best = evaluate(best_epoch, "best")
    repeated = evaluate(best_epoch, replay="best")
    expected = next(r for r in history if r["epoch"] == best_epoch)
    assert best["summary"] == expected["summary"] == repeated["summary"]
    for actual, before, twice in zip(best["rows"], expected["rows"], repeated["rows"], strict=True):
        for key in (
            "group_id",
            "noise",
            "metrics",
            "geometry",
            "weighted_losses",
            "quality",
            "smooth_lddt_loss",
            "fallback_counts",
        ):
            assert actual[key] == before[key] == twice[key]
    for p in packets:
        assert feature_digest(p["features"]) == p["info"]["input_provenance"]["feature_sha256"]
        assert feature_digest(p["adapter"].state_dict()) == p["info"]["adapter_sha256"]
    assert (
        feature_digest({n: p for n, p in model.named_parameters() if not p.requires_grad})
        == frozen_before
    )
    assert all(torch.isfinite(p).all() for p in parameters)
    report = {
        "complete": True,
        "objective_arm": args.arm,
        "arm": "raw",
        "size": args.size,
        "steps": step,
        "optimization_elapsed_seconds": history[-1]["optimization_elapsed_seconds"],
        "last_epoch": epoch,
        "best_epoch": best_epoch,
        "stop_reason": stop,
        "initial": initial,
        "best": best,
        "last": final_last,
        "joint_capacity_pass": best["summary"]["joint_capacity_pass"],
        "gradient_probe": gradient_probe,
        "best_replay_exact": True,
        "inputs_adapters_frozen_weights_unchanged": True,
        "contract_sha256": sha256(root / "contract.json"),
        "best_checkpoint_sha256": sha256(root / "best.pt"),
        "last_checkpoint_sha256": sha256(root / "last.pt"),
        "history_sha256": sha256(root / "history.json"),
        "training_sha256": sha256(root / "training.jsonl"),
        "peak_gpu_allocated_bytes": torch.cuda.max_memory_allocated(),
        "elapsed_seconds": time.monotonic() - started,
    }
    # Per-example view supports the independently implemented CPU coordinate audit.
    for p in packets:
        group = p["info"]["selection"]["group_id"]
        view = {"arm": "raw", "smooth_lddt_weight": SMOOTH_WEIGHT if args.arm == "smooth_lddt" else 0.0, **p["info"]}
        write_json(root / group / "example_contract.json", view)
        result = {}
        for condition in ("initial", "best", "last"):
            rows = [r for r in report[condition]["rows"] if r["group_id"] == group]
            result[condition] = {
                "rows": rows,
                "atom_score": atom_score(rows),
                "strict_single_pass": strict_single_pass(rows),
            }
        write_json(root / group / "example_report.json", result)
    write_json(root / "report.json", report)
    for handle in handles:
        handle.remove()
    print(
        json.dumps({"complete": True, "best_epoch": best_epoch, "summary": best["summary"]}),
        flush=True,
    )


if __name__ == "__main__":
    main()
