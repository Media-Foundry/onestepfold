import os,subprocess,time,json,signal
from pathlib import Path
base=Path('/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding');root=base/'factor_student_pilot_v1_20261002';v=Path('/data/user/shuang886/Folding')/root.name
py='/home/pc/anaconda3/envs/fold/bin/python';proot='/media/IntelSSD/onestepfold/diamondhill_migration_20261001/tools/proot/usr/bin/proot'
env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',LAYERNORM_TYPE='torch',PROTENIX_ROOT_DIR='/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime',PYTHONPATH=f'{v}/student_code/src:{v}/student_code/scripts')
def cmd(script,args):return [proot,'-b',str(base)+':/data/user/shuang886/Folding',py,'-u',str(v/'student_code/scripts'/script),'--root',str(v)]+args
def save(n,d):(root/n).write_text(json.dumps(d,indent=2)+'\n')
def single(script,args,label,gpu=''):
 with open(root/f'{label}.log','w') as f:p=subprocess.run(cmd(script,args),env=dict(env,HIP_VISIBLE_DEVICES=gpu,CUDA_VISIBLE_DEVICES=gpu),stdout=f,stderr=subprocess.STDOUT,timeout=900)
 if p.returncode:save('student_execution.json',dict(complete=False,stage=label,exit=p.returncode));raise SystemExit(1)
def phase(script,args,n,label,gpu=True):
 ps=[];start=time.time()
 for i in range(n):
  f=open(root/f'{label}_{i}.log','w');ps.append(subprocess.Popen(cmd(script,args+['--index',str(i)]),env=dict(env,HIP_VISIBLE_DEVICES=str(i) if gpu else '',CUDA_VISIBLE_DEVICES=str(i) if gpu else ''),stdout=f,stderr=subprocess.STDOUT,start_new_session=True))
 save(label+'_handles.json',dict(started=start,pids=[p.pid for p in ps]))
 while any(p.poll() is None for p in ps):
  if time.time()-start>3600:
   for p in ps:
    if p.poll() is None:os.killpg(p.pid,signal.SIGTERM)
   break
  time.sleep(5)
 exits=[p.wait() for p in ps];save(label+'_execution.json',dict(complete=not any(exits),exits=exits,seconds=time.time()-start))
 if any(exits):save('student_execution.json',dict(complete=False,stage=label,exits=exits));raise SystemExit(1)
waitstart=time.time()
while True:
 p=root/'teacher_execution.json'
 if p.exists():assert json.load(open(p))['complete'];break
 assert time.time()-waitstart<7200
 time.sleep(5)
start=time.time();single('prepare_factor_student_training.py',[],'student_prepare');single('preflight_factor_student.py',[],'student_preflight',gpu='0')
phase('train_factor_student_pilot.py',[],2,'training')
single('evaluate_factor_student_pilot.py',['--mode','prepare'],'evaluation_prepare')
phase('evaluate_factor_student_pilot.py',['--mode','run'],8,'evaluation')
phase('evaluate_factor_student_pilot.py',['--mode','score'],8,'evaluation_score',gpu=False)
single('evaluate_factor_student_pilot.py',['--mode','collect'],'evaluation_collect')
save('student_execution.json',dict(complete=True,seconds=time.time()-start))
