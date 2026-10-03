import json,os,time,subprocess
from pathlib import Path
r=Path('/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/task_readout_v1a_20261003')
v='/data/user/shuang886/Folding/'+r.name
for _ in range(480):
 p=r/'execution.json'
 if p.exists():
  x=json.loads(p.read_text())
  if not x['complete']: raise RuntimeError(x)
  break
 time.sleep(10)
else: raise TimeoutError('batch not complete')
env=dict(os.environ,HIP_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONPATH=v+'/code/src:'+v+'/code/scripts')
for k in ('CUDA_VISIBLE_DEVICES','ROCR_VISIBLE_DEVICES','GPU_DEVICE_ORDINAL','HSA_VISIBLE_DEVICES'):env.pop(k,None)
cmd=['/media/IntelSSD/onestepfold/diamondhill_migration_20261001/tools/proot/usr/bin/proot','-b',str(r.parent)+':/data/user/shuang886/Folding','/home/pc/anaconda3/envs/fold/bin/python',v+'/audit_task_readout.py','--root',v]
t=time.monotonic()
with (r/'audit.log').open('w') as f:result=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=1800)
(r/'audit_execution.json').write_text(json.dumps(dict(complete=result.returncode==0,exit=result.returncode,seconds=time.monotonic()-t)))
