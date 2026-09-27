"""Provenance and initial replay contract for a single raw-to-geometry adaptation pair."""

import json
from itertools import islice
from pathlib import Path

import numpy as np

from fastglycan.paired_teacher_protocol import sha256
from fastglycan.scaling_runtime import update_schedule as original_schedule

PARENT_STEPS = 22528
MAX_STEPS = 8192


def continuation_schedule(records, max_steps, parent_steps=PARENT_STEPS):
    if not records or parent_steps < 0 or max_steps < 0:
        raise ValueError("Invalid continuation schedule")
    for step, epoch, record, noise in islice(original_schedule(records, parent_steps + max_steps), parent_steps, None):
        yield step - parent_steps, epoch, record, noise


def verify_lock(root, source):
    root, source = Path(root), Path(source)
    lock = json.loads((root / "lock.json").read_text())
    assert lock["schema"] == "esmc-raw-warmstart-v1"
    assert lock["max_steps"] == MAX_STEPS and lock["parent_step"] == PARENT_STEPS
    assert lock["student"] == {"cycles": 1, "structure_evaluations": 1, "K": 1}
    assert str(source) == lock["source_root"]
    assert sha256(source / "source_manifest.json") == lock["source_manifest_sha256"]
    for name, digest in json.loads((source / "source_manifest.json").read_text())["files"].items():
        assert sha256(source / name) == digest, name
    for name, digest in lock["inputs_sha256"].items():
        assert sha256(Path(name)) == digest, name
    parent = Path(lock["parent_root"])
    report = json.loads((parent / "report.json").read_text())
    qa = json.loads((parent / "independent_validation.json").read_text())
    assert report["complete"] and qa["complete"]
    assert qa["report_sha256"] == sha256(parent / "report.json")
    assert report["best_step"] == PARENT_STEPS
    assert sha256(parent / "best.pt") == report["best_checkpoint_sha256"] == lock["checkpoint_sha256"]
    return lock


def verify_initial_view(view, current_root, parent_root, parent_view, arm):
    """Every raw coordinate must match the accepted parent before any update."""
    current_root, parent_root = Path(current_root), Path(parent_root)
    parent = json.loads((parent_root / "report.json").read_text())[parent_view]
    expected = {(r["group_id"], r["noise"]): r for r in parent["rows"]}
    assert len(expected) == len(view["rows"])
    assert {(r["group_id"], r["noise"]) for r in view["rows"]} == set(expected)
    for row in view["rows"]:
        old = expected[row["group_id"], row["noise"]]
        path, original = current_root / row["prediction_path"], parent_root / old["prediction_path"]
        assert sha256(path) == row["prediction_sha256"]
        assert sha256(original) == old["prediction_sha256"]
        with np.load(path) as current, np.load(original) as saved:
            for name in ("raw_coordinate", "atom_name", "residue_id", "element"):
                assert np.array_equal(current[name], saved[name]), (row["group_id"], name)
            if arm == "raw":
                assert np.array_equal(current["coordinate"], saved["coordinate"])
                for key in ("metrics", "geometry", "quality", "weighted_losses", "fallback_counts"):
                    assert row[key] == old[key], key
    return {"complete": True, "raw_exact": True, "rows_checked": len(expected), "arm": arm,
            "parent_view": parent_view, "parent_report_sha256": sha256(parent_root / "report.json")}
