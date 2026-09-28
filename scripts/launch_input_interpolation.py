#!/usr/bin/env python3
"""Bounded two-target preparation followed by eight independent source scans."""
import argparse,json,os,subprocess
from pathlib import Path

p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root.resolve();python='/home/pc/anaconda3/envs/fold/bin/python';records=[]
def launch(label,device,script,args):
 env=os.environ.copy();env.update(ROCR_VISIBLE_DEVICES=str(device),OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',PROTENIX_ROOT_DIR='/media/PM982/onestepfold/protenix_stage0_pkg/v1_1/runtime',PYTHONPATH=str(root/'code/src'))
 with open(root/(label+'.log'),'w') as log:
  process=subprocess.Popen(['timeout','1800',python,str(root/'code/scripts'/script),'--root',str(root),*args],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 record=dict(label=label,pid=process.pid,device=device,exit_code=None);records.append(record);(root/'jobs.json').write_text(json.dumps(records,indent=2));return process,record
def wait_group(jobs):
 for process,record in jobs:
  record['exit_code']=process.wait();(root/'jobs.json').write_text(json.dumps(records,indent=2))
 return all(r['exit_code']==0 for _,r in jobs)
try:
 jobs=[launch('prepare_'+case,device,'prepare_input_interpolation.py',['--case',case]) for device,case in enumerate(['8bzn','control'])]
 if not wait_group(jobs):raise RuntimeError('preparation failed; no inference submitted')
 for case in ['8bzn','control']:
  if not json.load(open(root/('prepare_'+case)/'report.json'))['complete']:raise RuntimeError('incomplete preparation')
 jobs=[]
 for device,(case,sources) in enumerate((c,s) for c in ['8bzn','control'] for s in ['E','R','C','ERC']):
  jobs.append(launch(case+'_'+sources,device,'run_input_interpolation.py',['--case',case,'--sources',sources]))
 if not wait_group(jobs):raise RuntimeError('one or more scans failed')
 (root/'exit.json').write_text(json.dumps(dict(complete=True,success=True)))
except Exception as error:
 (root/'exit.json').write_text(json.dumps(dict(complete=True,success=False,error=str(error))));raise
