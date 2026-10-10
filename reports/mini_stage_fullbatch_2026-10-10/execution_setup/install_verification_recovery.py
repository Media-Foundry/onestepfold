"""Run on DiamondHill; append a verification-only recovery, preserving all attempts."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
import time

root = Path('/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/stage_fullbatch_v1_20261010')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
expected = 'ed09b10002eaa7d04a4f2ea5843bf33657188a64cfd04836934aa47679993eed'
assert sha(root / 'training_lock.json') == expected
controller = json.loads((root / 'controller.json').read_text())
assert not controller['complete'] and controller['phase'] == 'closed_with_failures'
assert len(controller['jobs']) == 12
for name, job in controller['jobs'].items():
    if name.startswith('verify_'):
        assert job['status'] == 'failed' and job['exit_code'] == 1
        assert (root / (name + '.log')).read_text().strip().endswith(
            "ModuleNotFoundError: No module named 'verify_stage_pair_recovery'")
    else:
        assert job['status'] == 'complete' and job['exit_code'] == 0
    assert not job.get('timeout')
    assert not Path('/proc') .joinpath(str(job['pid'])).exists()
training = json.loads((root / 'training_lock.json').read_text())
assert not (root / 'code/scripts/verify_stage_pair_recovery.py').exists()
dest = root / 'verification_recovery'
dest.mkdir(exist_ok=False)
(dest / 'code').mkdir()
names = {'recover_stage_fullbatch_verification.py', 'verify_stage_pair_recovery.py', 'protocol.md'}
with tarfile.open('/tmp/fullbatch_verification_recovery_039c69be.tar.gz') as archive:
    assert set(archive.getnames()) == names
    for member in archive.getmembers():
        assert member.isfile()
        path = dest / 'protocol.md' if member.name == 'protocol.md' else dest / 'code' / member.name
        path.write_bytes(archive.extractfile(member).read())
assert sha(dest / 'code/verify_stage_pair_recovery.py') == '1671f75acb7ec3b190ec61aa34d326eb45fbde7a85663ab2f8dd1b8395081e2e'
protected = [p for p in root.iterdir() if p.is_file()]
for arm in training['arms']:
    for seed in training['seeds']:
        folder = root / 'runs' / arm / str(seed)
        assert not (folder / 'tensor_verification.json').exists()
        protected.extend(p for p in folder.iterdir() if p.is_file())
lock = dict(schema='fullbatch_verification_dependency_recovery_v1',
    created_unix=time.time(), training_lock_sha256=expected,
    source_revision='039c69bec2e3f7b4f613892db7dc2ba4420d64e2',
    original_controller_sha256=sha(root / 'controller.json'),
    protocol_sha256=sha(dest / 'protocol.md'),
    code={p.name: sha(p) for p in (dest / 'code').iterdir()},
    protected_files={str(p.relative_to(root)): sha(p) for p in protected},
    model_code_changed=False, verifier_code_changed=False, tolerances_changed=False,
    training_restarted=False, expected_forwards=10944, failed_attempt_forwards=0)
(dest / 'lock.json').write_text(json.dumps(lock, indent=2, sort_keys=True) + '\n')
with (dest / 'controller.log').open('x') as output:
    process = subprocess.Popen(['python3', '-u', str(dest / 'code/recover_stage_fullbatch_verification.py'),
                                '--root', str(root)], env=dict(os.environ, HIP_VISIBLE_DEVICES='4'),
                               stdout=output, stderr=subprocess.STDOUT,
                               stdin=subprocess.DEVNULL, start_new_session=True)
launch = dict(pid=process.pid, started_unix=time.time(), lock_sha256=sha(dest / 'lock.json'))
(dest / 'launch.json').write_text(json.dumps(launch, indent=2) + '\n')
print(json.dumps(launch))
