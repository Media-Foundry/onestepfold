#!/usr/bin/env python3
"""Paired bootstrap and hard-target stratification for Stage 0B outputs."""

from __future__ import annotations

import argparse
import gzip
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

SETTINGS = ("c1_s1", "c1_s2", "c1_s5", "c2_s1", "c2_s2", "c2_s5", "c4_s1", "c4_s2", "c4_s5")
METRICS = ("tm_score_ca", "all_atom_lddt", "ca_lddt", "backbone_rmsd_angstrom")


def _summary(values: list[float]) -> dict[str, float | None]:
    finite = np.asarray([value for value in values if math.isfinite(value)], dtype=np.float64)
    if finite.size == 0:
        return {"mean": None, "median": None, "p05": None, "p95": None}
    return {
        "mean": float(np.mean(finite)),
        "median": float(np.median(finite)),
        "p05": float(np.quantile(finite, 0.05)),
        "p95": float(np.quantile(finite, 0.95)),
    }


def _bootstrap(values: np.ndarray, rng: np.random.Generator, count: int) -> dict[str, Any]:
    if values.size == 0:
        return {"point": None, "bootstrap_ci95": [None, None]}
    indices = rng.integers(0, values.size, size=(count, values.size))
    means = values[indices].mean(axis=1)
    return {
        "point": float(values.mean()),
        "bootstrap_ci95": [float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))],
    }


def load_records(root: Path) -> dict[str, dict[str, dict[str, Any]]]:
    result = {}
    for setting in SETTINGS:
        path = root / f"{setting}.json"
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            result[setting] = {
                str(record["group_id"]): record
                for record in payload.get("records", [])
                if record.get("status") == "ok"
            }
    return result


def load_manifest(path: Path) -> dict[str, dict[str, Any]]:
    result = {}
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            result[str(row["group_id"])] = row
    return result


def load_groups(path: Path) -> dict[str, dict[str, Any]]:
    result = {}
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            result[str(row["group_id"])] = row
    return result


def analyze(eval_root: Path, manifest_path: Path, groups_path: Path, bootstrap_count: int, seed: int) -> dict[str, Any]:
    records = load_records(eval_root)
    anchor = records.get("c4_s5", {})
    rng = np.random.default_rng(seed)
    paired: dict[str, Any] = {}
    for setting, current in records.items():
        common = sorted(set(current) & set(anchor))
        setting_result: dict[str, Any] = {"common_count": len(common), "metrics": {}}
        for metric in METRICS:
            values = np.asarray(
                [float(current[group][metric]) - float(anchor[group][metric]) for group in common],
                dtype=np.float64,
            )
            metric_result = {
                **_summary(values.tolist()),
                "bootstrap_mean": _bootstrap(values, rng, bootstrap_count),
            }
            for threshold in (-0.01, -0.02, -0.05, -0.10):
                if metric in {"tm_score_ca", "all_atom_lddt", "ca_lddt"}:
                    metric_result[f"fraction_below_{abs(threshold):.2f}"] = float(np.mean(values < threshold))
            setting_result["metrics"][metric] = metric_result
        paired[setting] = setting_result

    metadata = load_manifest(manifest_path)
    groups = load_groups(groups_path)
    tail_ids = []
    for group_id, current in records.get("c1_s1", {}).items():
        if group_id in anchor and float(current["tm_score_ca"]) - float(anchor[group_id]["tm_score_ca"]) < -0.05:
            tail_ids.append(group_id)

    def group_features(group_id: str) -> dict[str, Any]:
        row = metadata[group_id]
        group = groups.get(group_id, {})
        stratum = row.get("stage0_stratum", {})
        return {
            "sequence_length": int(row.get("sequence_length", 0)),
            "resolution": row.get("resolution_high_angstrom"),
            "method": stratum.get("method", "unknown"),
            "length_bin": stratum.get("length", "unknown"),
            "apo_like": bool(stratum.get("apo_like", False)),
            "valid_member_count": int(group.get("valid_member_count", 1)),
            "near_pair_count": int(group.get("near_pair_count", 0)),
        }

    all_ids = sorted(set(records.get("c1_s1", {})) & set(anchor))
    tail_set = set(tail_ids)

    def stratum_summary(ids: list[str]) -> dict[str, Any]:
        features = [group_features(group_id) for group_id in ids]
        numeric = {}
        for name in ("sequence_length", "resolution", "valid_member_count", "near_pair_count"):
            numeric[name] = _summary([float(item[name]) for item in features if item[name] is not None])
        return {
            "count": len(features),
            "numeric": numeric,
            "method_counts": dict(sorted(Counter(item["method"] for item in features).items())),
            "length_bin_counts": dict(sorted(Counter(item["length_bin"] for item in features).items())),
            "apo_like_count": sum(item["apo_like"] for item in features),
            "multi_record_group_count": sum(item["valid_member_count"] > 1 for item in features),
        }

    return {
        "bootstrap_count": bootstrap_count,
        "seed": seed,
        "paired_vs_c4_s5": paired,
        "c1_s1_tail_definition": "TM-style delta versus c4_s5 < -0.05",
        "c1_s1_tail": stratum_summary(sorted(tail_set)),
        "c1_s1_non_tail": stratum_summary([group_id for group_id in all_ids if group_id not in tail_set]),
    }


def _fmt(value: float | None, digits: int = 4) -> str:
    return "NA" if value is None else f"{value:.{digits}f}"


def write_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Stage 0C Paired Analysis",
        "",
        "Paired deltas use the same 1,024 targets for each setting and the `c4_s5` output as anchor. Bootstrap intervals resample targets, not individual atoms.",
        "",
        "## Key Paired Risks",
        "",
        "| setting | metric | mean delta | bootstrap 95% CI | median delta | below -0.05 | below -0.10 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for setting in ("c1_s1", "c1_s5", "c2_s2", "c4_s1", "c4_s2"):
        for metric in ("tm_score_ca", "all_atom_lddt"):
            item = result["paired_vs_c4_s5"].get(setting, {}).get("metrics", {}).get(metric)
            if not item:
                continue
            ci = item["bootstrap_mean"]["bootstrap_ci95"]
            lines.append(
                f"| {setting} | {metric} | {_fmt(item['mean'])} | [{_fmt(ci[0])}, {_fmt(ci[1])}] | "
                f"{_fmt(item['median'])} | {_fmt(item.get('fraction_below_0.05'), 3)} | {_fmt(item.get('fraction_below_0.10'), 3)} |"
            )
    tail = result["c1_s1_tail"]
    non_tail = result["c1_s1_non_tail"]
    lines.extend([
        "",
        "## `c1_s1` Hard Tail",
        "",
        f"Definition: fixed-correspondence TM-style delta versus `c4_s5` < -0.05. The tail contains {tail['count']} targets; the comparison set contains {non_tail['count']}.",
        "",
        "| subset | median length | median resolution | multi-record groups | apo-like |",
        "| --- | ---: | ---: | ---: | ---: |",
        f"| tail | {_fmt(tail['numeric']['sequence_length']['median'], 1)} | {_fmt(tail['numeric']['resolution']['median'], 2)} | {tail['multi_record_group_count']} | {tail['apo_like_count']} |",
        f"| non-tail | {_fmt(non_tail['numeric']['sequence_length']['median'], 1)} | {_fmt(non_tail['numeric']['resolution']['median'], 2)} | {non_tail['multi_record_group_count']} | {non_tail['apo_like_count']} |",
        "",
        "This is a diagnostic on the temporal dev view; it is not used to tune or report the frozen temporal test.",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--groups", type=Path, required=True)
    parser.add_argument("--bootstrap-count", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=20260916)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-markdown", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.eval_root, args.manifest, args.groups, args.bootstrap_count, args.seed)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(args.output_markdown, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
