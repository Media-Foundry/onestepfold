import gzip
import json
from pathlib import Path

from onestepfold.data.temporal_dev import select_temporal_dev


def _write(path: Path, rows: list[dict]) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed:
            for row in rows:
                compressed.write((json.dumps(row) + "\n").encode("utf-8"))


def test_temporal_dev_is_group_disjoint_and_deterministic(tmp_path: Path) -> None:
    groups = []
    quality = []
    for index in range(8):
        group_id = f"group-{index:02d}"
        length = 40 + index * 40
        groups.append(
            {
                "group_id": group_id,
                "sequence": "A" * length,
                "sequence_length": length,
                "split": "test_candidate",
                "train_seen": False,
                "low_homology_pass": index == 7,
            }
        )
        quality.append(
            {
                "pdb_id": f"{index:04d}",
                "sample_id": f"{index:04d}.assembly-1.model-1",
                "group_id": group_id,
                "sequence": "A" * length,
                "sequence_length": length,
                "resolution_high_angstrom": 2.0 + index / 10,
                "experimental_methods": ["X-RAY DIFFRACTION"],
                "hq_eval_valid": True,
                "views": ["monomer_clean"],
                "qa": {"frame_coverage": 0.90, "heavy_atom_coverage": 0.90},
            }
        )
    quality.append(
        {
            "pdb_id": "0008",
            "sample_id": "0008.assembly-1.model-1",
            "group_id": "group-00",
            "sequence": "A" * 40,
            "sequence_length": 40,
            "resolution_high_angstrom": 2.8,
            "experimental_methods": ["X-RAY DIFFRACTION"],
            "hq_eval_valid": True,
            "views": ["monomer_clean"],
            "qa": {"frame_coverage": 0.99, "heavy_atom_coverage": 0.80},
        }
    )
    groups_path = tmp_path / "groups.jsonl.gz"
    quality_path = tmp_path / "quality.jsonl.gz"
    output_a = tmp_path / "out-a"
    output_b = tmp_path / "out-b"
    _write(groups_path, groups)
    _write(quality_path, quality)

    summary_a = select_temporal_dev(
        groups_path, quality_path, output_a, dev_size=4, variance_size=2, seed=101
    )
    select_temporal_dev(groups_path, quality_path, output_b, dev_size=4, variance_size=2, seed=101)
    assert summary_a["dev_group_count"] == 4
    assert summary_a["frozen_test_group_count"] == 4
    assert summary_a["variance_group_count"] == 2

    def read(path: Path) -> list[dict]:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]

    dev_a = read(output_a / "temporal_dev_v1.jsonl.gz")
    dev_b = read(output_b / "temporal_dev_v1.jsonl.gz")
    variance_a = read(output_a / "temporal_variance_v1.jsonl.gz")
    variance_b = read(output_b / "temporal_variance_v1.jsonl.gz")
    frozen = read(output_a / "frozen_temporal_test_v1.jsonl.gz")
    low_homology = read(output_a / "frozen_temporal_low_homology_groups_v1.jsonl.gz")
    assert dev_a == dev_b
    assert variance_a == variance_b
    assert {row["stage0_group_id"] for row in variance_a} <= {
        row["stage0_group_id"] for row in dev_a
    }
    assert {row["stage0_group_id"] for row in dev_a}.isdisjoint(
        {row["stage0_group_id"] for row in frozen}
    )
    assert "group-07" not in {row["stage0_group_id"] for row in dev_a}
    assert {row["group_id"] for row in low_homology} == {"group-07"}
    assert any(
        row["stage0_group_id"] == "group-00" and row["pdb_id"] == "0008"
        for row in dev_a + frozen
    )
