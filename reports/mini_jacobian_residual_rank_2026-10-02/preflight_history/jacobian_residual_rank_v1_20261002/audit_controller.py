import os,subprocess,time,json,signal
from pathlib import Path
base=Path('/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding');root=base/'jacobian_residual_rank_v1_20261002';v=Path('/data/user/shuang886/Folding')/root.name
py='/home/pc/anaconda3/envs/fold/bin/python';proot='/media/IntelSSD/onestepfold/diamondhill_migration_20261001/tools/proot/usr/bin/proot'
env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',LAYERNORM_TYPE='torch',PROTENIX_ROOT_DIR='/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime',PYTHONPATH=f'{v}/code/src:{v}/code/scripts')
prefix=[proot,'-b',str(base)+':/data/user/shuang886/Folding',py,'-u',str(v/'code/scripts/run_global_response_rank.py'),'--root',str(v)]
def save(n,x):(root/n).write_text(json.dumps(x,indent=2)+'\n')
start=time.time();processes={};exits={}
while len(exits)<8:
 for i in range(8):
  if i not in processes:
   try:ready=json.loads((root/f'worker_{i}/report.json').read_text()).get('complete',False)
   except (FileNotFoundError,json.JSONDecodeError):ready=False
   if ready:
    f=open(root/f'basis_audit_{i}.log','w')
    cmd=[proot,'-b',str(base)+':/data/user/shuang886/Folding',py,'-u',str(v/'audit_jacobian_residual_rank.py'),'--root',str(v),'--mode','basis','--index',str(i)]
    processes[i]=subprocess.Popen(cmd,env=dict(env,HIP_VISIBLE_DEVICES='',CUDA_VISIBLE_DEVICES=''),stdout=f,stderr=subprocess.STDOUT)
  if i in processes and processes[i].poll() is not None:exits[i]=processes[i].returncode
 if time.time()-start>7200:
  for p in processes.values():
   if p.poll() is None:p.terminate()
  break
 time.sleep(5)
save('basis_audit_execution.json',dict(complete=len(exits)==8 and all(x==0 for x in exits.values()),exits=exits,seconds=time.time()-start))
