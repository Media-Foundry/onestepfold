import gzip
import json
from pathlib import Path

import torch
from safetensors.torch import save_file

from onestepfold.data.esmc_cache import sequence_sha256
from onestepfold.data.teacher_pair_training import (
    ESMCShardStore,
    LengthAwareCollator,
    LengthBucketBatchSampler,
    TeacherPairTrainingExample,
    kabsch_align,
)


def _write_esmc_cache(root: Path) -> None:
    root.mkdir()
    (root / "feature_spec.json").write_text(
        json.dumps(
            {
                "model_id": "test",
                "hf_revision": "1" * 40,
                "code_revision": "2" * 40,
                "feature_variant": "final",
                "hidden_dim": 4,
                "num_layers": 1,
                "dtype": "bfloat16",
                "bos_removed": True,
                "eos_removed": True,
            }
        )
    )
    tensor = torch.arange(20, dtype=torch.float32).reshape(5, 4).to(torch.bfloat16)
    save_file({"final": tensor}, root / "shard-00000.safetensors")
    rows = [
        {
            "group_id": "g1",
            "sequence_sha256": sequence_sha256("AC"),
            "sequence_length": 2,
            "shard": "shard-00000.safetensors",
            "offset_start": 0,
            "offset_end": 2,
            "feature_names": ["final"],
        },
        {
            "group_id": "g2",
            "sequence_sha256": sequence_sha256("DEF"),
            "sequence_length": 3,
            "shard": "shard-00000.safetensors",
            "offset_start": 2,
            "offset_end": 5,
            "feature_names": ["final"],
        },
    ]
    with (root / "manifest.jsonl.gz").open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed:
            for row in rows:
                compressed.write((json.dumps(row) + "\n").encode())


def test_esmc_shard_store_slices_only_requested_group(tmp_path: Path):
    root = tmp_path / "cache"
    _write_esmc_cache(root)
    store = ESMCShardStore(root)
    tensor = store.load("g2", sequence="DEF", expected_length=3)
    expected = torch.arange(20, dtype=torch.float32).reshape(5, 4)[2:].to(torch.bfloat16)
    assert tensor.dtype == torch.bfloat16
    assert torch.equal(tensor, expected)


def test_kabsch_align_removes_only_rigid_transform():
    torch.manual_seed(11)
    reference = torch.randn(12, 3)
    rotation, _ = torch.linalg.qr(torch.randn(3, 3))
    if torch.linalg.det(rotation) < 0:
        rotation[:, 0] *= -1
    mobile = reference @ rotation + torch.tensor([4.0, -2.0, 1.5])
    mask = torch.ones(12, dtype=torch.bool)
    aligned = kabsch_align(mobile, reference, mask)
    assert torch.allclose(aligned, reference, atol=1e-5)


def _example(group_id: str, length: int, value: float) -> TeacherPairTrainingExample:
    backbone = torch.zeros(length, 4, 3)
    backbone[:, 0, 2] = -1.0
    backbone[:, 2, 0] = 1.0
    return TeacherPairTrainingExample(
        group_id=group_id,
        split="train",
        sequence_length=length,
        residue_features=torch.full((length, 4), value, dtype=torch.bfloat16),
        backbone_positions=backbone,
        target_ca=torch.full((length, 3), value),
        residue_mask=torch.ones(length, dtype=torch.bool),
        baseline_ca_rmsd=value,
    )


def test_length_aware_collator_sorts_and_masks_padding():
    batch = LengthAwareCollator(pad_to_multiple=4)(
        [_example("short", 3, 1.0), _example("long", 5, 2.0)]
    )
    assert batch["group_ids"] == ["long", "short"]
    assert batch["residue_features"].shape == (2, 8, 4)
    assert batch["backbone_positions"].shape == (2, 8, 4, 3)
    assert batch["residue_mask"].sum(dim=1).tolist() == [5, 3]
    assert not batch["residue_mask"][:, 5:].any()


def test_length_bucket_sampler_is_epoch_deterministic():
    lengths = [20, 21, 22, 100, 101, 102, 500, 501]
    sampler = LengthBucketBatchSampler(
        lengths, batch_size=2, bucket_size_multiplier=2, seed=7, shuffle=True
    )
    first = list(sampler)
    assert first == list(sampler)
    sampler.set_epoch(1)
    second = list(sampler)
    assert first != second
    assert sorted(index for batch in second for index in batch) == list(range(len(lengths)))
