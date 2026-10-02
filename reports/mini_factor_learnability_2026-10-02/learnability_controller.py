import os,subprocess,time,json,signal,hashlib
from pathlib import Path
base=Path('/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding');root=base/'factor_learnability_v1_20261002';v=Path('/data/user/shuang886/Folding')/root.name
old=base/'factor_student_pilot_v1_20261002';oldv=v.parent/old.name
py='/home/pc/anaconda3/envs/fold/bin/python';proot='/media/IntelSSD/onestepfold/diamondhill_migration_20261001/tools/proot/usr/bin/proot'
env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',LAYERNORM_TYPE='torch',PROTENIX_ROOT_DIR='/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime',PYTHONPATH=f'{v}/code/src:{v}/code/scripts')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,d):(root/n).write_text(json.dumps(d,indent=2)+'\n')
def load(p):return json.loads(p.read_text())
def cmd(script,args,sparse=False):return [proot,'-b',str(base)+':/data/user/shuang886/Folding',py,'-u',str(v/'code/scripts'/script),'--root',str(v/'sparse' if sparse else v)]+args
def single(script,args,label,sparse=False):
 with open(root/f'{label}.log','w') as f:p=subprocess.run(cmd(script,args,sparse),env=dict(env,HIP_VISIBLE_DEVICES='',CUDA_VISIBLE_DEVICES=''),stdout=f,stderr=subprocess.STDOUT,timeout=900)
 if p.returncode:raise RuntimeError((label,p.returncode))
def phase(script,args,n,label,gpu=True,sparse=False):
 ps=[];start=time.time()
 for i in range(n):
  f=open(root/f'{label}_{i}.log','w');ps.append(subprocess.Popen(cmd(script,args+['--index',str(i)],sparse),env=dict(env,HIP_VISIBLE_DEVICES=str(i) if gpu else '',CUDA_VISIBLE_DEVICES=str(i) if gpu else ''),stdout=f,stderr=subprocess.STDOUT,start_new_session=True))
 save(label+'_handles.json',dict(started=start,pids=[p.pid for p in ps]))
 while any(p.poll() is None for p in ps):
  if time.time()-start>1800:
   for p in ps:
    if p.poll() is None:os.killpg(p.pid,signal.SIGTERM)
   break
  time.sleep(5)
 exits=[p.wait() for p in ps];save(label+'_execution.json',dict(complete=not any(exits),exits=exits,seconds=time.time()-start))
 if any(exits):raise RuntimeError((label,exits))
start=time.time()
try:
 teacher=load(old/'teacher_lock.json');train=[r for r in teacher['rows'] if r['role']=='train'];val=[r for r in teacher['rows'] if r['role']=='validation']
 stages=[[[train[0]['index'],train[0]['positions'][0]]],[[train[0]['index'],p] for p in train[0]['positions']],[[r['index'],p] for r in train[:4] for p in r['positions']],[[r['index'],p] for r in train for p in r['positions']]]
 code={str(v/'code'/p.relative_to(root/'code')):sha(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.md','.json']}
 lock=dict(schema='factor_learnability_v1',teachers=str(oldv),teacher_lock_sha256=sha(old/'teacher_lock.json'),teacher_manifest_sha256=sha(old/'teacher_manifest.json'),code_hashes=code,rank=32,gap_tolerance=.01,init_seeds=[231301,231303],updates=512,lr=3e-4,weight_decay=1e-4,free_lr=.01,clip=1.,advance_nmse=.1,stages=stages)
 assert not (root/'lock.json').exists();save('lock.json',lock)
 sparse=root/'sparse';sparse.mkdir();assign=[[r['index']] for r in val];scores=[[dict(parent_index=r['index'],position=p,worker=i) for p in r['positions']] for i,r in enumerate(val)]
 prior_hash={}
 for report in (old/'evaluation').glob('worker_*/report.json'):
  for parent in load(report)['parents']:
   if parent['parent_index'] in [r['index'] for r in val]:
    for site in parent['sites']:
     for m in site['mutants']:prior_hash[str(oldv/'evaluation'/report.parent.name/(m['label']+'_coordinates.npz'))]=m['coordinate_sha256']
 save('sparse/lock.json',dict(teacher,teachers=str(oldv),schema='sparse_factor_oracle_v1',code_hashes=code,teacher_lock_sha256=sha(old/'teacher_lock.json'),assignments=assign,score_assignments=scores,rank=32,contact_radius=8.,prior_coordinate_hashes=prior_hash,arms=['exact','baseline','oracle_r32','rowcol','contact','top_row_budget','top_contact_budget'],expected_nfe=4272,expected_c4=0))
 for stage in range(4):
  phase('run_factor_memorization.py',['--stage',str(stage)],6 if stage==0 else 4,f'memory_{stage}')
  single('run_factor_memorization.py',['--mode','gate','--stage',str(stage)],f'gate_{stage}')
  if not load(root/f'ladder_gate_{stage}.json')['advance']:break
 save('memory_execution.json',dict(complete=True,last_stage=stage,seconds=time.time()-start))
 phase('run_sparse_factor_oracle.py',['--mode','run'],8,'sparse_gpu',sparse=True)
 phase('run_sparse_factor_oracle.py',['--mode','score'],8,'sparse_score',gpu=False,sparse=True)
 single('run_sparse_factor_oracle.py',['--mode','collect'],'sparse_collect',sparse=True)
 save('execution.json',dict(complete=True,seconds=time.time()-start))
except Exception as e:
 save('execution.json',dict(complete=False,error=repr(e),seconds=time.time()-start));raise
