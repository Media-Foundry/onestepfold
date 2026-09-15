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


def _load_compact_labels(path: Path) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Load CA labels exported from the HPC GT shards for a local probe."""
    arrays = np.load(path, allow_pickle=False)
    group_ids = [str(value) for value in arrays["group_ids"]]
    lengths = np.asarray(arrays["lengths"], dtype=np.int64)
    positions = np.asarray(arrays["positions"], dtype=np.float32)
    masks = np.asarray(arrays["masks"], dtype=bool)
    if len(group_ids) != len(lengths) or sum(lengths) != len(positions):
        raise ValueError("compact contact labels have inconsistent lengths")
    result: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    offset = 0
    for group_id, length in zip(group_ids, lengths, strict=True):
        end = offset + int(length)
        result[group_id] = (positions[offset:end], masks[offset:end])
        offset = end
    return result


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
    labels_path: Path | None = None,
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

    compact_labels = _load_compact_labels(labels_path) if labels_path else {}
    samples: list[tuple[str, np.ndarray, np.ndarray, dict[str, Any]]] = []
    for group in groups:
        group_id = str(group["group_id"])
        label_arrays = compact_labels.get(group_id)
        if labels_path and label_arrays is None:
            continue
        pairs = _sample_pairs(
            *(label_arrays if label_arrays is not None else _read_npz(record_by_group[group_id])),
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
    # Load each shard once. Keeping the sampled pair features in memory avoids
    # rereading the same 1.3 GB all-layer shard once per layer.
    x_by_feature: dict[str, list[np.ndarray]] = {name: [] for name in feature_names}
    labels_by_feature: dict[str, list[np.ndarray]] = {name: [] for name in feature_names}
    group_by_feature: dict[str, list[np.ndarray]] = {name: [] for name in feature_names}
    open_shard: str | None = None
    tensors: dict[str, np.ndarray] = {}
    for group_id, pairs, labels, row in samples:
        if row["shard"] != open_shard:
            from safetensors.torch import load_file

            tensors = {
                name: value.float().numpy()
                for name, value in load_file(str(cache_root / row["shard"])).items()
            }
            open_shard = row["shard"]
        start = int(row["offset_start"])
        end = int(row["offset_end"])
        for feature_name in feature_names:
            hidden = tensors[feature_name][start:end]
            x_by_feature[feature_name].append(
                np.abs(hidden[pairs[:, 0]] - hidden[pairs[:, 1]])
            )
            labels_by_feature[feature_name].append(labels)
            group_by_feature[feature_name].append(
                np.full(labels.shape, group_id, dtype=object)
            )

    results: list[dict[str, Any]] = []
    for feature_name in feature_names:
        x = np.concatenate(x_by_feature[feature_name], axis=0)
        y = np.concatenate(labels_by_feature[feature_name], axis=0)
        group_ids = np.concatenate(group_by_feature[feature_name], axis=0)
        train_mask = np.asarray([group_id in train_groups for group_id in group_ids])
        results.append(
            {
                "feature": feature_name,
                "heldout_auroc": _fit_probe(x, y, train_mask),
                "pairs": int(y.size),
                "positive_fraction": float(y.mean()),
            }
        )

    def fit_combined(name: str, names: tuple[str, ...]) -> None:
        x = np.concatenate(
            [np.concatenate(x_by_feature[layer], axis=0) for layer in names], axis=1
        )
        y = np.concatenate(labels_by_feature[names[0]], axis=0)
        group_ids = np.concatenate(group_by_feature[names[0]], axis=0)
        train_mask = np.asarray([group_id in train_groups for group_id in group_ids])
        results.append(
            {
                "feature": name,
                "heldout_auroc": _fit_probe(x, y, train_mask),
                "pairs": int(y.size),
                "positive_fraction": float(y.mean()),
            }
        )

    fit_combined("layers_12_24_36_concat", ("layer_12", "layer_24", "layer_36"))

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
    parser.add_argument("--labels", type=Path, default=None)
    args = parser.parse_args()
    run_probe(
        args.cache_root,
        args.groups,
        args.train_manifest,
        args.output,
        args.limit,
        args.pairs_per_group,
        args.labels,
    )


if __name__ == "__main__":
    main()
