"""Operational recovery must preserve failures and select only verified outputs."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "stage_export", REPO / "scripts/export_stage_pair_recovery.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value) + "\n")


def test_incomplete_recovery_cannot_export(tmp_path):
    write_json(tmp_path / "controller.json", {"complete": False, "phase": "failed"})
    write_json(tmp_path / "execution_recovery.json", {"complete": False, "phase": "train"})
    with pytest.raises(AssertionError):
        module.export_stage_recovery(tmp_path)
    assert not (tmp_path / "export").exists()


def test_export_preserves_failed_attempt_and_explicit_replacement(tmp_path):
    write_json(tmp_path / "controller.json", {"complete": False, "phase": "failed"})
    write_json(tmp_path / "execution_recovery.json", {
        "complete": True, "phase": "closed", "one_retry_only": True,
        "source_provider": str(tmp_path / "runtime_retry_v1"),
        "jobs": {k: {"status": "complete", "exit_code": 0} for k in ("train", "score", "verify")},
    })
    code = tmp_path / "code/example.py"
    code.parent.mkdir(); code.write_text("# frozen\n")
    write_json(tmp_path / "build_lock.json", {
        "code": {"example.py": hashlib.sha256(code.read_bytes()).hexdigest()}
    })
    for name in ("protocol.md", "controller.log", "preflight_tests.log", "stage_manifest.json",
                 "runtime_recovery_lock.json", "runtime_recovery_protocol.md", "runtime_recovery_stop.json",
                 "controller_before_recovery.json", "runtime_retry_launch.json"):
        (tmp_path / name).write_text("{}\n")
    for i in range(4): write_json(tmp_path / f"cache_{i}.json", {})
    for cohort in ("n1", "n15"):
        cfg = {"arms": ["final", "hint"], "seeds": [272001, 272003], "checkpoints": [0]}
        write_json(tmp_path / cohort / "training_lock.json", cfg)
        for arm in cfg["arms"]:
            for seed in cfg["seeds"]:
                folder = tmp_path / cohort / "runs" / arm / str(seed)
                for name in ("report.json", "tensor_verification.json", "score_complete.json",
                             "history.jsonl", "evaluation_0.json", "summary_0.json", "scores_0.json.gz"):
                    write_json(folder / name, {"complete": True, "origin": "original"})
    failed = tmp_path / "n15/runs/final/272003"
    write_json(failed / "report.json", {"complete": False, "step": 1408})
    (failed / "history.jsonl").write_text("{}\n" * 1420)
    write_json(failed / "evaluation_0.json", {"predictions": [{}] * 912})
    retry = tmp_path / "runtime_retry_v1"
    retry.mkdir()
    (retry / "training_lock.json").write_bytes((tmp_path / "n15/training_lock.json").read_bytes())
    (retry / "python_stack.log").write_text("observer only\n")
    replacement = retry / "runs/final/272003"
    for name in ("report.json", "tensor_verification.json", "score_complete.json", "history.jsonl",
                 "evaluation_0.json", "summary_0.json", "scores_0.json.gz"):
        write_json(replacement / name, {"complete": True, "origin": "retry"})
    write_json(tmp_path / "runtime_replay_v1/result.json", {
        "counts": {"updates": 1421}, "complete": True, "exact_updates": 1420, "next_update_completed": True,
    })
    module.export_stage_recovery(tmp_path)
    out = tmp_path / "export"
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["operational_recovery"] and len(manifest["source_provider_map"]) == 8
    assert json.loads((out / "n15/runs/final/272003/report.json").read_text())["origin"] == "retry"
    assert not json.loads((out / "failed_attempt/n15_final_272003/report.json").read_text())["complete"]
    assert manifest["operational_extra_accounting"]["failed_attempt_s1"] == 1824
    assert (failed / "history.jsonl").read_text() == "{}\n" * 1420
    for name, digest in manifest["files"].items():
        assert hashlib.sha256((out / name).read_bytes()).hexdigest() == digest


def test_observer_preserves_arguments_main_and_failure_exit(tmp_path):
    original = tmp_path / "worker.py"
    original.write_text("import sys\nassert __name__ == '__main__'\nassert sys.argv[1:] == ['--flag', 'value']\nraise SystemExit(7)\n")
    env = dict(os.environ, FASTGLYCAN_LOCKED_STAGE_SCRIPT=str(original),
               FASTGLYCAN_RUNTIME_STACK_LOG=str(tmp_path / "stack.log"))
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts/observe_stage_retry.py"), "--flag", "value"],
        env=env, capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 7 and "STACK_HANDLER_READY" in result.stdout
    assert (tmp_path / "stack.log").is_file()
