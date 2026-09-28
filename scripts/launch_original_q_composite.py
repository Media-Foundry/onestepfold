#!/usr/bin/env python3
import argparse,json,os,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root.resolve();(root/'composite_launch.lock').open('x').close()
env=os.environ.copy();env.update(ROCR_VISIBLE_DEVICES='0',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',PYTHONPATH=str(root/'code/src'),PROTENIX_ROOT_DIR='/media/PM982/onestepfold/protenix_stage0_pkg/v1_1/runtime')
with open(root/'composite_worker.log','w') as log:
 job=subprocess.Popen(['timeout','1800','/home/pc/anaconda3/envs/fold/bin/python',str(root/'code/scripts/run_original_q_composite.py'),'--root',str(root)],env=env,stdout=log,stderr=subprocess.STDOUT)
(root/'composite_job.json').write_text(json.dumps(dict(pid=job.pid,device=0)))
result=job.wait();(root/'composite_exit.json').write_text(json.dumps(dict(complete=True,success=result==0,exit_code=result)))
