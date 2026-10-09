"""Verify the runtime evidence separately from the incomplete eight-run trial."""
import hashlib
import json
from pathlib import Path


def verify_runtime_snapshot(root):
    read = lambda name: json.loads((root / name).read_text())
    manifest = read("manifest.json")
    for name, digest in manifest["files"].items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
    assert not manifest["scientific_experiment_complete"] and not manifest["recovery_complete"]
    assert len(manifest["original_completed_runs"]) == 7
    assert read("controller.json")["phase"] == "failed"
    assert not read("failed_attempt/report.json")["complete"]
    stop = read("runtime_recovery_stop.json")
    assert not stop["live_pids"] and stop["controller_phase"] == "failed"
    assert stop["proot_signal_exit_code"] == 0
    original = [json.loads(s) for s in (root / "failed_attempt/history.jsonl").read_text().splitlines()]
    replay = [json.loads(s) for s in (root / "runtime_replay_v1/history.jsonl").read_text().splitlines()]
    lock = read("runtime_replay_v1/replay_lock.json")
    result = read("runtime_replay_v1/result.json")
    assert len(original) == 1420 and len(replay) == 1421
    assert original == lock["original_history"]
    for a, b in zip(original, replay):
        for key in ("step", "site", "aa", "loss", "gradient_norm", "clipped"):
            assert a[key] == b[key]
    assert result["complete"] and result["counts"]["updates"] == 1421
    assert result["training_forwards"] == 2842 and result["next_update_completed"]
    assert not result["scientific_replacement"]
    assert result["source_checkpoint_sha256"] == read("failed_attempt/evaluation_0.json")["sha256"]
    assert len(read("failed_attempt/evaluation_0.json")["predictions"]) * 2 == 1824
    recovery = read("execution_recovery.json")
    assert not recovery["complete"] and recovery["one_retry_only"]
    assert recovery["deadline_unix"] == read("runtime_recovery_lock.json")["deadline_unix"]
    assert recovery["recovery_lock_sha256"] == hashlib.sha256((root / "runtime_recovery_lock.json").read_bytes()).hexdigest()
    assert read("runtime_retry_prefix_check.json")["exact_updates"] == 1420
    checks = dict(
        complete=True, snapshot_files=len(manifest["files"]), exact_prefix_scalars=4260,
        diagnostic_updates=1421, recorded_discarded_updates=1420,
        failed_attempt_s1=1824, retry_observed_updates=manifest["retry_recorded_updates"],
        scientific_experiment_complete=False,
        original_unrecorded_partial_update=True,
    )
    (root.parent / "runtime_snapshot_verification.json").write_text(json.dumps(checks, indent=2) + "\n")
    print(json.dumps(checks))


if __name__ == "__main__":
    verify_runtime_snapshot(Path(__file__).resolve().parent / "runtime_snapshot")
