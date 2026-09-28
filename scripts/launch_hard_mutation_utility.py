#!/usr/bin/env python3
import argparse,json,os,subprocess,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);root=p.parse_args().root.resolve();(root/'launch.lock').open('x').close()
base=os.environ.copy();base.update(OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',PYTHONPATH=str(root/'code/src'),PROTENIX_ROOT_DIR='/media/PM982/onestepfold/protenix_stage0_pkg/v1_1/runtime')
script=str(root/'code/scripts/run_hard_mutation_utility.py');python='/home/pc/anaconda3/envs/fold/bin/python'
def launch(mode,worker):
 env=base|{'ROCR_VISIBLE_DEVICES':str([2,3,4,5][worker])};log=open(root/f'{mode}{worker}.log','w');job=subprocess.Popen(['timeout','1800',python,script,'--root',str(root),'--mode',mode,'--worker',str(worker)],env=env,stdout=log,stderr=subprocess.STDOUT);log.close();return job
started=time.time();job=launch('propose',0);code=job.wait();(root/'proposal_exit.json').write_text(json.dumps(dict(exit_code=code,success=code==0)))
if code:raise SystemExit(code)
jobs=[launch('evaluate',i) for i in range(4)];(root/'jobs.json').write_text(json.dumps([dict(worker=i,pid=j.pid) for i,j in enumerate(jobs)]));codes=[j.wait() for j in jobs];(root/'exit.json').write_text(json.dumps(dict(complete=True,success=all(c==0 for c in codes),codes=codes,elapsed_seconds=time.time()-started)))
