#!/usr/bin/env python3
import argparse,json,os,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root.resolve();python='/home/pc/anaconda3/envs/fold/bin/python'
def env_for(device):
 env=os.environ.copy();env.update(ROCR_VISIBLE_DEVICES=str(device),OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',PROTENIX_ROOT_DIR='/media/PM982/onestepfold/protenix_stage0_pkg/v1_1/runtime',PYTHONPATH=str(root/'code/src'));return env
with open(root/'regional_prepare.log','w') as log:
 rc=subprocess.run(['timeout','1800',python,str(root/'code/scripts/prepare_regional_interpolation.py'),'--root',str(root)],env=env_for(0),stdout=log,stderr=subprocess.STDOUT).returncode
if rc:raise RuntimeError('regional preparation failed '+str(rc))
jobs=[];records=[]
for device,(region,sources) in enumerate((r,s) for r in ['local42_43','complement'] for s in ['E','R','C','ERC']):
 folder=root/'regional'/region;label='8bzn_'+sources
 with open(folder/(label+'.log'),'w') as log:
  p=subprocess.Popen(['timeout','1800',python,str(root/'code/scripts/run_regional_input_interpolation.py'),'--root',str(folder),'--case','8bzn','--sources',sources],env=env_for(device),stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 row=dict(region=region,sources=sources,pid=p.pid,device=device,exit_code=None);records.append(row);jobs.append((p,row));(root/'regional_jobs.json').write_text(json.dumps(records,indent=2))
for process,row in jobs:
 row['exit_code']=process.wait();(root/'regional_jobs.json').write_text(json.dumps(records,indent=2))
for region in ['local42_43','complement']:
 (root/'regional'/region/'exit.json').write_text(json.dumps(dict(complete=True,success=all(row['exit_code']==0 for row in records if row['region']==region))))
(root/'regional_exit.json').write_text(json.dumps(dict(complete=True,success=all(row['exit_code']==0 for row in records))))
