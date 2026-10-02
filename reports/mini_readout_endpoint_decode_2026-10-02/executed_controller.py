from pathlib import Path
import os,subprocess,json,time
r=Path('/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/readout_endpoint_decode_v1_20261002');v=Path('/data/user/shuang886/Folding')/r.name
start=time.monotonic();records=[]
env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',LAYERNORM_TYPE='torch',PROTENIX_ROOT_DIR='/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime',PYTHONPATH=f'{v}/code/src:{v}/code/scripts')
for key in ['CUDA_VISIBLE_DEVICES','ROCR_VISIBLE_DEVICES','GPU_DEVICE_ORDINAL','HSA_VISIBLE_DEVICES']:env.pop(key,None)
base=['/media/IntelSSD/onestepfold/diamondhill_migration_20261001/tools/proot/usr/bin/proot','-b',str(r.parent)+':/data/user/shuang886/Folding','/home/pc/anaconda3/envs/fold/bin/python','-u',str(v/'code/scripts/run_readout_endpoint_decode.py'),'--root',str(v)]
def save(complete=False,error=None):
 (r/'execution.json').write_text(json.dumps(dict(complete=complete,error=error,stages=records,seconds=time.monotonic()-start,pid=os.getpid()),indent=2))
try:
 for mode,index in [('prepare',0),('decode',0),*[( 'score',i) for i in range(6)],('collect',0),('audit',0)]:
  env['HIP_VISIBLE_DEVICES']='0' if mode=='decode' else '';t=time.monotonic();records.append(dict(mode=mode,index=index,complete=False));save()
  with (r/f'{mode}_{index}.log').open('w') as f:
   p=subprocess.run(base+['--mode',mode,'--index',str(index)],env=env,stdout=f,stderr=subprocess.STDOUT,timeout=3600)
  records[-1].update(complete=p.returncode==0,returncode=p.returncode,seconds=time.monotonic()-t);save();assert p.returncode==0,(mode,index,p.returncode)
 save(True)
except Exception as e:
 save(False,repr(e));raise
