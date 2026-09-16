import gzip
import json
import runpy


def _write_rows(path, rows):
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def test_hash_partitions_are_disjoint_and_complete(tmp_path):
    module = runpy.run_path("scripts/build_esmc_cache.py")
    read_groups = module["_read_groups"]
    rows = [
        {"group_id": f"{index:064x}", "sequence": "AC", "sequence_length": 2} for index in range(8)
    ]
    path = tmp_path / "groups.jsonl.gz"
    _write_rows(path, rows)
    left = read_groups(path, None, 2, 0)
    right = read_groups(path, None, 2, 1)
    left_ids = {row["group_id"] for row in left}
    right_ids = {row["group_id"] for row in right}
    assert not left_ids & right_ids
    assert left_ids | right_ids == {row["group_id"] for row in rows}


def test_merge_keeps_partition_relative_shard_paths(tmp_path):
    module = runpy.run_path("scripts/merge_esmc_cache_parts.py")
    merge = module["merge"]
    rows = [
        {"group_id": f"{index:064x}", "sequence": "AC", "sequence_length": 2} for index in range(2)
    ]
    groups_path = tmp_path / "groups.jsonl.gz"
    _write_rows(groups_path, rows)
    spec = {
        "feature_variant": "final",
        "model_id": "biohub/ESMC-300M",
        "hf_revision": "abc",
        "code_revision": "def",
        "dtype": "bfloat16",
    }
    for index, row in enumerate(rows):
        part = tmp_path / f"part-{index:03d}"
        part.mkdir()
        (part / "feature_spec.json").write_text(json.dumps(spec))
        (part / "summary.json").write_text(json.dumps({"total_residues": 2, "shard_count": 1}))
        _write_rows(
            part / "manifest.jsonl.gz",
            [{**row, "shard": "shard-00000.safetensors"}],
        )
    summary = merge(tmp_path, groups_path)
    merged = module["read_jsonl_gz"](tmp_path / "manifest.jsonl.gz")
    assert summary["groups_processed"] == 2
    assert {row["shard"] for row in merged} == {
        "part-000/shard-00000.safetensors",
        "part-001/shard-00000.safetensors",
    }
