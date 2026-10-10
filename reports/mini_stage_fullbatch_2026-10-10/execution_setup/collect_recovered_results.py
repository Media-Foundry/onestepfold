"""Run on DiamondHill after verification closes; CPU-only export and arithmetic."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tarfile
import time

root = Path('/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/stage_fullbatch_v1_20261010')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
assert os.environ.get('HIP_VISIBLE_DEVICES') == ''
recovery = read(root / 'verification_recovery/controller.json')
assert recovery['complete'] and recovery['phase'] == 'closed'
dest = root / 'result_recovery'
dest.mkdir(exist_ok=False)
(dest / 'code').mkdir()
names = {'export_stage_fullbatch.py', 'src/fastglycan/__init__.py',
         'src/fastglycan/fullbatch_results.py', 'src/fastglycan/fullbatch_recovery.py'}
with tarfile.open('/tmp/fullbatch_recovered_results_039c69be.tar.gz') as archive:
    assert set(archive.getnames()) == names
    for member in archive.getmembers():
        assert member.isfile()
        path = dest / 'code' / member.name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(archive.extractfile(member).read())
lock = dict(created_unix=time.time(), files={n: sha(dest / 'code' / n) for n in sorted(names)},
            training_lock_sha256=sha(root / 'training_lock.json'),
            verification_recovery_lock_sha256=sha(root / 'verification_recovery/lock.json'),
            model_execution=False, new_training=False)
(dest / 'lock.json').write_text(json.dumps(lock, indent=2) + '\n')
sys.path.insert(0, str(dest / 'code/src'))
from fastglycan.fullbatch_results import verify_fullbatch_results, analyze_fullbatch_results
spec = importlib.util.spec_from_file_location('recovered_export', dest / 'code/export_stage_fullbatch.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
status = dict(complete=False, started_unix=time.time(), lock_sha256=sha(dest / 'lock.json'))
try:
    exported = module.export_stage_fullbatch(root)
    checked = verify_fullbatch_results(exported)
    analyze_fullbatch_results(exported)
    assert 'torch' not in sys.modules
    for name in ['lock.json'] + ['code/' + n for n in sorted(names)]:
        path = exported / 'result_recovery' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((dest / name).read_bytes())
    generated = ['manifest.json', 'verification.json', 'optimization_ledger.json', 'analysis.json',
                 'result_recovery/lock.json'] + ['result_recovery/code/' + n for n in sorted(names)]
    (exported / 'postprocess_manifest.json').write_text(json.dumps(dict(complete=True,
        operational_recovery=True, files={n: sha(exported / n) for n in generated}), indent=2) + '\n')
    archive = root / 'fullbatch_export.tar.gz'
    with tarfile.open(archive, 'x:gz') as tar:
        tar.add(exported, arcname='.')
    status.update(complete=True, phase='complete', checks=checked['checks'],
                  archive_sha256=sha(archive), seconds=time.time() - status['started_unix'])
except BaseException as error:
    status.update(phase='failed', error=repr(error))
    raise
finally:
    (dest / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
    print(json.dumps(status))
