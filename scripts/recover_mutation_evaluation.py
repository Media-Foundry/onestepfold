#!/usr/bin/env python3
"""Evaluate the frozen manifest once after proposal audit; no new proposals."""
import argparse,json,os,subprocess,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);root=p.parse_args().root.resolve();(root/'recovery_launch.lock').open('x').close();assert json.loads((root/'proposal/report.json').read_text())['complete']
base=os.environ.copy();base.update(OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',PYTHONPATH=str(root/'code/src'),PROTENIX_ROOT_DIR='/media/PM982/onestepfold/protenix_stage0_pkg/v1_1/runtime');started=time.time();jobs=[]
for worker,device in enumerate([2,3,4,5]):
 if worker:time.sleep(20)
 with open(root/f'evaluate{worker}.log','w') as log:
  jobs.append(subprocess.Popen(['timeout','1800','/home/pc/anaconda3/envs/fold/bin/python',str(root/'code/scripts/run_hard_mutation_utility.py'),'--root',str(root),'--mode','evaluate','--worker',str(worker)],env=base|{'ROCR_VISIBLE_DEVICES':str(device)},stdout=log,stderr=subprocess.STDOUT))
(root/'jobs.json').write_text(json.dumps([dict(worker=i,device=[2,3,4,5][i],pid=j.pid) for i,j in enumerate(jobs)]));codes=[j.wait() for j in jobs];(root/'exit.json').write_text(json.dumps(dict(complete=True,success=all(c==0 for c in codes),codes=codes,elapsed_seconds=time.time()-started)))

if all(c==0 for c in codes):
 with open(root/'score.log','w') as log:
  result=subprocess.run(['/home/pc/anaconda3/envs/fold/bin/python',str(root/'code/scripts/score_hard_mutation_utility.py'),'--root',str(root)],env=base,stdout=log,stderr=subprocess.STDOUT)
 (root/'score_exit.json').write_text(json.dumps(dict(success=result.returncode==0,exit_code=result.returncode)))
