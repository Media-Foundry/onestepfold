import os,json,subprocess,time,hashlib
from pathlib import Path
r=Path('/media/PM982/onestepfold/scratch_structure_data_v1_20260927');s=r/'scale192';b=r.parent;assets=b/'scratch_structure_inputs_v1_20260927';py='/home/pc/anaconda3/envs/fold/bin/python'
assert not (s/'launch.json').exists()
migration=json.loads((s/'migration.json').read_text());assert migration['complete']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
retained={p.name:sha(p/'prepared.json') for p in (r/'new/examples').iterdir() if (p/'prepared.json').is_file()}
(s/'retained_manifest.json').write_text(json.dumps({'prepared_sha256':retained,'original_source_sha256':sha(r/'code_v1/source_manifest.json')},indent=2)+'\n')
env=dict(os.environ,ROCR_VISIBLE_DEVICES='',HIP_VISIBLE_DEVICES='',CUDA_VISIBLE_DEVICES='',LAYERNORM_TYPE='torch',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',BLIS_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',VECLIB_MAXIMUM_THREADS='1',RAYON_NUM_THREADS='1',TOKENIZERS_PARALLELISM='false',PROTENIX_ROOT_DIR=str(b/'protenix_stage0_pkg/v1_1/runtime'),PYTHONPATH=str(r/'code_v2/src'),PYTHONUNBUFFERED='1')
cpus=sorted(os.sched_getaffinity(0));assert len(cpus)>=192
jobs={'controller_pid':os.getpid(),'workers':[],'started':time.time(),'target_workers':192,'threads_per_worker':1};procs=[]
for i in range(192):
 cmd=['taskset','-c',str(cpus[i]),py,str(r/'code_v2/scripts/prepare_scratch_structure_data.py'),'--base',str(b),'--root',str(r/'new'),'--input-root',str(r/'input'),'--worker',str(i),'--workers','192','--graph',str(assets/'standard_amino_acids.cif'),'--variants',str(assets/'articulation_report.json')]
 f=(r/'new'/f'worker_{i}.log').open('x');p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,env=env);procs.append((i,p,f))
 jobs['workers'].append({'worker':i,'pid':p.pid,'cpu':cpus[i]});(s/'launch.json').write_text(json.dumps(jobs,indent=2)+'\n')
 time.sleep(.15)
results=[]
for i,p,f in procs:
 results.append({'worker':i,'returncode':p.wait()});f.close();(s/'exit.json').write_text(json.dumps(results,indent=2)+'\n')
assert all(x['returncode']==0 for x in results),results
# Resume the existing transfer after its original process exits, preserving all
# successful data and completing any interrupted stream before acceptance.
old=migration['preserved_rsync_pid']
while Path(f'/proc/{old}/cmdline').exists() and Path(f'/proc/{old}/cmdline').read_bytes():time.sleep(10)
cmd=['rsync','-aL','--partial','--partial-dir=.rsync-partial','--info=stats2','hpc3:/data/user/shuang886/Folding/esmc_expansion_data_v1_20260927/examples/',str(r/'examples')+'/']
with (s/'reuse_verify.log').open('x') as f:rc=subprocess.call(cmd,stdout=f,stderr=subprocess.STDOUT)
assert rc==0
with (s/'acceptance.log').open('x') as f:rc=subprocess.call([py,str(r/'code_v2/scripts/accept_scratch_structure_data.py'),'--root',str(r)],stdout=f,stderr=subprocess.STDOUT,env=env)
(s/'pipeline_exit.json').write_text(json.dumps({'returncode':rc,'finished':time.time()})+'\n');assert rc==0
