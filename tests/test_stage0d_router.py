import json
import runpy

import pytest


def test_add_internal_features_requires_exact_one_cycle_coverage(tmp_path):
    module = runpy.run_path("scripts/analyze_stage0d_router.py")
    names = module["INTERNAL_FEATURES"]
    cycle = {name.removeprefix("internal_"): float(index) for index, name in enumerate(names)}
    cycle.update(
        {
            "cycle_index": 1,
            "single_shape": [10, 384],
            "pair_shape": [10, 10, 128],
        }
    )
    path = tmp_path / "internal.jsonl"
    path.write_text(
        json.dumps({"sample_name": "group-a", "cycle_count": 1, "cycles": [cycle]}) + "\n"
    )
    records = [{"group_id": "group-a", "features": {}}]
    module["add_internal_features"](records, path)
    assert set(records[0]["features"]) == set(names)

    bad_path = tmp_path / "bad.jsonl"
    bad_path.write_text(
        json.dumps({"sample_name": "group-a", "cycle_count": 2, "cycles": [cycle]}) + "\n"
    )
    with pytest.raises(ValueError, match="exactly one cycle"):
        module["add_internal_features"]([{"group_id": "group-a", "features": {}}], bad_path)
