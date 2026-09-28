#!/usr/bin/env python3
"""Eight bounded complete-ERC logits checks, one independent arm per MI250 GCD."""
import argparse,json,os,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root.resolve();jobs=[];records=[]
for device,(case,alpha,steps) in enumerate((c,i,s) for c in ['8bzn','control'] for i in [0,1] for s in [1,2]):
 label=f'{case}_a{alpha}_s{steps}';assert not (root/label).exists()
 env=os.environ.copy();env.update(ROCR_VISIBLE_DEVICES=str(device),OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',PROTENIX_ROOT_DIR='/media/PM982/onestepfold/protenix_stage0_pkg/v1_1/runtime',PYTHONPATH=str(root/'code/src'))
 with open(root/(label+'.log'),'w') as log:
  process=subprocess.Popen(['timeout','1800','/home/pc/anaconda3/envs/fold/bin/python',str(root/'code/scripts/run_near_hard_gradient.py'),'--root',str(root),'--case',case,'--alpha-index',str(alpha),'--steps',str(steps)],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 row=dict(label=label,pid=process.pid,device=device,exit_code=None);records.append(row);jobs.append((process,row));(root/'jobs.json').write_text(json.dumps(records,indent=2))
for process,row in jobs:
 row['exit_code']=process.wait();(root/'jobs.json').write_text(json.dumps(records,indent=2))
(root/'exit.json').write_text(json.dumps(dict(complete=True,success=all(r['exit_code']==0 for r in records))))
