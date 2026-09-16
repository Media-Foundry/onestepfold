import gzip
import json
import runpy


def test_selector_accepts_pre_filtered_train_manifest(tmp_path):
    module = runpy.run_path("scripts/select_teacher_pairs.py")
    rows = [
        {
            "group_id": "b",
            "sample_id": "b-low",
            "hq_eval_valid": False,
            "resolution_high_angstrom": 2.0,
            "sequence_length": 20,
        },
        {
            "group_id": "b",
            "sample_id": "b-hq",
            "hq_eval_valid": True,
            "resolution_high_angstrom": 2.5,
            "sequence_length": 20,
        },
        {
            "group_id": "a",
            "sample_id": "a-only",
            "hq_eval_valid": True,
            "resolution_high_angstrom": 3.0,
            "sequence_length": 30,
        },
    ]
    selected = module["select_records"](rows, None)
    assert [row["sample_id"] for row in selected] == ["a-only", "b-hq"]

    group_rows = [
        {"group_id": "a", "sequence": "ACDE"},
        {"group_id": "b", "sequence": "FGHI"},
    ]
    attached = module["attach_sequences"](selected, group_rows)
    output = tmp_path / "pairs"
    manifest = module["build_inputs"](attached, output, 2)
    assert manifest["record_count"] == 2
    assert sum(shard["count"] for shard in manifest["shards"]) == 2
    payloads = []
    for path in output.glob("shard-*/metadata.jsonl.gz"):
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            payloads.extend(json.loads(line) for line in handle if line.strip())
    assert {row["sequence"] for row in payloads} == {"ACDE", "FGHI"}
