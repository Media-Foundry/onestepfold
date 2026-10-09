"""Reconstruct frozen-checkpoint TRAIN losses from full-field saved moments.

This is descriptive analysis of the already fixed objectives, not a new weight
search. Optimizer-history losses and endpoint losses are kept separate.
"""
import argparse
import json
from pathlib import Path

import numpy as np


def diagnose_stage_objective(root, cohorts=("n1", "n15")):
    build = json.loads((root / "build_lock.json").read_text())
    stats = {r["site"]: r for r in build["train_residual_stats"]}
    result = {"descriptive_only": True, "changes_training_weights": False, "runs": {}}
    for cohort in cohorts:
        cfg = json.loads((root / cohort / "training_lock.json").read_text())
        for arm in ("final", "hint"):
            for seed in (272001, 272003):
                nodes = []
                folder = root / cohort / "runs" / arm / str(seed)
                for step in cfg["checkpoints"]:
                    ev = json.loads((folder / f"evaluation_{step}.json").read_text())
                    sites = []
                    for row in ev["latent"]:
                        if row["site"] not in cfg["train_sites"]:
                            continue
                        recorded = stats[row["site"]]
                        elements = recorded["length"] ** 2 * 128
                        q = cfg["site_scale_squared"][row["site"]]
                        moments = row["moments"]
                        assert np.isclose(
                            moments["raw"]["target_energy"] / elements,
                            recorded["mean_squared_residual"], rtol=1e-8,
                        )
                        values = {
                            "site": row["site"], "parent": row["parent"],
                            "q": q, "length": recorded["length"],
                        }
                        for mode in ("raw", "common", "centered"):
                            values[mode + "_nmse"] = moments[mode]["nmse"]
                            values[mode + "_weighted_mse"] = moments[mode]["error_energy"] / elements / q
                        values["hint_weighted_mse"] = row["hint_moments"]["raw"]["error_energy"] / elements / q
                        values["declared_objective"] = values["raw_weighted_mse"] if arm == "final" else (
                            values["raw_weighted_mse"] + values["hint_weighted_mse"]
                        ) / 2
                        sites.append(values)
                    assert len(sites) == len(cfg["train_sites"])
                    parents = sorted({r["parent"] for r in sites})
                    parent_mean = lambda key: float(np.mean([
                        np.mean([r[key] for r in sites if r["parent"] == parent]) for parent in parents
                    ]))
                    nodes.append({
                        "step": step, "sites": sites,
                        "site_mean_declared_objective": float(np.mean([r["declared_objective"] for r in sites])),
                        "site_mean_final_weighted_mse": float(np.mean([r["raw_weighted_mse"] for r in sites])),
                        "parent_mean_raw_nmse": parent_mean("raw_nmse"),
                        "parent_mean_centered_nmse": parent_mean("centered_nmse"),
                        "raw_nmse_over_one_sites": sum(r["raw_nmse"] > 1 for r in sites),
                        "centered_nmse_over_one_sites": sum(r["centered_nmse"] > 1 for r in sites),
                    })
                result["runs"][f"{cohort}_{arm}_{seed}"] = nodes
    if len(cohorts) == 2:
        matched = {}
        for arm in ("final", "hint"):
            for seed in (272001, 272003):
                rows = {}
                for cohort, step in (("n1", 304), ("n15", 8208)):
                    node = next(r for r in result["runs"][f"{cohort}_{arm}_{seed}"] if r["step"] == step)
                    rows[cohort] = next(r for r in node["sites"] if r["site"] == "p3_s37")
                matched[f"{arm}_{seed}"] = rows
        result["t37_equal_32_exposures"] = matched
    name = "objective_diagnostic.json" if len(cohorts) == 2 else "objective_diagnostic_n1.json"
    (root / name).write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print("Reconstructed fixed objectives for", len(result["runs"]), "runs")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n1-only", action="store_true")
    args = parser.parse_args()
    diagnose_stage_objective(Path(__file__).resolve().parent, ("n1",) if args.n1_only else ("n1", "n15"))
