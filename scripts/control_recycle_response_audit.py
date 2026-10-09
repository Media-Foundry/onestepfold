"""Six independent read-only shards; first site's replay gates launch the rest."""
import argparse,json,os,subprocess,time,signal
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);root=p.parse_args().root
virtual=Path('/data/user/shuang886/Folding')/root.name
prefix=['/media/IntelSSD/onestepfold/diamondhill_migration_20261001/tools/proot/usr/bin/proot','-b',str(root.parent)+':/data/user/shuang886/Folding','/home/pc/anaconda3/envs/fold/bin/python','-u']
env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',LAYERNORM_TYPE='torch',FASTGLYCAN_AUTHORIZED_HIP_0_5='1',PROTENIX_ROOT_DIR='/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime',PYTHONPATH=str(virtual/'code/src')+':'+str(virtual/'code/scripts'))
assert not any(k in env for k in ('CUDA_VISIBLE_DEVICES','ROCR_VISIBLE_DEVICES','HSA_VISIBLE_DEVICES','GPU_DEVICE_ORDINAL'))
state=dict(complete=False,phase='first_site_replay',jobs={});jobs={};start=time.monotonic();pending=list(range(6))
try:
 while pending or any(p.poll() is None for p,f in jobs.values()):
  if pending and (not jobs or (root/'shard_0.json').exists()):
   shard=pending.pop(0);f=(root/f'worker_{shard}.log').open('w')
   job=subprocess.Popen(prefix+[str(virtual/'code/scripts/run_recycle_response_audit.py'),'--root',str(virtual),'--shard',str(shard)],env=dict(env,HIP_VISIBLE_DEVICES=str(shard)),stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
   jobs[shard]=(job,f);state['jobs'][str(shard)]=dict(pid=job.pid,hip=shard,status='running')
   if shard:state['phase']='diagnostic'
  for shard,(job,f) in jobs.items():
   code=job.poll()
   if code is not None:
    state['jobs'][str(shard)].update(status='complete' if code==0 else 'failed',exit_code=code)
    if code:raise RuntimeError(f'shard{shard} failed:{code}')
  state['seconds']=time.monotonic()-start;(root/'controller.json').write_text(json.dumps(state,indent=2)+'\n')
  if state['seconds']>2700:raise TimeoutError('45minute diagnostic budget')
  time.sleep(3)
 rows=[]
 for shard in range(6):
  d=json.loads((root/f'shard_{shard}.json').read_text());assert d['complete'];rows.extend(d['rows'])
 assert len(rows)==len({r['site'] for r in rows})==48
 (root/'results.json').write_text(json.dumps(dict(complete=True,rows=rows),indent=2)+'\n')
 state.update(complete=True,phase='closed',seconds=time.monotonic()-start)
except BaseException as e:
 state.update(complete=False,phase='failed',error=repr(e))
 for job,f in jobs.values():
  if job.poll() is None:os.killpg(job.pid,signal.SIGTERM)
 raise
finally:
 for job,f in jobs.values():f.close()
 (root/'controller.json').write_text(json.dumps(state,indent=2)+'\n')
