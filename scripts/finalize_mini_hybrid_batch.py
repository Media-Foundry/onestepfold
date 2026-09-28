#!/usr/bin/env python3
import json,os,subprocess,time
from pathlib import Path
root=Path('/media/PM982/onestepfold/mini_hybrid_v1_20260928');deadline=time.monotonic()+7500
while not (root/'exit.json').exists():
 pid=json.load(open(root/'controller_launch.json'))['pid']
 if not Path('/proc',str(pid)).exists():raise RuntimeError('controller terminated without exit manifest; inspect logs, do not restart inference')
 if time.monotonic()>deadline:raise TimeoutError('batch observation deadline; inspect existing handles')
 time.sleep(20)
exits=json.load(open(root/'exit.json'))
if any(exits['results'].values()):raise RuntimeError('one or more workers failed: '+str(exits))
env=os.environ.copy();env.update(ROCR_VISIBLE_DEVICES='',PYTHONPATH=str(root/'code_v2/src'),OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',PROTENIX_ROOT_DIR='/media/PM982/onestepfold/protenix_stage0_pkg/v1_1/runtime')
command=['/home/pc/anaconda3/envs/fold/bin/python',str(root/'code_v2/scripts/score_mini_hybrid_pilot.py'),'--root',str(root),'--out',str(root/'final')]
with open(root/'score.log','w') as log:result=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=3600)
(root/'finalizer_exit.json').write_text(json.dumps(dict(scorer_exit_code=result.returncode)))
if result.returncode:raise RuntimeError('independent scoring failed')
