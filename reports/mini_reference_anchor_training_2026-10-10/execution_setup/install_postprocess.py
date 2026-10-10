"""Add a separately locked result follower without touching scientific code."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
import time

root=Path('/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/reference_anchor_training_v1_20261010')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(root/'training_lock.json')=='13cda88bacb0bca93f93c59fad801428d120b37f124bcdc022d915127c4cdeff'
training=json.loads((root/'training_lock.json').read_text())
for n,digest in training['code'].items():assert sha(root/'code'/n)==digest,n
dest=root/'postprocess_code';dest.mkdir(exist_ok=False);files=[]
with tarfile.open('/tmp/reference_anchor_postprocess_c12a2681.tar.gz') as archive:
    for item in archive:
        assert item.isfile() and not Path(item.name).is_absolute() and '..' not in Path(item.name).parts
        path=dest/item.name;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(archive.extractfile(item).read());files.append(item.name)
env=dict(os.environ,HIP_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
    PYTHONPATH=str(dest/'src')+':'+str(dest/'scripts'))
py='/home/pc/anaconda3/envs/fold/bin/python'
with (root/'postprocess_tests.log').open('x') as output:
    subprocess.run([py,'-m','pytest','-q','-p','no:cacheprovider',str(dest/'tests/test_anchor_results.py')],
        env=env,stdout=output,stderr=subprocess.STDOUT,check=True,timeout=120)
    subprocess.run([py,'-c','import finish_anchor_training, export_anchor_training; import fastglycan.anchor_results'],
        env=env,stdout=output,stderr=subprocess.STDOUT,check=True,timeout=120)
controller=json.loads((root/'controller.json').read_text())
lock=dict(training_lock_sha256=sha(root/'training_lock.json'),files={n:sha(dest/n) for n in files},
    created_unix=time.time(),wait_deadline_unix=controller['started_unix']+12*3600,
    training_source_unchanged=True,no_model_or_optimizer_execution=True)
(root/'postprocess_lock.json').write_text(json.dumps(lock,indent=2,sort_keys=True)+'\n')
with (root/'postprocess.log').open('x') as output:
    process=subprocess.Popen([py,'-u',str(dest/'scripts/finish_anchor_training.py'),'--root',str(root)],
        env=env,stdout=output,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
launch=dict(pid=process.pid,started_unix=time.time(),postprocess_lock_sha256=sha(root/'postprocess_lock.json'))
(root/'postprocess_launch.json').write_text(json.dumps(launch,indent=2)+'\n');print(json.dumps(launch))
