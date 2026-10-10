"""A dependency repair must never hide a scientific or tensor-verification failure."""
import hashlib
import json
from pathlib import Path

import pytest

from fastglycan.fullbatch_recovery import verify_fullbatch_completion


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _completed_recovery(root):
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    configs = [(a, s) for a in ('adamw', 'lbfgs') for s in (272001, 272003)]
    training_sha = _write(root / 'training_lock.json', dict(code={'scripts/verify_stage_fullbatch.py': 'verifier'}))
    jobs = {f'{k}_{a}_{s}': dict(status='complete', exit_code=0)
            for k in ('train', 'score') for a, s in configs}
    for a, s in configs:
        jobs[f'verify_{a}_{s}'] = dict(status='failed', exit_code=1)
        (root / f'verify_{a}_{s}.log').write_text(
            "ModuleNotFoundError: No module named 'verify_stage_pair_recovery'\n")
    controller_sha = _write(root / 'controller.json', dict(complete=False,
        phase='closed_with_failures', jobs=jobs, lock_sha256=training_sha))
    r = root / 'verification_recovery'
    (r / 'code').mkdir(parents=True)
    dependency = Path(__file__).resolve().parents[1] / 'scripts/verify_stage_pair_recovery.py'
    (r / 'code/verify_stage_pair_recovery.py').write_bytes(dependency.read_bytes())
    (r / 'code/recover_stage_fullbatch_verification.py').write_text('test runner')
    (r / 'protocol.md').write_text('test protocol')
    lock_sha = _write(r / 'lock.json', dict(
        schema='fullbatch_verification_dependency_recovery_v1', training_lock_sha256=training_sha,
        original_controller_sha256=controller_sha, protocol_sha256=sha(r / 'protocol.md'),
        code={p.name: sha(p) for p in (r / 'code').iterdir()}, created_unix=1,
        protected_files={'controller.json': controller_sha}, model_code_changed=False,
        verifier_code_changed=False, tolerances_changed=False, training_restarted=False,
        expected_forwards=10944, failed_attempt_forwards=0))
    recovery_jobs = {}
    for a, s in configs:
        result_sha = _write(root / 'runs' / a / str(s) / 'tensor_verification.json',
                            dict(complete=True, feature_forwards=2736, verifier_sha256='verifier'))
        recovery_jobs[f'verify_{a}_{s}'] = dict(status='complete', exit_code=0, hip=4,
            started_unix=2, finished_unix=3, result_sha256=result_sha)
    _write(r / 'controller.json', dict(complete=True, phase='closed', lock_sha256=lock_sha,
        jobs=recovery_jobs, protected_files_unchanged=True, frozen_source_files_verified=1))


def test_recovery_keeps_original_failure_and_binds_successful_replays(tmp_path):
    _completed_recovery(tmp_path)
    before = (tmp_path / 'controller.json').read_bytes()
    assert verify_fullbatch_completion(tmp_path) is True
    assert (tmp_path / 'controller.json').read_bytes() == before


@pytest.mark.parametrize('corruption', ['tensor', 'failure_reason', 'timeout', 'unfinished', 'trained_again'])
def test_recovery_does_not_waive_failed_or_changed_evidence(tmp_path, corruption):
    _completed_recovery(tmp_path)
    r = tmp_path / 'verification_recovery'
    if corruption == 'tensor':
        (tmp_path / 'runs/adamw/272001/tensor_verification.json').write_text('{}')
    elif corruption == 'failure_reason':
        (tmp_path / 'verify_adamw_272001.log').write_text('AssertionError: numerical mismatch')
    elif corruption in ('timeout', 'unfinished'):
        path = r / 'controller.json'; value = json.loads(path.read_text())
        if corruption == 'timeout':
            value['jobs']['verify_adamw_272001']['timeout'] = True
        else:
            value['complete'] = False
        _write(path, value)
    else:
        path = r / 'lock.json'; value = json.loads(path.read_text())
        value['training_restarted'] = True; _write(path, value)
    with pytest.raises((AssertionError, ValueError)):
        verify_fullbatch_completion(tmp_path)
