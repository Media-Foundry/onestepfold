import importlib.util
from pathlib import Path

_SCRIPT = Path(__file__).parents[1] / "scripts" / "scan_mmcif_catalog.py"
_SPEC = importlib.util.spec_from_file_location("scan_mmcif_catalog", _SCRIPT)
assert _SPEC and _SPEC.loader
scanner = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(scanner)


def test_sharding_is_stable_and_covers_one_bucket():
    ids = ["1abc", "2xyz", "7wxm", "6xu7"]
    first = [scanner._shard_for(pdb_id, 17) for pdb_id in ids]
    second = [scanner._shard_for(pdb_id, 17) for pdb_id in ids]
    assert first == second
    assert all(0 <= shard < 17 for shard in first)


def test_manifest_is_sorted_and_deduplicated(tmp_path):
    raw = tmp_path / "raw"
    for pdb_id in ("7wxm", "1abc"):
        path = raw / pdb_id[1:3] / f"{pdb_id}.cif.gz"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    manifest = tmp_path / "ids.txt"
    manifest.write_text("7wxm\n1abc\n7wxm\n", encoding="utf-8")
    assert [path.name for path in scanner._manifest_paths(raw, manifest)] == [
        "1abc.cif.gz",
        "7wxm.cif.gz",
    ]


def test_shard_path_preserves_requested_suffix(tmp_path):
    path = tmp_path / "entries.jsonl.gz"
    assert scanner._shard_path(path, 3, 8).name == "shard-003.jsonl.gz"
    assert scanner._shard_path(path, 0, 1) == path
