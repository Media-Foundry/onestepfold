#!/usr/bin/env python3
"""Bounded eight-GCD batch with a shared runtime preflight and explicit exit codes."""
import json,os,subprocess,time
from pathlib import Path
root=Path('/media/PM982/onestepfold/mini_hybrid_v1_20260928')
source=root/'code_v2';python='/home/pc/anaconda3/envs/fold/bin/python'
env=os.environ.copy()
for key in ('CUDA_VISIBLE_DEVICES','HIP_VISIBLE_DEVICES'):env.pop(key,None)
env.update(PYTHONPATH=str(source/'src'),PROTENIX_ROOT_DIR='/media/PM982/onestepfold/protenix_stage0_pkg/v1_1/runtime',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',PYTHONUNBUFFERED='1',PYTORCH_ALLOC_CONF='expandable_segments:True')
workers=[]
def save(name,value):
 temp=root/(name+'.part');temp.write_text(json.dumps(value,indent=2));temp.replace(root/name)
def launch(case,steps,gcd,derivatives=False):
 command=['timeout','--kill-after=30','7200',python,str(source/'scripts/run_mini_hybrid_pilot.py'),'--root',str(root),'--case',case,'--steps',str(steps)]
 if derivatives:command.append('--derivatives-only')
 log=open(root/f'{case}_s{steps}.log','x')
 p=subprocess.Popen(command,env=env|dict(ROCR_VISIBLE_DEVICES=str(gcd)),stdout=log,stderr=subprocess.STDOUT);log.close()
 workers.append((p,dict(case=case,steps=steps,gcd=gcd,pid=p.pid,command=command)))
 save('launch.json',[w for _,w in workers]);return p
assert json.load(open(root/'geometry_regression.json'))['complete']
first=launch('initial100',1,0)
deadline=time.monotonic()+900
while True:
 if first.poll() is not None:raise RuntimeError('preflight worker exited before launch gate')
 path=root/'initial100_s1/report.json'
 if path.exists():
  d=json.load(open(path))
  if 'coordinates_old_float32' in d.get('segments',{}) and d.get('frozen_forward_max_abs')==0:break
 if time.monotonic()>deadline:raise TimeoutError('preflight did not reach coordinate check; do not duplicate')
 time.sleep(10)
for case,steps,gcd,only in [('8bzn',1,1,False),('control',1,2,False),('9qr4',1,3,False),('confirmation1',1,4,False),('confirmation2',1,5,False),('8bzn',2,6,True),('control',2,7,True)]:launch(case,steps,gcd,only)
while any(p.poll() is None for p,_ in workers):
 save('status.json',[w|dict(exit_code=p.poll()) for p,w in workers]);time.sleep(20)
save('status.json',[w|dict(exit_code=p.returncode) for p,w in workers])
results={f'{w["case"]}_s{w["steps"]}':p.returncode for p,w in workers}
save('exit.json',dict(complete=True,results=results))
