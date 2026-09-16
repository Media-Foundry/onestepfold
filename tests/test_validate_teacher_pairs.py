import gzip
import json
import runpy


def test_validate_teacher_pairs_reports_complete_outputs(tmp_path):
    module = runpy.run_path("scripts/validate_teacher_pairs.py")
    input_root = tmp_path / "input"
    metadata_dir = input_root / "shard-0000"
    metadata_dir.mkdir(parents=True)
    row = {"group_id": "a" * 64}
    with gzip.open(metadata_dir / "metadata.jsonl.gz", "wt", encoding="utf-8") as handle:
        handle.write(json.dumps(row) + "\n")
    output_root = tmp_path / "output"
    for setting in ("c2_s2", "c4_s2"):
        path = module["_prediction"](output_root, setting, "shard-0000", row["group_id"], 101)
        path.parent.mkdir(parents=True)
        path.write_text("data")
    result = module["validate"](input_root, output_root, ("c2_s2", "c4_s2"), 101)
    assert result["complete"] is True
    assert result["present"] == {"c2_s2": 1, "c4_s2": 1}
