"""Rigidly aligned atom and internal-distance errors against a fixed teacher target."""
from __future__ import annotations

import math
import statistics

import torch

from onestepfold.data.teacher_pair_training import kabsch_align


def compare_coordinates(first, target, ca_mask):
    first, target = torch.as_tensor(first).float(), torch.as_tensor(target).float()
    ca_mask = torch.as_tensor(ca_mask, dtype=torch.bool)

    def rmsd(a, b):
        aligned = kabsch_align(b, a, torch.ones(len(a), dtype=torch.bool))
        return float((a - aligned).square().sum(-1).mean().sqrt())

    return {"all_heavy_atom_rmsd": rmsd(first, target),
            "ca_rmsd": rmsd(first[ca_mask], target[ca_mask]),
            "ca_pair_distance_rmse": float(
                (torch.pdist(first[ca_mask]) - torch.pdist(target[ca_mask]))
                .square().mean().sqrt())}


def summarize_coordinates(rows):
    metrics = ("all_heavy_atom_rmsd", "ca_rmsd", "ca_pair_distance_rmse")
    summary = {}
    for label in ("c1", "c2", "student"):
        result = {}
        for metric in metrics:
            values = [r["comparisons_to_c4"][label][metric] for r in rows]
            weights = [r["atom_count"] if metric == "all_heavy_atom_rmsd" else (
                r["length"] if metric == "ca_rmsd" else r["length"] * (r["length"] - 1) // 2)
                for r in rows]
            result["macro_" + metric] = statistics.mean(values)
            result["median_" + metric] = statistics.median(values)
            result["pooled_" + metric] = math.sqrt(
                sum(v * v * w for v, w in zip(values, weights, strict=True)) / sum(weights))
            for baseline in ("c1", "c2"):
                result[f"{metric}_worse_than_{baseline}_count"] = sum(
                    r["comparisons_to_c4"][label][metric]
                    > r["comparisons_to_c4"][baseline][metric] + 1e-6 for r in rows)
        summary[label] = result
    for baseline in ("c1", "c2"):
        summary[f"student_to_{baseline}_pooled_ratios"] = {
            metric: summary["student"]["pooled_" + metric] / summary[baseline]["pooled_" + metric]
            for metric in metrics}
    required = ("all_heavy_atom_rmsd", "ca_pair_distance_rmse")
    summary["exploratory_learning_signal"] = all(
        summary["student_to_c1_pooled_ratios"][key] <= 0.95 for key in required)
    summary["parity_with_c2"] = all(
        summary["student_to_c2_pooled_ratios"][key] <= 1 for key in required)
    return summary
