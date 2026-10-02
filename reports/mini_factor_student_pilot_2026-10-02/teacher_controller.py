import os,subprocess,time,json,signal
from pathlib import Path
base=Path('/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding');root=base/'factor_student_pilot_v1_20261002';v=Path('/data/user/shuang886/Folding')/root.name
py='/home/pc/anaconda3/envs/fold/bin/python';proot='/media/IntelSSD/onestepfold/diamondhill_migration_20261001/tools/proot/usr/bin/proot'
env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',LAYERNORM_TYPE='torch',PROTENIX_ROOT_DIR='/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime',PYTHONPATH=f'{v}/teacher_code/src:{v}/teacher_code/scripts')
prefix=[proot,'-b',str(base)+':/data/user/shuang886/Folding',py,'-u',str(v/'teacher_code/scripts/export_factor_student_teachers.py'),'--root',str(v)]
def save(n,d):(root/n).write_text(json.dumps(d,indent=2)+'\n')
waitstart=time.time()
while True:
 p=base/'spatial_rank24_v1_20261002/execution.json'
 if p.exists():
  d=json.load(open(p));assert d['complete'];break
 assert time.time()-waitstart<7200
 time.sleep(5)
start=time.time()
with open(root/'teacher_prepare.log','w') as f:p=subprocess.run(prefix+['--mode','prepare'],env=env,stdout=f,stderr=subprocess.STDOUT,timeout=900)
if p.returncode:save('teacher_execution.json',dict(complete=False,stage='prepare',exit=p.returncode));raise SystemExit(1)
ps=[]
for i in range(8):
 f=open(root/f'teacher_{i}.log','w');ps.append(subprocess.Popen(prefix+['--mode','run','--index',str(i)],env=dict(env,HIP_VISIBLE_DEVICES=str(i),CUDA_VISIBLE_DEVICES=str(i)),stdout=f,stderr=subprocess.STDOUT,start_new_session=True))
save('teacher_handles.json',dict(controller=os.getpid(),started=start,workers=[dict(worker=i,pid=p.pid,gcd=i) for i,p in enumerate(ps)]))
while any(p.poll() is None for p in ps):
 if time.time()-start>3600:
  for p in ps:
   if p.poll() is None:os.killpg(p.pid,signal.SIGTERM)
  break
 time.sleep(5)
exits=[p.wait() for p in ps]
if any(exits):save('teacher_execution.json',dict(complete=False,stage='export',worker_exits=exits));raise SystemExit(1)
with open(root/'teacher_collect.log','w') as f:p=subprocess.run(prefix+['--mode','collect'],env=env,stdout=f,stderr=subprocess.STDOUT,timeout=900)
save('teacher_execution.json',dict(complete=p.returncode==0,worker_exits=exits,collector=p.returncode,seconds=time.time()-start))
