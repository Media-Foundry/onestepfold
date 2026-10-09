"""Complete per-parent geometry counts and predeclared worst-output summaries."""
import gzip
import json
from pathlib import Path


def summarize_stage_tails(root):
    assert json.loads((root / "verification.json").read_text())["scientific_experiment_complete"]
    result = {"descriptive_only": True, "runs": {}}
    for arm in ("final", "hint"):
        for seed in (272001, 272003):
            with gzip.open(root / f"n15/runs/{arm}/{seed}/scores_8208.json.gz", "rt") as f:
                score = json.load(f)
            names = {s["parent"]: s["pdb"] for s in score["sites"]}
            groups = {}
            for role in ("train", "dev_new_site", "dev_unseen_protein"):
                methods = {}
                for method in ("disabled", "exact", "oracle_pair", "correct", "mismatched"):
                    outputs = [x for x in score["outputs"] if x["role"] == role and x["arm"] == method]
                    parents = []
                    for parent in sorted({x["parent"] for x in outputs}):
                        rows = [x for x in outputs if x["parent"] == parent]
                        entry = {"parent": parent, "pdb": names[parent], "outputs": len(rows)}
                        for name, source in (
                            ("geometry_pass", "zero_severe_strict_checked_chirality"),
                            ("severe_pairs", "severe_pairs"), ("wrong_centres", "checked_chirality_wrong")
                        ):
                            entry[name] = sum(x["geometry"][source] for x in rows)
                        for name in ("disabled_pass_to_fail", "disabled_fail_to_pass", "exact_pass_to_fail", "exact_fail_to_pass"):
                            entry[name] = sum(x[name] for x in rows)
                        entry["local_over1"] = sum(x["fidelity"]["local_ca_rmsd_global_frame"] > 1 for x in rows)
                        entry["local_max"] = max(x["fidelity"]["local_ca_rmsd_global_frame"] for x in rows)
                        parents.append(entry)
                    for name in ("geometry_pass", "severe_pairs", "wrong_centres", "disabled_pass_to_fail", "disabled_fail_to_pass", "local_over1"):
                        assert sum(x[name] for x in parents) == score["summary"][role][method][name]
                    worst = sorted(outputs, key=lambda x: x["fidelity"]["local_ca_rmsd_global_frame"], reverse=True)[:3]
                    cases = [{"pdb": names[x["parent"]], "site": x["site_key"], "aa": x["aa"], "noise": x["noise"],
                              "local_rmsd": x["fidelity"]["local_ca_rmsd_global_frame"],
                              "geometry_pass": x["geometry"]["zero_severe_strict_checked_chirality"]} for x in worst]
                    methods[method] = {"parents": parents, "worst_local_outputs": cases}
                baseline = {r["parent"]: r for r in methods["disabled"]["parents"]}
                for row in methods["correct"]["parents"]:
                    row["net_pass_change"] = row["geometry_pass"] - baseline[row["parent"]]["geometry_pass"]
                    assert row["net_pass_change"] == row["disabled_fail_to_pass"] - row["disabled_pass_to_fail"]
                groups[role] = methods
            result["runs"][f"{arm}_{seed}"] = groups
    (root / "tail_decomposition.json").write_text(json.dumps(result, indent=2) + "\n")
    print("Verified per-parent geometry decomposition for four fixed endpoints")


if __name__ == "__main__":
    summarize_stage_tails(Path(__file__).resolve().parent)
