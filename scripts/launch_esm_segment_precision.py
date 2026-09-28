#!/usr/bin/env python3
import argparse,json,os,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root.resolve();(root/'launch.lock').open('x').close()
env=os.environ.copy();env.update(ROCR_VISIBLE_DEVICES='0',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',PYTHONPATH=str(root/'code/src'))
with open(root/'worker.log','w') as log:
 job=subprocess.Popen(['timeout','1800','/home/pc/anaconda3/envs/fold/bin/python',str(root/'code/scripts/run_esm_segment_precision.py'),'--root',str(root)],env=env,stdout=log,stderr=subprocess.STDOUT)
(root/'job.json').write_text(json.dumps(dict(pid=job.pid,device=0)))
result=job.wait();(root/'exit.json').write_text(json.dumps(dict(complete=True,success=result==0,exit_code=result)))
