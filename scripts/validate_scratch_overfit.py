#!/usr/bin/env python3
"""Independent saved-output CPU acceptance for the scratch supervision comparison."""

import argparse
import json
from pathlib import Path

import numpy as np
import torch

from fastglycan.articulated_gradient_diagnostics import independent_losses
from fastglycan.articulated_output import ArticulatedOutput
from fastglycan.articulated_validation import numpy_project
from fastglycan.capacity_b import all_frame_labels, atom_score, strict_single_pass
from fastglycan.capacity_c import (
    EVAL_SEEDS,
    MAX_EXPOSURES,
    epoch_schedule,
    select_indices,
)
from fastglycan.scratch_overfit import SMOOTH_WEIGHT, MIN_LDDT, summarize_rows
from fastglycan.scaling_metrics import quality_metrics
from fastglycan.distance_supervision import build_distance_labels
from fastglycan.experimental_geometry import compare_local_geometry
from fastglycan.experimental_metrics import compare_experimental
from fastglycan.experimental_training import map_experimental_atoms
from fastglycan.frame_attribution import frame_partitions
from fastglycan.frame_supervision import build_frame_labels
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.teacher_pairing import feature_digest
from onestepfold.data.gt_materializer import ATOM37_INDEX


def dense_lddt_reference(prediction, target, residue):
    """Independent FP64 dense-row computation, without sparse training labels."""
    x, y = np.asarray(prediction, dtype=np.float64), np.asarray(target, dtype=np.float64)
    hard_scores, soft_scores = [], []
    thresholds = np.array([0.5, 1.0, 2.0, 4.0])
    for start in range(0, len(x), 64):
        stop = min(start + 64, len(x))
        dx = np.linalg.norm(x[start:stop, None] - x[None, :], axis=-1)
        dy = np.linalg.norm(y[start:stop, None] - y[None, :], axis=-1)
        mask = (dy < 15.0) & (residue[start:stop, None] != residue[None, :])
        error = np.abs(dx - dy)
        hard = (error[..., None] < thresholds).mean(-1)
        logistic = 1.0 / (1.0 + np.exp(np.clip((error[..., None] - thresholds) / 0.1, -700, 700)))
        soft = logistic.mean(-1)
        count = mask.sum(-1)
        valid = count > 0
        hard_scores.extend(((hard * mask).sum(-1)[valid] / count[valid]).tolist())
        soft_scores.extend(((soft * mask).sum(-1)[valid] / count[valid]).tolist())
    assert hard_scores
    return float(np.mean(hard_scores)), float(1.0 - np.mean(soft_scores))


def validate_example(root, contract, report):
    for name in ("labels", "supervision", "inventory", "reference"):
        path = root / (name + (".pt" if name == "supervision" else ".npz"))
        assert sha256(path) == contract[name + "_sha256"]
    assert sha256(root / "articulation_report.json") == contract["articulation_report_sha256"]
    selection = contract["selection"]
    provenance = contract["input_provenance"]
    assert sha256(root / "gt.npz") == provenance["gt_npz_sha256"]
    assert sha256(root / "gt.json") == provenance["gt_metadata_sha256"]
    assert sha256(Path(contract["input_path"])) == provenance["inputs_sha256"]
    with np.load(root / "inventory.npz") as data:
        inventory = dict(data)
    with np.load(root / "gt.npz") as data:
        arrays = dict(data)
    labels = map_experimental_atoms(
        arrays,
        json.loads((root / "gt.json").read_text()),
        selection["sequence"],
        selection["sample_id"],
        inventory,
    )
    with np.load(root / "labels.npz") as data:
        for key, value in labels.items():
            assert np.array_equal(data[key], value.numpy())
    # Independently reconstruct observed masks and fixed atom-name mapping.
    ri = inventory["residue_id"].astype(int) - 1
    ai = np.array([ATOM37_INDEX[str(n)] for n in inventory["atom_name"]])
    mask = arrays["atom37_mask"][ri, ai] & arrays["residue_mask"][ri]
    assert np.array_equal(mask, labels["coordinate_mask"].numpy())
    target = labels["coordinate"].numpy()
    assert np.array_equal(target[mask], arrays["atom37_positions"][ri[mask], ai[mask]])
    local = build_frame_labels(labels, inventory)
    frame = all_frame_labels(labels, inventory) if contract["arm"] == "allframe" else local
    same = frame_partitions(local, inventory["residue_id"])["same_residue"]
    distance = build_distance_labels(labels, inventory)
    supervision = torch.load(root / "supervision.pt", map_location="cpu", weights_only=True)
    assert feature_digest(supervision) == feature_digest(
        {"frame": frame, "same": same, "distance": distance}
    )
    if contract["arm"] == "allframe":
        for i, anchors in enumerate(frame["frame_atoms"]):
            points = frame["point_indices"][frame["frame_rows"] == i].numpy()
            assert np.array_equal(
                points, np.flatnonzero(mask & (np.arange(len(mask)) != int(anchors[1])))
            )
    with np.load(root / "reference.npz") as data:
        reference = data["reference"]
    variants = json.loads((root / "articulation_report.json").read_text())["variants"]
    adapter = ArticulatedOutput(
        reference, inventory["atom_name"], inventory["residue_id"], selection["sequence"], variants
    ).float()
    assert feature_digest(adapter.state_dict()) == contract["adapter_sha256"]
    adapter.double()
    errors, loss_errors, metric_errors = [], [], []
    for condition in ("initial", "best", "last"):
        rows = report[condition]["rows"]
        assert atom_score(rows) == report[condition]["atom_score"]
        assert strict_single_pass(rows) == report[condition]["strict_single_pass"]
        for row in rows:
            path = root / f"{condition}_{row['noise']}.npz"
            assert sha256(path) == row["prediction_sha256"]
            with np.load(path) as data:
                prediction = {k: data[k] for k in inventory} | {"coordinate": data["coordinate"]}
                for key in inventory:
                    assert np.array_equal(data[key], inventory[key])
                raw = data["raw_coordinate"].astype(np.float64)
                x = data["coordinate"].astype(np.float64)
            if contract["arm"] == "raw":
                projected, counts = raw, np.zeros(3, dtype=int)
            else:
                projected, counts = numpy_project(raw, adapter)
            error = float(np.max(np.abs(x - projected)))
            assert error <= 1e-4, error
            errors.append(error)
            assert counts.tolist() == row["fallback_counts"]
            metrics = compare_experimental(prediction, arrays, selection["sequence"])
            geometry = compare_local_geometry(prediction, arrays, selection["sequence"])
            assert metrics == row["metrics"] and geometry == row["geometry"]
            independent = independent_losses(
                torch.tensor(x), target, mask, frame, same, distance
            ).numpy()
            quality = quality_metrics(prediction, arrays, selection["sequence"])
            assert quality == row["quality"]
            hard_lddt, smooth = dense_lddt_reference(x[mask], target[mask], ri[mask])
            assert abs(hard_lddt - quality["all_atom_lddt"]) < 1e-12
            assert abs(smooth - row["smooth_lddt_loss"]) < 3e-6
            independent = np.append(independent, contract["smooth_lddt_weight"] * smooth)
            delta = np.abs(independent - row["weighted_losses"])
            assert np.allclose(independent, row["weighted_losses"], atol=1e-3, rtol=2e-5), delta
            loss_errors.append(delta.tolist())
            error = abs(np.sqrt(independent[0]) - metrics["all_heavy_atom_rmsd"])
            assert error < 1e-5
            metric_errors.append(error)
    return {
        "predictions_checked": 6,
        "max_projection_error": max(errors),
        "max_loss_errors": np.max(loss_errors, axis=0).tolist(),
        "max_independent_rmsd_error": max(metric_errors),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root
    torch.set_num_threads(1)
    report = json.loads((root / "report.json").read_text())
    contract = json.loads((root / "contract.json").read_text())
    assert report["complete"] and report["best_replay_exact"]
    assert contract["schema"] == "scratch-overfit-v1"
    assert contract["size"] == 4 and contract["arm"] == "raw"
    assert contract["folding_checkpoint_load_calls"] == 0
    assert contract["minimum_all_atom_lddt"] == MIN_LDDT
    assert contract["smooth_lddt_temperature_angstrom"] == 0.1
    assert contract["smooth_lddt_weight"] == (SMOOTH_WEIGHT if contract["objective_arm"] == "smooth_lddt" else 0.0)
    assert sha256(root / "contract.json") == report["contract_sha256"]
    for name, key in (
        ("best.pt", "best_checkpoint_sha256"),
        ("last.pt", "last_checkpoint_sha256"),
        ("history.json", "history_sha256"),
        ("training.jsonl", "training_sha256"),
    ):
        assert sha256(root / name) == report[key]
    source = Path(contract["source_root"])
    assert sha256(source / "source_manifest.json") == contract["source_manifest_sha256"]
    manifest = json.loads((source / "source_manifest.json").read_text())
    for name, digest in manifest["files"].items():
        assert sha256(source / name) == digest
    for name, digest in contract["runtime_source_sha256"].items():
        assert sha256(Path(name)) == digest
    parent_root = Path(contract["parent_root"])
    assert sha256(parent_root / "report.json") == contract["parent_report_sha256"]
    assert sha256(parent_root / "contract.json") == contract["parent_contract_sha256"]
    parent = json.loads((parent_root / "contract.json").read_text())
    n = contract["size"]
    indices = select_indices(n, contract["indices"][0] if n == 1 else None)
    assert indices == contract["indices"] and len(contract["examples"]) == n
    results = {}
    for index, info in zip(indices, contract["examples"], strict=True):
        assert info["selection"] == parent["selection"][index]
        assert info["input_provenance"] == parent["input_provenance"][index]
        group = info["selection"]["group_id"]
        folder = root / group
        ec = json.loads((folder / "example_contract.json").read_text())
        er = json.loads((folder / "example_report.json").read_text())
        assert ec == {"arm": contract["arm"], "smooth_lddt_weight": contract["smooth_lddt_weight"], **info}
        for condition in ("initial", "best", "last"):
            rows = [r for r in report[condition]["rows"] if r["group_id"] == group]
            assert rows == er[condition]["rows"]
        results[group] = validate_example(folder, ec, er)
    history = json.loads((root / "history.json").read_text())
    for evaluation in [*history, report["initial"], report["best"], report["last"]]:
        assert summarize_rows(evaluation["rows"]) == evaluation["summary"]
        assert evaluation["step"] == evaluation["epoch"] * n
    best = min(history, key=lambda r: r["summary"]["selection_score"])
    assert best["epoch"] == report["best_epoch"]
    assert best["summary"] == report["best"]["summary"]
    assert report["joint_capacity_pass"] == best["summary"]["joint_capacity_pass"]
    groups = [i["selection"]["group_id"] for i in contract["examples"]]
    seeds = [noise for e in range(1, MAX_EXPOSURES + 1) for _, noise in epoch_schedule(groups, e)]
    assert feature_digest(seeds) == contract["training_seed_sha256"]
    assert len(seeds) - len(set(seeds)) == contract["training_seed_collisions"]
    assert not set(seeds).intersection(EVAL_SEEDS)
    training = [json.loads(line) for line in (root / "training.jsonl").read_text().splitlines()]
    assert len(training) == report["steps"] == report["last_epoch"] * n
    for epoch in range(1, report["last_epoch"] + 1):
        for offset, (index, noise) in enumerate(epoch_schedule(groups, epoch)):
            step = (epoch - 1) * n + offset + 1
            row = training[step - 1]
            assert (row["epoch"], row["step"], row["group_id"], row["noise"]) == (
                epoch,
                step,
                groups[index],
                noise,
            )
            assert np.isfinite(row["weighted_losses"]).all() and np.isfinite(row["preclip_norm"])
    assert contract["max_exposures"] == MAX_EXPOSURES and report["last_epoch"] <= MAX_EXPOSURES
    assert all(not item["summary"]["joint_capacity_pass"] for item in history[:-1])
    assert report["optimization_elapsed_seconds"] == history[-1]["optimization_elapsed_seconds"]
    assert all(item["optimization_elapsed_seconds"] < contract["soft_seconds"] for item in history[:-1])
    if report["stop_reason"] == "joint_capacity_pass":
        assert report["last"]["summary"]["joint_capacity_pass"]
    elif report["stop_reason"] == "exposure_budget":
        assert report["last_epoch"] == MAX_EXPOSURES
    else:
        assert report["stop_reason"] == "soft_time_budget"
        assert report["optimization_elapsed_seconds"] >= contract["soft_seconds"]
    result = {
        "complete": True,
        "report_sha256": sha256(root / "report.json"),
        "source_files_checked": len(manifest["files"]),
        "examples": results,
        "predictions_checked": 6 * n,
        "training_updates_checked": len(training),
        "checkpoint_hashes_checked": True,
        "exposure_schedule_checked": True,
        "scope": (
            "CPU labels/names/masks, independent projection/loss/RMSD, geometry, "
            "dense all-atom lDDT/smooth-lDDT, schedule, selection, hashes; GPU reload checked by worker"
        ),
    }
    write_json(root / "independent_validation.json", result)
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
