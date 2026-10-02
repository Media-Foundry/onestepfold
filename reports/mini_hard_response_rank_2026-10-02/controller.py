import os,subprocess,time,json,signal
from pathlib import Path
base=Path('/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding');root=base/'hard_response_rank_v1_20261002';v=Path('/data/user/shuang886/Folding')/root.name
py='/home/pc/anaconda3/envs/fold/bin/python';proot='/media/IntelSSD/onestepfold/diamondhill_migration_20261001/tools/proot/usr/bin/proot'
env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',LAYERNORM_TYPE='torch',PROTENIX_ROOT_DIR='/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime',PYTHONPATH=f'{v}/code/src:{v}/code/scripts')
prefix=[proot,'-b',str(base)+':/data/user/shuang886/Folding',py,'-u',str(v/'code/scripts/run_hard_response_rank.py'),'--root',str(v)]
def save(n,x):(root/n).write_text(json.dumps(x,indent=2)+'\n')
start=time.time()
with open(root/'prepare.log','w') as f:
 p=subprocess.run(prefix+['--mode','prepare'],env=env,stdout=f,stderr=subprocess.STDOUT,timeout=180)
if p.returncode:save('controller_execution.json',dict(complete=False,stage='prepare',exit=p.returncode));raise SystemExit(p.returncode)
processes=[];handles=[]
for i in range(8):
 f=open(root/f'worker_{i}.log','w');p=subprocess.Popen(prefix+['--mode','run','--index',str(i)],env=dict(env,HIP_VISIBLE_DEVICES=str(i),CUDA_VISIBLE_DEVICES=str(i)),stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
 processes.append(p);handles.append(dict(worker=i,gcd=i,pid=p.pid))
save('handles.json',dict(controller=os.getpid(),started=start,workers=handles))
while any(p.poll() is None for p in processes):
 if time.time()-start>1800:
  for p in processes:
   if p.poll() is None:os.killpg(p.pid,signal.SIGTERM)
  time.sleep(2)
  for p in processes:
   if p.poll() is None:os.killpg(p.pid,signal.SIGKILL)
  break
 time.sleep(3)
exits=[p.wait() for p in processes];save('execution.json',dict(complete=all(x==0 for x in exits),worker_exits=exits,seconds=time.time()-start))
if any(exits):raise SystemExit(1)
with open(root/'collect.log','w') as f:
 p=subprocess.run(prefix+['--mode','collect'],env=dict(env,HIP_VISIBLE_DEVICES='',CUDA_VISIBLE_DEVICES=''),stdout=f,stderr=subprocess.STDOUT,timeout=300)
save('controller_execution.json',dict(complete=p.returncode==0,stage='collect',exit=p.returncode,seconds=time.time()-start))
raise SystemExit(p.returncode)
