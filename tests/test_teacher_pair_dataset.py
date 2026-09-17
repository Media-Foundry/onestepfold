import gzip
import json
from pathlib import Path

import pytest

from onestepfold.data.teacher_pairs import (
    TEACHER_PAIR_SCHEMA_VERSION,
    TeacherPairDataError,
    TeacherPairDataset,
    build_teacher_pair_records,
    load_teacher_pair_manifest,
    write_teacher_pair_manifest,
)


def rows(count: int = 10):
    return [
        {
            "group_id": f"group-{index:02d}",
            "teacher_shard": f"shard-{index % 2:04d}",
            "sequence": "ACD",
            "sequence_length": 3,
            "sample_id": f"sample-{index:02d}",
        }
        for index in range(count)
    ]


def test_exact_group_split_is_reproducible_and_manifest_is_deterministic(tmp_path: Path):
    sources = {"shard-0000": "hpc2", "shard-0001": "hpc3"}
    first = build_teacher_pair_records(
        rows(), validation_count=2, seed=101, c2_sources=sources, c4_sources=sources
    )
    second = build_teacher_pair_records(
        list(reversed(rows())),
        validation_count=2,
        seed=101,
        c2_sources=sources,
        c4_sources=sources,
    )
    assert first == second
    assert sum(record.split == "validation" for record in first) == 2
    assert len({record.group_id for record in first}) == len(first)

    path_a = tmp_path / "a.jsonl.gz"
    path_b = tmp_path / "b.jsonl.gz"
    assert write_teacher_pair_manifest(path_a, first) == write_teacher_pair_manifest(path_b, second)
    assert path_a.read_bytes() == path_b.read_bytes()
    assert load_teacher_pair_manifest(path_a, split="validation") == [
        record for record in first if record.split == "validation"
    ]
    assert len(TeacherPairDataset.from_manifest(path_a, tmp_path, split="train")) == 8


def test_manifest_rejects_parent_traversal(tmp_path: Path):
    path = tmp_path / "bad.jsonl.gz"
    row = {
        "schema_version": TEACHER_PAIR_SCHEMA_VERSION,
        "group_id": "group",
        "split": "train",
        "shard": "shard-0000",
        "sequence": "A",
        "sequence_length": 1,
        "sample_id": "sample",
        "c2_cif": "../outside.cif",
        "c4_cif": "c4.cif",
        "c2_confidence": "c2.json",
        "c4_confidence": "c4.json",
        "c2_source": "hpc2",
        "c4_source": "DiamondHill",
    }
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write(json.dumps(row) + "\n")
    with pytest.raises(TeacherPairDataError, match="relative and contained"):
        load_teacher_pair_manifest(path)


def test_coordinate_loader_aligns_synthetic_pair(tmp_path: Path):
    pytest.importorskip("gemmi")
    # The split helper requires a non-empty train complement, so use a two-row
    # corpus and retain only the first row for this coordinate-loading smoke.
    sources = {"shard-0000": "test", "shard-0001": "test"}
    record = build_teacher_pair_records(
        rows(2), validation_count=1, seed=101, c2_sources=sources, c4_sources=sources
    )[0]
    cif = """data_test
loop_
_atom_site.group_PDB
_atom_site.label_atom_id
_atom_site.label_alt_id
_atom_site.label_comp_id
_atom_site.label_asym_id
_atom_site.label_seq_id
_atom_site.B_iso_or_equiv
_atom_site.Cartn_x
_atom_site.Cartn_y
_atom_site.Cartn_z
_atom_site.pdbx_PDB_model_num
ATOM N . ALA A 1 90 0 0 0 1
ATOM CA . ALA A 1 91 1 0 0 1
ATOM C . ALA A 1 92 1 1 0 1
ATOM O . ALA A 1 93 1 1 1 1
ATOM N . CYS A 2 90 2 1 0 1
ATOM CA . CYS A 2 91 2 2 0 1
ATOM C . CYS A 2 92 3 2 0 1
ATOM O . CYS A 2 93 3 2 1 1
ATOM N . ASP A 3 90 4 2 0 1
ATOM CA . ASP A 3 91 4 3 0 1
ATOM C . ASP A 3 92 5 3 0 1
ATOM O . ASP A 3 93 5 3 1 1
"""
    for relative in (record.c2_cif, record.c4_cif):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(cif, encoding="utf-8")
    for relative, recycles in ((record.c2_confidence, 2), (record.c4_confidence, 4)):
        path = tmp_path / relative
        path.write_text(json.dumps({"num_recycles": recycles, "ptm": 0.5}), encoding="utf-8")

    example = TeacherPairDataset([record], tmp_path)[0]
    assert example.c2.atom_keys == example.c4.atom_keys
    assert example.c2.positions.shape == (12, 3)
    assert example.c2.backbone_positions.shape == (3, 4, 3)
    assert example.c2.backbone_mask.all()
    assert example.c2_confidence["num_recycles"] == 2
