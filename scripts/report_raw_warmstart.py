#!/usr/bin/env python3
"""Matched finite-budget warm-start report after complete independent acceptance."""

import argparse
import json
from pathlib import Path

import numpy as np

from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.raw_warmstart import verify_lock
from report_endpoint_objective import METRICS, comparison, summaries, vectors


def geometry(rows):
    chirality = [r["geometry"]["ca_chirality"] for r in rows]
    chirality = [r for r in chirality if r["evaluable_count"]]
    return {
        "chirality_macro": float(np.mean([r["agreement_count"] / r["evaluable_count"] for r in chirality])) if chirality else None,
        "chirality_evaluable_rows": len(chirality),
        "distance_mae": {name: float(np.mean([r["geometry"]["local_distances"][name]["mae"] for r in rows if r["geometry"]["local_distances"][name]["mae"] is not None])) for name in ("N_CA", "CA_C", "C_O", "consecutive_C_N")},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    root = parser.parse_args().root.resolve()
    lock = verify_lock(root, root / "code_v1")
    reports, contracts, history, inputs = {}, {}, {}, {}
    for label in ("raw_continue", "geometry_adapt"):
        folder = root / label
        loaded = {}
        for name in ("report.json", "contract.json", "history.json", "independent_validation_precision_v2.json", "initial_replay_acceptance.json"):
            inputs[str(folder / name)] = sha256(folder / name)
            loaded[name] = json.loads((folder / name).read_text())
        report, qa, c = loaded["report.json"], loaded["independent_validation_precision_v2.json"], loaded["contract.json"]
        assert report["complete"] and qa["complete"] and qa["gpu32_replay_exact"]
        assert qa["report_sha256"] == inputs[str(folder / "report.json")]
        assert report["parent_checkpoint_sha256"] == lock["checkpoint_sha256"]
        assert report["history_sha256"] == inputs[str(folder / "history.json")]
        assert loaded["initial_replay_acceptance.json"]["complete"]
        reports[label], contracts[label] = report, c
        history[label] = {h["step"]: h for h in loaded["history.json"]}
    for key in ("parent_checkpoint_sha256", "parent_step", "initial_weights_sha256", "config", "optimizer", "optimizer_reset", "max_steps", "soft_seconds", "train", "validation", "train_probe", "evaluation_seeds", "gpu_model", "matmul_tf32", "cudnn_tf32"):
        assert contracts["raw_continue"][key] == contracts["geometry_adapt"][key], key
    assert contracts["raw_continue"]["arm"] == "raw" and contracts["geometry_adapt"]["arm"] == "control"
    groups = sorted(r["group_id"] for r in contracts["raw_continue"]["validation"])
    common = sorted(set(history["raw_continue"]) & set(history["geometry_adapt"]))
    comparisons = {}
    for step in common:
        comparisons[str(step)] = {metric: comparison(vectors(history["geometry_adapt"][step]["validation"]["rows"], metric, groups), vectors(history["raw_continue"][step]["validation"]["rows"], metric, groups)) for metric in METRICS}
    status = "budget_not_reached"
    if "8192" in comparisons:
        passed = all(comparisons["8192"][m][s]["ci95"][0] > 0 for m in METRICS for s in ("mean", "worst5_mean"))
        status = "development_joint_quality_gate_passed_requires_confirmation" if passed else "joint_quality_gate_not_passed"
    result = {"complete": True, "primary_status": status, "primary_step": 8192, "lock_sha256": sha256(root / "lock.json"), "inputs_sha256": inputs, "analysis_source_sha256": sha256(Path(__file__)), "groups": groups, "common_update_comparisons": comparisons, "arms": {}, "scope": "Single-seed exploratory warm-start adaptation; same data and parent, no frozen test, chemistry separate"}
    lines = ["# Raw父权重的几何适配：匹配预算结果", "", "主终点：" + status, "", "两arm均从raw2048第22528步best权重开始，新建相同AdamW，sampler从epoch12接续。唯一方法变化为是否经过既有几何构建器。", "", "|新增更新|Δmean lDDT [95% CI]|Δmean TM [95% CI]|", "|---:|---|---|"]
    for step in common:
        items = []
        for metric in METRICS:
            value = comparisons[str(step)][metric]["mean"]
            items.append(f"{value['delta']:+.5f} [{value['ci95'][0]:+.5f}, {value['ci95'][1]:+.5f}]")
        lines.append(f"|{step}|" + "|".join(items) + "|")
    if "8192" in comparisons:
        lines += ["", "|8192步指标|Δworst5% mean [95% CI]|下降>0.05目标数|", "|---|---|---:|"]
        for metric in METRICS:
            value = comparisons["8192"][metric]; tail = value["worst5_mean"]
            lines.append(f"|{metric}|{tail['delta']:+.5f} [{tail['ci95'][0]:+.5f}, {tail['ci95'][1]:+.5f}]|{value['loss_gt_005_count']}/128|")
    lines += ["", "|arm|view|step|mean lDDT|mean TM|C–N MAE Å|chirality|", "|---|---|---:|---:|---:|---:|---:|"]
    for label, report in reports.items():
        arm = {"steps": report["steps"], "best_step": report["best_step"], "samples_seen": report["samples_seen"], "training_gpu_hours": report["training_seconds"] / 3600, "worker_seconds": report["elapsed_seconds"], "views": {}}
        for view in ("initial_validation", "last_validation", "best_validation", "best_full_train"):
            rows = report[view]["rows"]; ids = sorted({r["group_id"] for r in rows})
            values = {metric: {k: float(v) for k, v in summaries(vectors(rows, metric, ids)).items()} for metric in METRICS}
            values.update(geometry=geometry(rows), step=report[view]["step"])
            arm["views"][view] = values
            lines.append(f"|{label}|{view}|{values['step']}|{values[METRICS[0]]['mean']:.5f}|{values[METRICS[1]]['mean']:.5f}|{values['geometry']['distance_mae']['consecutive_C_N']:.5f}|{values['geometry']['chirality_macro']:.5f}|")
        arm["within_arm_last_minus_initial"] = {metric: comparison(vectors(report["last_validation"]["rows"], metric, groups), vectors(report["initial_validation"]["rows"], metric, groups)) for metric in METRICS}
        result["arms"][label] = arm
    parent = json.loads((Path(lock["parent_root"]) / "report.json").read_text())
    result["parent_cost"] = {"worker_seconds": parent["elapsed_seconds"], "training_seconds": parent["training_seconds"], "total_updates": parent["steps"], "chosen_step": parent["best_step"]}
    lines += ["", "8192新增更新仅4轮曝光，不是收敛证明。父训练成本另列于JSON；新增worker总时长包含初始/最终评估。",
              "每目标平均两个预定K1噪声，不best-of-K；配对bootstrap5000次seed20260926，非独立训练重复，未作多重检验校正。",
              "初始geometry输出质量可以低于raw；raw坐标起点必须相同。最佳checkpoint单列，不替换8192主终点。",
              "质量联合门槛、化学几何、独立泛化确认分别判断，不能通过修改门槛宣布成功。", "", "```json", json.dumps({label: {k: v for k, v in arm.items() if k not in ("views", "within_arm_last_minus_initial")} for label, arm in result["arms"].items()}, indent=2), "```"]
    write_json(root / "comparison.json", result)
    (root / "report.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"complete": True, "primary_status": status}), flush=True)


if __name__ == "__main__":
    main()
