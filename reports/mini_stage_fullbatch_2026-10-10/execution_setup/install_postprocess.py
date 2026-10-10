"""Run on DiamondHill; install only the separately hashed CPU result follower."""
import hashlib
import importlib.util
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
names = {'export_stage_fullbatch.py', 'finish_stage_fullbatch.py', 'fullbatch_results.py'}
dest = root / 'postprocess_code'
dest.mkdir(exist_ok=False)
with tarfile.open('/tmp/fullbatch_postprocess_code_78744996.tar.gz') as archive:
    assert set(archive.getnames()) == names
    for member in archive.getmembers():
        assert member.isfile()
        (dest / member.name).write_bytes(archive.extractfile(member).read())
spec = importlib.util.spec_from_file_location('export_gate', dest / 'export_stage_fullbatch.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
assert not controller['complete']
try:
    module.export_stage_fullbatch(root)
except ValueError as error:
    assert 'incomplete' in str(error)
else:
    raise AssertionError('live batch was incorrectly accepted as finished')
assert not (root / 'export').exists() and not (root / 'export.partial').exists()
lock = dict(training_lock_sha256=expected, files={n: sha(dest / n) for n in sorted(names)},
            created_unix=time.time(), scientific_source_mutated=False,
            wait_deadline_unix=controller['training_deadline_unix'] + 10 * 3600,
            incomplete_gate_passed=True, new_model_execution=False,
            source_revision='787449964a2dd95490181bc678d3319a9dd639f8 plus separately hashed result-only code')
(root / 'postprocess_lock.json').write_text(json.dumps(lock, indent=2) + '\n')
env = dict(os.environ, HIP_VISIBLE_DEVICES='', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
assert not any(k in env for k in ('CUDA_VISIBLE_DEVICES', 'ROCR_VISIBLE_DEVICES', 'HSA_VISIBLE_DEVICES'))
with (root / 'postprocess.log').open('x') as log:
    process = subprocess.Popen(['/home/pc/anaconda3/envs/fold/bin/python', '-u',
                                str(dest / 'finish_stage_fullbatch.py'), '--root', str(root)],
                               env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                               start_new_session=True)
launch = dict(pid=process.pid, started_unix=time.time(), lock_sha256=sha(root / 'postprocess_lock.json'))
(root / 'postprocess_launch.json').write_text(json.dumps(launch, indent=2) + '\n')
print(json.dumps(dict(lock=lock, launch=launch)))
