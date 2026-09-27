import os,json,hashlib,shutil,subprocess,time,fcntl
from pathlib import Path
r=Path('/media/PM982/onestepfold/c4_s1_precision_crosshost_v1_20260927');ctl=r/'control';ctl.mkdir(exist_ok=False)
lockfile=(ctl/'process.lock').open('w');fcntl.flock(lockfile,fcntl.LOCK_EX|fcntl.LOCK_NB)
def write(n,d):
 p=ctl/n;t=p.with_suffix('.tmp');t.write_text(json.dumps(d,indent=2)+'\n');t.replace(p)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4<<20),b''):h.update(b)
 return h.hexdigest()
write('stage.json',dict(stage='wait_transfer',time=time.time()))
start=time.time()
while not (r/'transfer_complete.json').exists():
 assert time.time()-start<1800,'transfer wait budget';time.sleep(15)
manifest=json.loads((r/'bundle_manifest.json').read_text())
for n,h in manifest['files'].items():assert sha(r/n)==h,n
write('bundle_acceptance.json',dict(complete=True,files=len(manifest['files']),manifest_sha256=sha(r/'bundle_manifest.json')))
source=r/'code_cross_v1';shutil.copytree(r/'code_v1',source)
for name in ('run_c4_s1_crosshost.py','score_c4_s1_crosshost.py','run_c4_s1_precision.py','score_c4_s1_attribution.py'):shutil.copy2(r/name,source/'scripts'/name)
(r/'cross_source_manifest.json').write_text(json.dumps(dict(files={str(p.relative_to(source)):sha(p) for p in source.rglob('*.py')}),indent=2))
rows=json.loads((r/'manifest.json').read_text());l=json.loads((r/'lock.json').read_text())
for g in l['panel_b']:
 p=Path(rows[g]['shard'].replace('/hpc2hdd/home/shuang886/Folding/','/media/PM982/onestepfold/',1));assert p.is_file(),str(p)
env=os.environ.copy()
for key in ('HIP_VISIBLE_DEVICES','CUDA_VISIBLE_DEVICES'):env.pop(key,None)
env.update(PYTHONPATH=str(source/'src'),PROTENIX_ROOT_DIR='/media/PM982/onestepfold/protenix_stage0_pkg/v1_1/runtime',LAYERNORM_TYPE='torch',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',PYTHONUNBUFFERED='1',PYTORCH_ALLOC_CONF='expandable_segments:True',CUBLAS_WORKSPACE_CONFIG=':4096:8')
py='/home/pc/anaconda3/envs/fold/bin/python';command=[py,'-u',str(source/'scripts/run_c4_s1_crosshost.py'),'--root',str(r)]
write('stage.json',dict(stage='preflight',time=time.time()))
with (ctl/'preflight.log').open('w') as log:
 rc=subprocess.call(['timeout','--kill-after=60','1800',*command,'--preflight'],env=env|dict(ROCR_VISIBLE_DEVICES='0'),stdout=log,stderr=subprocess.STDOUT)
write('preflight_exit.json',dict(returncode=rc,time=time.time()));assert rc==0,'preflight failed'
procs=[]
for i in range(8):
 with (ctl/f'worker_{i}.log').open('w') as log:
  p=subprocess.Popen(['timeout','--kill-after=60','5400',*command,'--worker',str(i)],env=env|dict(ROCR_VISIBLE_DEVICES=str(i)),stdout=log,stderr=subprocess.STDOUT)
 procs.append((i,p))
write('launch.json',dict(time=time.time(),workers=[dict(worker=i,pid=p.pid,gcd=i) for i,p in procs],precision=['bf16','fp32'],groups=102,seeds=[103,107,109,113],predictions=2448))
write('stage.json',dict(stage='inference',time=time.time()))
results=[dict(worker=i,returncode=p.wait()) for i,p in procs];write('exit.json',results);assert all(x['returncode']==0 for x in results)
write('stage.json',dict(stage='wait_hpc_scores',time=time.time()));hp='/data/user/shuang886/Folding/c4_s1_attribution_v1_20260927';start=time.time();(r/'hpc_fp32').mkdir()
while True:
 rc=subprocess.call(['rsync','-a',f'hpc3:{hp}/final_precision/acceptance.json',str(r/'hpc_fp32')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 if rc==0:break
 assert time.time()-start<3600,'HPC score wait budget';time.sleep(60)
for i in range(8):
 f=r/f'hpc_fp32/precision_v2_{i}';f.mkdir();subprocess.run(['rsync','-a',f'hpc3:{hp}/precision_v2_{i}/scores.json',str(f)],check=True)
write('stage.json',dict(stage='scoring',time=time.time()))
with (ctl/'scoring.log').open('w') as log:
 rc=subprocess.call(['timeout','3600',py,str(source/'scripts/score_c4_s1_crosshost.py'),'--root',str(r)],env=env|dict(ROCR_VISIBLE_DEVICES=''),stdout=log,stderr=subprocess.STDOUT)
write('pipeline_exit.json',dict(returncode=rc,time=time.time()));assert rc==0
write('stage.json',dict(stage='complete',time=time.time()))
