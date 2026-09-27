import os,json,subprocess,time,hashlib
from pathlib import Path
r=Path('/media/990Pro/onestepfold/esmc_29769_20260927');assert not (r/'launch_precision.json').exists()
assert subprocess.check_output(['git','-C',str(r/'vendor/esm'),'rev-parse','HEAD'],text=True).strip()=='bf343ba264b650dff7a073643725f9aaa1fdbe8d'
blob=r/'hf_cache/hub/models--biohub--ESMC-600M/blobs/526573c304b7718f9cfd2a8adf79638feb6752eb38056968bf21d9036b7882ce'
h=hashlib.sha256()
with blob.open('rb') as f:
 for block in iter(lambda:f.read(1<<20),b''):h.update(block)
assert h.hexdigest()==blob.name
records=[]
for part,device in [(1,0),(2,1)]:
 env=dict(os.environ,HF_HOME=str(r/'hf_cache'),HF_HUB_OFFLINE='1',PYTHONPATH=str(r/'vendor/esm')+':'+str(r/'code/src')+':'+str(r/'code/scripts'),ROCR_VISIBLE_DEVICES=str(device),OMP_NUM_THREADS='4',PYTHONUNBUFFERED='1')
 cmd=['/home/husrcf/anaconda3/envs/BIO/bin/python',str(r/'code/scripts/run_esmc_29769_partition.py'),'--root',str(r),'--partition',str(part)]
 with (r/f'part-{part:03d}.log').open('x') as f:p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,env=env,start_new_session=True)
 records.append({'pid':p.pid,'partition':part,'device':device,'started':time.time(),'command':cmd})
 (r/'launch_precision.json').write_text(json.dumps(records,indent=2)+'\n')
print(json.dumps(records))
