#!/usr/bin/env python3
"""Run a small group-held-out contact probe over an all-layer ESMC cache."""

from __future__ import annotations

import argparse
import gzip
import io
import json
import tarfile
from pathlib import Path
from typing import Any

import numpy as np


def _read_jsonl_gz(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _read_npz(record: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    with tarfile.open(record["shard"], "r") as archive:
        member = archive.extractfile(record["npz"])
        if member is None:
            raise FileNotFoundError(f"missing GT member {record['npz']}")
        arrays = np.load(io.BytesIO(member.read()))
        positions = np.asarray(arrays["atom37_positions"], dtype=np.float32)
        mask = np.asarray(arrays["atom37_mask"], dtype=bool)
    # atom37_heavy_v1 fixes CA at vocabulary index 1.
    return positions[:, 1, :], mask[:, 1]


def _sample_pairs(
    positions: np.ndarray,
    mask: np.ndarray,
    max_pairs: int,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray] | None:
    valid = np.flatnonzero(mask)
    if valid.size < 6:
        return None
    delta = positions[valid, None, :] - positions[None, valid, :]
    distances = np.sqrt(np.sum(delta * delta, axis=-1))
    upper_i, upper_j = np.triu_indices(valid.size, k=1)
    separated = (valid[upper_j] - valid[upper_i]) >= 3
    upper_i, upper_j = upper_i[separated], upper_j[separated]
    labels = distances[upper_i, upper_j] < 8.0
    positive = np.flatnonzero(labels)
    negative = np.flatnonzero(~labels)
    if positive.size == 0 or negative.size == 0:
        return None
    half = max(1, max_pairs // 2)
    pos = rng.choice(positive, size=min(half, positive.size), replace=False)
    neg = rng.choice(negative, size=min(half, negative.size), replace=False)
    selected = np.concatenate([pos, neg])
    rng.shuffle(selected)
    return (
        np.stack([valid[upper_i[selected]], valid[upper_j[selected]]], axis=1),
        labels[selected].astype(np.int8),
    )


def _load_cache_rows(cache_root: Path) -> dict[str, dict[str, Any]]:
    rows = _read_jsonl_gz(cache_root / "manifest.jsonl.gz")
    return {str(row["group_id"]): row for row in rows}


def _fit_probe(x: np.ndarray, y: np.ndarray, train_mask: np.ndarray) -> float:
    try:
        from sklearn.linear_model import SGDClassifier
        from sklearn.metrics import roc_auc_score
    except ImportError as exc:  # pragma: no cover - HPC-only optional dependency
        raise RuntimeError("scikit-learn is required for the ESMC contact probe") from exc
    model = SGDClassifier(
        loss="log_loss", class_weight="balanced", max_iter=8, tol=1e-3, random_state=101
    )
    model.fit(x[train_mask], y[train_mask])
    heldout = ~train_mask
    if np.unique(y[heldout]).size < 2:
        raise ValueError("held-out contact labels contain one class; increase --limit")
    return float(roc_auc_score(y[heldout], model.predict_proba(x[heldout])[:, 1]))


def run_probe(
    cache_root: Path,
    groups_path: Path,
    train_manifest: Path,
    output_path: Path,
    limit: int = 500,
    pairs_per_group: int = 128,
) -> dict[str, Any]:
    cache_rows = _load_cache_rows(cache_root)
    train_records = _read_jsonl_gz(train_manifest)
    record_by_group: dict[str, dict[str, Any]] = {}
    for record in train_records:
        record_by_group.setdefault(str(record["group_id"]), record)
    groups = [
        row
        for row in _read_jsonl_gz(groups_path)
        if str(row["group_id"]) in cache_rows and str(row["group_id"]) in record_by_group
    ]
    groups.sort(key=lambda row: str(row["group_id"]))
    groups = groups[:limit]
    if len(groups) < 20:
        raise ValueError("contact probe needs at least 20 train-seen groups")
    train_group_count = max(1, int(round(len(groups) * 0.8)))
    train_groups = {str(row["group_id"]) for row in groups[:train_group_count]}

    samples: list[tuple[str, np.ndarray, np.ndarray, dict[str, Any]]] = []
    for group in groups:
        group_id = str(group["group_id"])
        pairs = _sample_pairs(
            *_read_npz(record_by_group[group_id]),
            pairs_per_group,
            np.random.default_rng(int(group_id[:16], 16)),
        )
        if pairs is not None:
            samples.append((group_id, pairs[0], pairs[1], cache_rows[group_id]))
    if len(samples) < 20:
        raise ValueError("too few groups with valid contact pairs")

    feature_names = sorted(
        name
        for name in samples[0][3]["feature_names"]
        if name.startswith("layer_")
    )
    results: list[dict[str, Any]] = []
    for feature_name in feature_names:
        x_parts: list[np.ndarray] = []
        y_parts: list[np.ndarray] = []
        group_parts: list[np.ndarray] = []
        open_shard: str | None = None
        tensors: dict[str, Any] = {}
        for group_id, pairs, labels, row in samples:
            if row["shard"] != open_shard:
                from safetensors.numpy import load_file

                tensors = load_file(str(cache_root / row["shard"]))
                open_shard = row["shard"]
            hidden = np.asarray(tensors[feature_name], dtype=np.float32)
            start = int(row["offset_start"])
            h = hidden[start : int(row["offset_end"])]
            pair_features = np.abs(h[pairs[:, 0]] - h[pairs[:, 1]])
            x_parts.append(pair_features)
            y_parts.append(labels)
            group_parts.append(np.full(labels.shape, group_id, dtype=object))
        x = np.concatenate(x_parts, axis=0)
        y = np.concatenate(y_parts, axis=0)
        group_ids = np.concatenate(group_parts, axis=0)
        train_mask = np.asarray([group_id in train_groups for group_id in group_ids])
        results.append(
            {
                "feature": feature_name,
                "heldout_auroc": _fit_probe(x, y, train_mask),
                "pairs": int(y.size),
                "positive_fraction": float(y.mean()),
            }
        )

    output = {
        "cache": str(cache_root),
        "groups_requested": len(groups),
        "groups_with_pairs": len(samples),
        "train_group_count": len(train_groups),
        "pairs_per_group": pairs_per_group,
        "contact_definition": "CA distance < 8 A; sequence separation >= 3",
        "feature_results": results,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2, sort_keys=True))
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-root", type=Path, required=True)
    parser.add_argument("--groups", type=Path, required=True)
    parser.add_argument("--train-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--pairs-per-group", type=int, default=128)
    args = parser.parse_args()
    run_probe(
        args.cache_root,
        args.groups,
        args.train_manifest,
        args.output,
        args.limit,
        args.pairs_per_group,
    )


if __name__ == "__main__":
    main()
