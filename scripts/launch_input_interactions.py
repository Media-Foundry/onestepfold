#!/usr/bin/env python3
"""Conditional ER/EC/RC follow-up on exactly the existing two-target alpha grid."""
import argparse,json,os,subprocess
from pathlib import Path

p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root.resolve()
values={s:json.load(open(root/('8bzn_'+s)/'report.json'))['rows'][7]['tracked_distance'] for s in ['E','R','C','ERC']}
assert values['ERC']<.1 and all(values[s]>=.1 for s in ['E','R','C']),values
records=[];jobs=[]
for device,(case,sources) in enumerate((c,s) for c in ['8bzn','control'] for s in ['ER','EC','RC']):
 label=case+'_'+sources;assert not (root/label).exists()
 env=os.environ.copy();env.update(ROCR_VISIBLE_DEVICES=str(device),OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',PROTENIX_ROOT_DIR='/media/PM982/onestepfold/protenix_stage0_pkg/v1_1/runtime',PYTHONPATH=str(root/'code/src'))
 with open(root/(label+'.log'),'w') as log:
  process=subprocess.Popen(['timeout','1800','/home/pc/anaconda3/envs/fold/bin/python',str(root/'code/scripts/run_input_interpolation.py'),'--root',str(root),'--case',case,'--sources',sources],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 row=dict(label=label,pid=process.pid,device=device,exit_code=None);records.append(row);jobs.append((process,row));(root/'interaction_jobs.json').write_text(json.dumps(records,indent=2))
for process,row in jobs:
 row['exit_code']=process.wait();(root/'interaction_jobs.json').write_text(json.dumps(records,indent=2))
(root/'interaction_exit.json').write_text(json.dumps(dict(complete=True,success=all(r['exit_code']==0 for r in records),trigger_distances=values)))
