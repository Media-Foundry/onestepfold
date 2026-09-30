import json,os,subprocess,time
from pathlib import Path
root=Path('/media/PM982/onestepfold/diffusion_learning_pilot_v1_20260930')
assert (root/'lock.json').exists() and not (root/'execution.json').exists()
env=dict(os.environ,PROTENIX_ROOT_DIR=str(root.parent/'protenix_stage0_pkg/v1_1/runtime'),LAYERNORM_TYPE='torch',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONPATH=f'{root}/code/scripts:{root}/code:{root}/code/src:{root.parent}/independent32_v2_20260930/deps_offline')
records=[];processes=[];start=time.time()
for i,arm in enumerate(['gt','gt_s2']):
 log=open(root/f'{arm}.log','w')
 p=subprocess.Popen(['/home/pc/anaconda3/envs/fold/bin/python',str(root/'code/scripts/train_diffusion_learning_pilot.py'),'--root',str(root),'--mode','train','--arm',arm],env=dict(env,ROCR_VISIBLE_DEVICES=str(i)),stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 records.append(dict(arm=arm,gcd=i,pid=p.pid));processes.append(p)
(root/'execution.json').write_text(json.dumps(dict(controller=os.getpid(),started=start,workers=records),indent=2))
for p,r in zip(processes,records):r['exit_code']=p.wait()
(root/'execution.json').write_text(json.dumps(dict(controller=os.getpid(),started=start,workers=records,seconds=time.time()-start,complete=all(r['exit_code']==0 for r in records)),indent=2))
