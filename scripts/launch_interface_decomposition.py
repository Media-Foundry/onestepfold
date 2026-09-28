#!/usr/bin/env python3
"""Run exactly two independent archived failure points, one GCD each."""
import argparse,json,os,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root.resolve()
(root/'launch.lock').open('x').close()
jobs=[]
for device,case in enumerate(['control','8bzn']):
 env=os.environ.copy();env.update(ROCR_VISIBLE_DEVICES=str(device),OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',PYTHONPATH=str(root/'code/src'),PROTENIX_ROOT_DIR='/media/PM982/onestepfold/protenix_stage0_pkg/v1_1/runtime')
 with open(root/f'{case}.log','w') as log:
  worker=subprocess.Popen(['timeout','1800','/home/pc/anaconda3/envs/fold/bin/python',str(root/'code/scripts/run_interface_decomposition.py'),'--root',str(root),'--case',case],env=env,stdout=log,stderr=subprocess.STDOUT)
 jobs.append((dict(case=case,device=device,pid=worker.pid),worker))
(root/'jobs.json').write_text(json.dumps([record for record,_ in jobs],indent=2))
for record,worker in jobs:record['exit_code']=worker.wait()
(root/'jobs.json').write_text(json.dumps([record for record,_ in jobs],indent=2))
(root/'exit.json').write_text(json.dumps(dict(complete=True,success=all(r['exit_code']==0 for r,_ in jobs))))
