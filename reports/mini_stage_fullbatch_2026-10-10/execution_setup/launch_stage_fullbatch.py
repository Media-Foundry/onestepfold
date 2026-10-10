import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

root = Path('/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/stage_fullbatch_v1_20261010')
assert (root/'training_lock.json').exists()
assert not (root/'launch.json').exists() and not (root/'controller.json').exists()
with (root/'controller.log').open('x') as output:
    process = subprocess.Popen(['/home/pc/anaconda3/envs/fold/bin/python','-u',
        str(root/'code/scripts/control_stage_fullbatch.py'),'--root',str(root)],
        cwd=root,env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1'),
        stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
record = dict(pid=process.pid,started_unix=time.time(),
              lock_sha256=hashlib.sha256((root/'training_lock.json').read_bytes()).hexdigest())
(root/'launch.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record))
