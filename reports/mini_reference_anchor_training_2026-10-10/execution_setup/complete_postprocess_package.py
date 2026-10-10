"""Preserve failed import preflight and supply the frozen package dependencies."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

root=Path('/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/reference_anchor_training_v1_20261010')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(root/'training_lock.json')=='13cda88bacb0bca93f93c59fad801428d120b37f124bcdc022d915127c4cdeff'
assert not (root/'postprocess_lock.json').exists() and not (root/'postprocess_launch.json').exists()
training=json.loads((root/'training_lock.json').read_text());dest=root/'postprocess_code'
assert "No module named 'fastglycan.glycoshape'" in (root/'postprocess_tests.log').read_text()
before={str(p.relative_to(dest)):sha(p) for p in dest.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
attempt=dict(complete=False,reason='missing package dependency before follower launch',
    test_log_sha256=sha(root/'postprocess_tests.log'),original_files=before,created_unix=time.time())
(root/'postprocess_attempt_1.json').write_text(json.dumps(attempt,indent=2)+'\n')
added=[]
for name,digest in training['code'].items():
    assert sha(root/'code'/name)==digest,name
    if name.startswith('src/fastglycan/') and not (dest/name).exists():
        path=dest/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/'code'/name,path)
        added.append(name)
for name,digest in before.items():assert sha(dest/name)==digest,name
shutil.copy2(Path(__file__),dest/'complete_postprocess_package.py')
env=dict(os.environ,HIP_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
    PYTHONPATH=str(dest/'src')+':'+str(dest/'scripts'))
py='/home/pc/anaconda3/envs/fold/bin/python'
with (root/'postprocess_tests_complete_package.log').open('x') as output:
    subprocess.run([py,'-m','pytest','-q','-p','no:cacheprovider',str(dest/'tests/test_anchor_results.py')],
        env=env,stdout=output,stderr=subprocess.STDOUT,check=True,timeout=120)
    subprocess.run([py,'-c','import finish_anchor_training, export_anchor_training; import fastglycan.anchor_results'],
        env=env,stdout=output,stderr=subprocess.STDOUT,check=True,timeout=120)
controller=json.loads((root/'controller.json').read_text())
files={str(p.relative_to(dest)):sha(p) for p in dest.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
lock=dict(training_lock_sha256=sha(root/'training_lock.json'),files=files,created_unix=time.time(),
    wait_deadline_unix=controller['started_unix']+12*3600,training_source_unchanged=True,
    no_model_or_optimizer_execution=True,package_dependencies_added=added,
    failed_preflight_sha256=sha(root/'postprocess_attempt_1.json'),
    successful_preflight_sha256=sha(root/'postprocess_tests_complete_package.log'))
(root/'postprocess_lock.json').write_text(json.dumps(lock,indent=2,sort_keys=True)+'\n')
with (root/'postprocess.log').open('x') as output:
    process=subprocess.Popen([py,'-u',str(dest/'scripts/finish_anchor_training.py'),'--root',str(root)],
        env=env,stdout=output,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
launch=dict(pid=process.pid,started_unix=time.time(),postprocess_lock_sha256=sha(root/'postprocess_lock.json'))
(root/'postprocess_launch.json').write_text(json.dumps(launch,indent=2)+'\n');print(json.dumps(launch))
