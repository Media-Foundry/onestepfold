#!/usr/bin/env python3
"""Bounded post-batch CPU audit; never restarts an inference worker."""
import argparse,json,os,subprocess,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root.resolve();deadline=time.monotonic()+2100
while not (root/'exit.json').exists():
 if time.monotonic()>deadline:raise TimeoutError('observation deadline; inspect existing workers')
 pid=json.load(open(root/'controller_launch.json'))['pid']
 if not Path('/proc',str(pid)).exists():raise RuntimeError('controller stopped without exit file')
 time.sleep(10)
if not json.load(open(root/'exit.json'))['success']:raise RuntimeError('worker failure; preserve logs')
env=os.environ.copy();env.update(ROCR_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',PYTHONPATH=str(root/'code/src'))
for script in ['score_near_hard_gradient.py','report_near_hard_gradient.py']:
 with open(root/(script+'.log'),'w') as log:
  result=subprocess.run(['/home/pc/anaconda3/envs/fold/bin/python',str(root/'code/scripts'/script),'--root',str(root)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=900)
 if result.returncode:
  (root/'finalizer_exit.json').write_text(json.dumps(dict(success=False,script=script,exit_code=result.returncode)));raise RuntimeError(script+' failed')
(root/'finalizer_exit.json').write_text(json.dumps(dict(success=True)))
