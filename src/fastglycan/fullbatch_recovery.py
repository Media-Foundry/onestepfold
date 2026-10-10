"""Strict completion gate for the recorded dependency-only verifier recovery."""
import hashlib
import json
from pathlib import Path


DEPENDENCY_SHA256 = '1671f75acb7ec3b190ec61aa34d326eb45fbde7a85663ab2f8dd1b8395081e2e'


def verify_fullbatch_completion(root):
    """Accept all original jobs, or the explicitly evidenced import-only repair.

    Return whether operational recovery occurred. Neither branch changes the
    original controller. Missing/partial/failed recovery is never completion.
    """
    root = Path(root)
    read = lambda p: json.loads(p.read_text())
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    controller = read(root / 'controller.json')
    configurations = [(arm, seed) for arm in ('adamw', 'lbfgs') for seed in (272001, 272003)]
    expected = {f'{kind}_{arm}_{seed}' for kind in ('train', 'score', 'verify')
                for arm, seed in configurations}
    jobs = controller.get('jobs', {})
    good = lambda j: j.get('status') == 'complete' and j.get('exit_code') == 0 and not j.get('timeout')
    if (controller.get('complete') and controller.get('phase') == 'closed'
            and set(jobs) == expected and all(good(j) for j in jobs.values())):
        return False
    recovery = root / 'verification_recovery'
    if (controller.get('complete') or controller.get('phase') != 'closed_with_failures'
            or set(jobs) != expected or not (recovery / 'controller.json').exists()):
        raise ValueError('batch is incomplete; no completed verification-only recovery')
    training = read(root / 'training_lock.json')
    lock, state = read(recovery / 'lock.json'), read(recovery / 'controller.json')
    assert lock['schema'] == 'fullbatch_verification_dependency_recovery_v1'
    assert lock['training_lock_sha256'] == sha(root / 'training_lock.json') == controller['lock_sha256']
    assert lock['original_controller_sha256'] == sha(root / 'controller.json')
    assert lock['protocol_sha256'] == sha(recovery / 'protocol.md')
    for field in ('model_code_changed', 'verifier_code_changed', 'tolerances_changed', 'training_restarted'):
        assert lock[field] is False, field
    assert lock['expected_forwards'] == 10944 and lock['failed_attempt_forwards'] == 0
    assert set(lock['code']) == {'recover_stage_fullbatch_verification.py', 'verify_stage_pair_recovery.py'}
    assert lock['code']['verify_stage_pair_recovery.py'] == DEPENDENCY_SHA256
    for name, digest in lock['code'].items():
        assert sha(recovery / 'code' / name) == digest, name
    assert state['complete'] and state['phase'] == 'closed'
    assert state['lock_sha256'] == sha(recovery / 'lock.json')
    assert state['protected_files_unchanged'] is True
    assert state['frozen_source_files_verified'] == len(training['code'])
    assert set(state['jobs']) == {f'verify_{a}_{s}' for a, s in configurations}
    for name, digest in lock['protected_files'].items():
        assert sha(root / name) == digest, name
    for arm, seed in configurations:
        for kind in ('train', 'score'):
            assert good(jobs[f'{kind}_{arm}_{seed}'])
        key = f'verify_{arm}_{seed}'
        original = jobs[key]
        assert original['status'] == 'failed' and original['exit_code'] == 1 and not original.get('timeout')
        assert (root / (key + '.log')).read_text().strip().endswith(
            "ModuleNotFoundError: No module named 'verify_stage_pair_recovery'")
        repaired = state['jobs'][key]
        assert good(repaired) and repaired['hip'] == 4
        assert repaired['finished_unix'] >= repaired['started_unix'] >= lock['created_unix']
        result = root / 'runs' / arm / str(seed) / 'tensor_verification.json'
        assert sha(result) == repaired['result_sha256']
        tensor = read(result)
        assert tensor['complete'] and tensor['feature_forwards'] == 2736
        assert tensor['verifier_sha256'] == training['code']['scripts/verify_stage_fullbatch.py']
    return True
