import os,time,json,subprocess,hashlib
from pathlib import Path
r=Path('/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/factor_learnability_v1_20261002');base=r.parent;v=Path('/data/user/shuang886/Folding')/r.name
py='/home/pc/anaconda3/envs/fold/bin/python';proot='/media/IntelSSD/onestepfold/diamondhill_migration_20261001/tools/proot/usr/bin/proot'
env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',LAYERNORM_TYPE='torch',PROTENIX_ROOT_DIR='/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime',PYTHONPATH=f'{v}/code/src:{v}/code/scripts')
start=time.time()
while not (r/'execution.json').exists():
 assert time.time()-start<1800
 time.sleep(5)
assert json.loads((r/'execution.json').read_text())['complete']
status={}
for mode in ['memory','sparse']:
 with open(r/f'audit_{mode}.log','w') as f:
  p=subprocess.run([proot,'-b',str(base)+':/data/user/shuang886/Folding',py,'-u',str(v/'audit_factor_learnability.py'),'--root',str(v),'--mode',mode],env=dict(env,HIP_VISIBLE_DEVICES='0' if mode=='memory' else '',CUDA_VISIBLE_DEVICES='0' if mode=='memory' else ''),stdout=f,stderr=subprocess.STDOUT,timeout=900)
 status[mode]=p.returncode
 if p.returncode:break
(r/'audit_execution.json').write_text(json.dumps(dict(complete=len(status)==2 and not any(status.values()),exits=status,audit_code_sha256=hashlib.sha256((r/'audit_factor_learnability.py').read_bytes()).hexdigest(),seconds=time.time()-start),indent=2))
