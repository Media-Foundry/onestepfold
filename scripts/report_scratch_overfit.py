#!/usr/bin/env python3
"""Report only independently accepted, exposure-matched scratch TRAIN4 results."""

import argparse
import csv
import json
from pathlib import Path

from fastglycan.paired_teacher_protocol import sha256, write_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root
    runs = {}
    for arm in ("baseline", "smooth_lddt"):
        folder = root / arm
        report = json.loads((folder / "report.json").read_text())
        qa = json.loads((folder / "independent_validation.json").read_text())
        contract = json.loads((folder / "contract.json").read_text())
        assert report["complete"] and qa["complete"]
        assert qa["report_sha256"] == sha256(folder / "report.json")
        assert report["contract_sha256"] == sha256(folder / "contract.json")
        assert contract["objective_arm"] == arm
        runs[arm] = {
            "report": report,
            "contract": contract,
            "qa_sha256": sha256(folder / "independent_validation.json"),
            "history": json.loads((folder / "history.json").read_text()),
        }
    a, b = (runs[key] for key in ("baseline", "smooth_lddt"))
    for field in (
        "indices", "examples", "initial_weights_sha256", "config", "optimizer",
        "training_seed_sha256", "evaluation_seeds", "source_manifest_sha256",
    ):
        assert a["contract"][field] == b["contract"][field], field
    for first, second in zip(a["report"]["initial"]["rows"], b["report"]["initial"]["rows"], strict=True):
        assert first["prediction_sha256"] == second["prediction_sha256"]
    lookup = {
        arm: {item["epoch"]: item for item in run["history"]}
        for arm, run in runs.items()
    }
    common = sorted(set(lookup["baseline"]).intersection(lookup["smooth_lddt"]))
    comparisons = []
    for epoch in common:
        row = {"exposures_per_protein": epoch, "updates": 4 * epoch}
        for arm in runs:
            item = lookup[arm][epoch]
            summary = item["summary"]
            row[arm + "_mean_lddt"] = summary["paired_protein_quality"]["mean"]
            row[arm + "_minimum_protein_noise_lddt"] = summary["minimum_protein_noise_lddt"]
            row[arm + "_rmsd"] = summary["worst_seed_pooled_atom_rmsd"]
            row[arm + "_joint_pass"] = summary["joint_capacity_pass"]
            row[arm + "_elapsed_seconds"] = item["elapsed_seconds"]
        row["mean_lddt_delta"] = row["smooth_lddt_mean_lddt"] - row["baseline_mean_lddt"]
        comparisons.append(row)
    result = {
        "complete": True,
        "scope": "TRAIN4 memorization and supervision efficiency; no generalization claim",
        "common_exposure_comparisons": comparisons,
        "runs": {
            arm: {
                "last_epoch": run["report"]["last_epoch"],
                "best_epoch": run["report"]["best_epoch"],
                "stop_reason": run["report"]["stop_reason"],
                "joint_pass": run["report"]["joint_capacity_pass"],
                "best_summary": run["report"]["best"]["summary"],
                "last_summary": run["report"]["last"]["summary"],
                "elapsed_seconds": run["report"]["elapsed_seconds"],
                "report_sha256": sha256(root / arm / "report.json"),
                "qa_sha256": run["qa_sha256"],
            }
            for arm, run in runs.items()
        },
        "automatically_launch_next_stage": False,
    }
    write_json(root / "comparison.json", result)
    with (root / "matched_exposure_curves.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(comparisons[0]))
        writer.writeheader()
        writer.writerows(comparisons)
    lines = [
        "# Scratch TRAIN4 监督对照", "",
        "两臂同随机初始化、输入、优化器、顺序和噪声；仅 smooth-lDDT 项不同。",
        "这只评估小集记忆能力，不评估泛化或最低 1% 尾部。", "",
        "| 臂 | 停止曝光/蛋白 | 停止原因 | 联合通过 | 作业内耗时秒 |",
        "| --- | ---: | --- | --- | ---: |",
    ]
    for arm, run in result["runs"].items():
        lines.append(f"| {arm} | {run['last_epoch']} | {run['stop_reason']} | {run['joint_pass']} | {run['elapsed_seconds']:.1f} |")
    lines += ["", "完整同曝光比较见 matched_exposure_curves.csv；提前停止后不外推。", "",
              "下一步先人工审阅逐目标曲线和化学指标，再决定是否进入 TRAIN32。"]
    (root / "comparison.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
