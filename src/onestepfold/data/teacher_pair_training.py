"""Training inputs for the c2-to-c4 coordinate-refiner baseline.

This module joins the frozen teacher-pair manifest to the frozen ESMC cache.
ESMC tensors are sliced lazily from their safetensors shards. The c4 target is
rigidly aligned into the c2 coordinate frame before a residual is learned;
missing atoms remain represented by explicit masks and are never imputed.
"""

from __future__ import annotations

import gzip
import json
import math
import random
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
from safetensors import safe_open
from torch import Tensor
from torch.utils.data import Sampler

from .esmc_cache import sequence_sha256
from .teacher_pairs import TeacherPairDataError, TeacherPairRecord, load_teacher_pair


@dataclass(frozen=True)
class ESMCCacheRecord:
    group_id: str
    sequence_sha256: str
    sequence_length: int
    shard: str
    offset_start: int
    offset_end: int
    feature_names: tuple[str, ...]

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> ESMCCacheRecord:
        record = cls(
            group_id=str(row["group_id"]),
            sequence_sha256=str(row["sequence_sha256"]),
            sequence_length=int(row["sequence_length"]),
            shard=str(row["shard"]),
            offset_start=int(row["offset_start"]),
            offset_end=int(row["offset_end"]),
            feature_names=tuple(str(name) for name in row["feature_names"]),
        )
        if record.offset_start < 0 or record.offset_end <= record.offset_start:
            raise TeacherPairDataError(f"invalid ESMC offsets for {record.group_id}")
        if record.offset_end - record.offset_start != record.sequence_length:
            raise TeacherPairDataError(f"ESMC length/offset mismatch for {record.group_id}")
        path = Path(record.shard)
        if path.is_absolute() or ".." in path.parts:
            raise TeacherPairDataError(f"unsafe ESMC shard path {record.shard!r}")
        return record


class ESMCShardStore:
    """Index and lazily slice residue features from frozen safetensors shards."""

    def __init__(
        self,
        root: Path,
        *,
        manifest_path: Path | None = None,
        feature_name: str = "final",
    ) -> None:
        self.root = Path(root)
        self.manifest_path = manifest_path or self.root / "manifest.jsonl.gz"
        self.feature_name = feature_name
        self.feature_spec = json.loads((self.root / "feature_spec.json").read_text())
        if self.feature_spec.get("feature_variant") != feature_name:
            raise TeacherPairDataError(
                f"feature spec is {self.feature_spec.get('feature_variant')!r}, "
                f"not {feature_name!r}"
            )
        records: dict[str, ESMCCacheRecord] = {}
        with gzip.open(self.manifest_path, "rt", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                record = ESMCCacheRecord.from_dict(json.loads(line))
                if record.group_id in records:
                    raise TeacherPairDataError(
                        f"duplicate ESMC group {record.group_id} at row {line_number}"
                    )
                records[record.group_id] = record
        if not records:
            raise TeacherPairDataError(f"empty ESMC manifest {self.manifest_path}")
        self.records = records

    def __len__(self) -> int:
        return len(self.records)

    def load(
        self,
        group_id: str,
        *,
        sequence: str | None = None,
        expected_length: int | None = None,
    ) -> Tensor:
        try:
            record = self.records[group_id]
        except KeyError as exc:
            raise TeacherPairDataError(f"group {group_id} is absent from the ESMC cache") from exc
        if sequence is not None and sequence_sha256(sequence) != record.sequence_sha256:
            raise TeacherPairDataError(f"ESMC sequence hash mismatch for {group_id}")
        if expected_length is not None and expected_length != record.sequence_length:
            raise TeacherPairDataError(f"ESMC sequence length mismatch for {group_id}")
        if self.feature_name not in record.feature_names:
            raise TeacherPairDataError(
                f"ESMC feature {self.feature_name!r} is absent for {group_id}"
            )
        shard_path = self.root / record.shard
        if not shard_path.is_file():
            raise TeacherPairDataError(f"missing ESMC shard {shard_path}")
        with safe_open(shard_path, framework="pt", device="cpu") as handle:
            if self.feature_name not in handle.keys():
                raise TeacherPairDataError(
                    f"shard {shard_path} lacks tensor {self.feature_name!r}"
                )
            shard_slice = handle.get_slice(self.feature_name)
            shape = tuple(shard_slice.get_shape())
            if len(shape) != 2 or record.offset_end > shape[0]:
                raise TeacherPairDataError(
                    f"invalid tensor shape {shape} for offsets in {shard_path}"
                )
            tensor = shard_slice[record.offset_start : record.offset_end].clone()
        hidden_dim = int(self.feature_spec["hidden_dim"])
        if tuple(tensor.shape) != (record.sequence_length, hidden_dim):
            raise TeacherPairDataError(
                f"ESMC tensor shape {tuple(tensor.shape)} does not match "
                f"{(record.sequence_length, hidden_dim)} for {group_id}"
            )
        if not tensor.is_floating_point() or not bool(torch.isfinite(tensor.float()).all()):
            raise TeacherPairDataError(f"invalid ESMC values for {group_id}")
        return tensor


def kabsch_align(mobile: Tensor, reference: Tensor, mask: Tensor) -> Tensor:
    """Rigidly align ``mobile`` onto ``reference`` using masked row vectors."""
    if mobile.ndim != 2 or mobile.shape[-1] != 3 or reference.shape != mobile.shape:
        raise ValueError("mobile and reference must both have shape [L,3]")
    if mask.shape != mobile.shape[:1]:
        raise ValueError("mask must have shape [L]")
    valid = mask.bool()
    if int(valid.sum()) < 3:
        raise TeacherPairDataError("Kabsch alignment requires at least three valid residues")
    if not bool(torch.isfinite(mobile[valid]).all() and torch.isfinite(reference[valid]).all()):
        raise TeacherPairDataError("Kabsch inputs contain non-finite valid coordinates")
    output_dtype = mobile.dtype
    mobile64 = mobile.to(torch.float64)
    reference64 = reference.to(torch.float64)
    mobile_center = mobile64[valid].mean(dim=0)
    reference_center = reference64[valid].mean(dim=0)
    centered_mobile = mobile64[valid] - mobile_center
    centered_reference = reference64[valid] - reference_center
    covariance = centered_mobile.transpose(0, 1) @ centered_reference
    left, _, right_t = torch.linalg.svd(covariance)
    correction = torch.eye(3, dtype=torch.float64, device=mobile.device)
    correction[-1, -1] = torch.sign(torch.linalg.det(left @ right_t))
    rotation = left @ correction @ right_t
    aligned = (mobile64 - mobile_center) @ rotation + reference_center
    aligned = torch.where(valid[:, None], aligned, torch.zeros_like(aligned))
    return aligned.to(output_dtype)


@dataclass(frozen=True)
class TeacherPairTrainingExample:
    group_id: str
    split: str
    sequence_length: int
    residue_features: Tensor
    backbone_positions: Tensor
    target_ca: Tensor
    residue_mask: Tensor
    baseline_ca_rmsd: float


class CoordinateRefinerDataset(Sequence[TeacherPairTrainingExample]):
    """Lazy join of teacher coordinates and frozen ESMC residue features."""

    def __init__(
        self,
        records: Sequence[TeacherPairRecord],
        output_root: Path,
        esmc_store: ESMCShardStore,
    ) -> None:
        self.records = tuple(records)
        self.output_root = Path(output_root)
        self.esmc_store = esmc_store

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int) -> TeacherPairTrainingExample:
        record = self.records[index]
        pair = load_teacher_pair(record, self.output_root)
        features = self.esmc_store.load(
            record.group_id,
            sequence=record.sequence,
            expected_length=record.sequence_length,
        )
        c2_backbone = torch.from_numpy(pair.c2.backbone_positions).clone()
        c4_backbone = torch.from_numpy(pair.c4.backbone_positions).clone()
        c2_mask = torch.from_numpy(pair.c2.backbone_mask).bool()
        c4_mask = torch.from_numpy(pair.c4.backbone_mask).bool()
        residue_mask = c2_mask[:, :3].all(dim=-1) & c4_mask[:, 1]
        c2_ca = c2_backbone[:, 1]
        aligned_c4_ca = kabsch_align(c4_backbone[:, 1], c2_ca, residue_mask)
        squared_distance = (aligned_c4_ca[residue_mask] - c2_ca[residue_mask]).square().sum(-1)
        baseline_ca_rmsd = float(torch.sqrt(squared_distance.mean()).item())
        if not math.isfinite(baseline_ca_rmsd):
            raise TeacherPairDataError(f"non-finite baseline RMSD for {record.group_id}")
        return TeacherPairTrainingExample(
            group_id=record.group_id,
            split=record.split,
            sequence_length=record.sequence_length,
            residue_features=features,
            backbone_positions=c2_backbone,
            target_ca=aligned_c4_ca,
            residue_mask=residue_mask,
            baseline_ca_rmsd=baseline_ca_rmsd,
        )


class LengthAwareCollator:
    """Sort by length and pad a batch to a configurable length multiple."""

    def __init__(self, pad_to_multiple: int = 8) -> None:
        if pad_to_multiple < 1:
            raise ValueError("pad_to_multiple must be positive")
        self.pad_to_multiple = pad_to_multiple

    def __call__(self, examples: Sequence[TeacherPairTrainingExample]) -> dict[str, Any]:
        if not examples:
            raise ValueError("cannot collate an empty batch")
        ordered = sorted(examples, key=lambda example: (-example.sequence_length, example.group_id))
        batch_size = len(ordered)
        max_length = max(example.sequence_length for example in ordered)
        padded_length = (
            (max_length + self.pad_to_multiple - 1) // self.pad_to_multiple
        ) * self.pad_to_multiple
        hidden_dim = int(ordered[0].residue_features.shape[-1])
        feature_dtype = ordered[0].residue_features.dtype
        features = torch.zeros(batch_size, padded_length, hidden_dim, dtype=feature_dtype)
        backbone = torch.zeros(batch_size, padded_length, 4, 3, dtype=torch.float32)
        target_ca = torch.zeros(batch_size, padded_length, 3, dtype=torch.float32)
        residue_mask = torch.zeros(batch_size, padded_length, dtype=torch.bool)
        for batch_index, example in enumerate(ordered):
            length = example.sequence_length
            if tuple(example.residue_features.shape) != (length, hidden_dim):
                raise TeacherPairDataError(f"feature shape mismatch for {example.group_id}")
            if example.backbone_positions.shape != (length, 4, 3):
                raise TeacherPairDataError(f"backbone shape mismatch for {example.group_id}")
            features[batch_index, :length] = example.residue_features
            backbone[batch_index, :length] = example.backbone_positions
            target_ca[batch_index, :length] = example.target_ca
            residue_mask[batch_index, :length] = example.residue_mask
        return {
            "group_ids": [example.group_id for example in ordered],
            "splits": [example.split for example in ordered],
            "lengths": torch.tensor(
                [example.sequence_length for example in ordered], dtype=torch.long
            ),
            "residue_features": features,
            "backbone_positions": backbone,
            "target_ca": target_ca,
            "residue_mask": residue_mask,
            "baseline_ca_rmsd": torch.tensor(
                [example.baseline_ca_rmsd for example in ordered], dtype=torch.float32
            ),
        }


class LengthBucketBatchSampler(Sampler[list[int]]):
    """Deterministic length buckets that reduce padding while retaining shuffle."""

    def __init__(
        self,
        lengths: Sequence[int],
        batch_size: int,
        *,
        bucket_size_multiplier: int = 16,
        shuffle: bool = True,
        seed: int = 101,
        drop_last: bool = False,
    ) -> None:
        if batch_size < 1 or bucket_size_multiplier < 1:
            raise ValueError("batch_size and bucket_size_multiplier must be positive")
        self.lengths = tuple(int(length) for length in lengths)
        if any(length < 1 for length in self.lengths):
            raise ValueError("all sequence lengths must be positive")
        self.batch_size = batch_size
        self.bucket_size = batch_size * bucket_size_multiplier
        self.shuffle = shuffle
        self.seed = seed
        self.drop_last = drop_last
        self.epoch = 0

    def set_epoch(self, epoch: int) -> None:
        self.epoch = int(epoch)

    def __len__(self) -> int:
        if self.drop_last:
            return len(self.lengths) // self.batch_size
        return math.ceil(len(self.lengths) / self.batch_size)

    def __iter__(self) -> Iterator[list[int]]:
        ordered = sorted(range(len(self.lengths)), key=lambda index: (self.lengths[index], index))
        rng = random.Random(self.seed + self.epoch)
        batches: list[list[int]] = []
        for start in range(0, len(ordered), self.bucket_size):
            bucket = ordered[start : start + self.bucket_size]
            if self.shuffle:
                rng.shuffle(bucket)
            for batch_start in range(0, len(bucket), self.batch_size):
                batch = bucket[batch_start : batch_start + self.batch_size]
                if len(batch) == self.batch_size or not self.drop_last:
                    batches.append(batch)
        if self.shuffle:
            rng.shuffle(batches)
        yield from batches


__all__ = [
    "CoordinateRefinerDataset",
    "ESMCCacheRecord",
    "ESMCShardStore",
    "LengthAwareCollator",
    "LengthBucketBatchSampler",
    "TeacherPairTrainingExample",
    "kabsch_align",
]
