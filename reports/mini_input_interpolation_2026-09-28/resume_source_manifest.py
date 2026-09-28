import json,hashlib,subprocess,os
from pathlib import Path
r=Path('/media/PM982/onestepfold/mini_input_interpolation_v1_20260928');old=r/'lock.json';lock=json.load(open(old));digest=hashlib.sha256(old.read_bytes()).hexdigest()
old.rename(r/'lock.v1.json');(r/'exit.json').rename(r/'exit.v1.json');(r/'jobs.json').rename(r/'jobs.v1.json')
changes={}
for name,h in lock['source_sha256'].items():
 actual=hashlib.sha256((r/'code'/name).read_bytes()).hexdigest()
 if actual!=h:changes[name]=dict(expected=h,actual=actual)
 lock['source_sha256'][name]=actual
assert set(changes)=={'src/fastglycan/models/soft_sequence_chart.py','scripts/run_input_interpolation.py'},changes
lock['preparation_lock_sha256']=digest;lock['source_manifest_correction']=changes
(r/'lock.json').write_text(json.dumps(lock,indent=2));failed=r/'failed_source_preflight';failed.mkdir()
records=[]
for device,(case,sources) in enumerate((c,s) for c in ['8bzn','control'] for s in ['E','R','C','ERC']):
 label=case+'_'+sources;(r/label).rename(failed/label);(r/(label+'.log')).rename(failed/(label+'.log'))
 env=os.environ.copy();env.update(ROCR_VISIBLE_DEVICES=str(device),OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',PROTENIX_ROOT_DIR='/media/PM982/onestepfold/protenix_stage0_pkg/v1_1/runtime',PYTHONPATH=str(r/'code/src'))
 with open(r/(label+'.log'),'w') as log:
  p=subprocess.Popen(['timeout','1800','/home/pc/anaconda3/envs/fold/bin/python',str(r/'code/scripts/run_input_interpolation.py'),'--root',str(r),'--case',case,'--sources',sources],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 records.append(dict(label=label,pid=p.pid,device=device,exit_code=None))
(r/'jobs.json').write_text(json.dumps(records,indent=2));print(json.dumps(records))
# This controller waits for actual process exit, preserving negative outcomes.
for row in records:
 _,status=os.waitpid(row['pid'],0);row['exit_code']=os.waitstatus_to_exitcode(status);(r/'jobs.json').write_text(json.dumps(records,indent=2))
(r/'exit.json').write_text(json.dumps(dict(complete=True,success=all(x['exit_code']==0 for x in records))))
