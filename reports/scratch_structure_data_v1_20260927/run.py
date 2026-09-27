import hashlib,json,os,subprocess,time
from pathlib import Path
r=Path('/media/PM982/onestepfold/scratch_structure_data_v1_20260927');b=r.parent;assets=b/'scratch_structure_inputs_v1_20260927';py='/home/pc/anaconda3/envs/fold/bin/python'
assert not (r/'launch.json').exists()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source={'files':{str(p.relative_to(r/'code_v1')):sha(p) for p in (r/'code_v1').rglob('*.py')}}
(r/'code_v1/source_manifest.json').write_text(json.dumps(source,indent=2)+'\n')
for name in ['inputs.pt','gt.npz','gt.json']:
 assert name
# Verify every requested source exists before any expensive preparation.
rows=json.loads((r/'new/selection.json').read_text())
missing=[]
for x in rows:
 for p in [b/'processed_stageb_v1/shards'/Path(x['shard']).name,b/'Dataset/raw/pdb_mmcif'/x['pdb_id'][1:3]/(x['pdb_id']+'.cif.gz')]:
  if not p.is_file():missing.append(str(p))
(r/'source_preflight.json').write_text(json.dumps({'complete':not missing,'missing':sorted(set(missing)),'new_groups':len(rows)},indent=2)+'\n')
assert not missing
# Verify existing final-layer cache shards once; workers also verify loaded slices.
import gzip
with gzip.open(b/'esmc_600m_final_v1/manifest.jsonl.gz','rt') as f:cache=list(map(json.loads,f))
bygroup={x['group_id']:x for x in cache};hashes={x['shard']:x['shard_sha256'] for x in cache}
for x in rows:assert bygroup[x['group_id']]['sequence_length']==len(x['sequence'])
# Hash verification runs concurrently with the independent packet smoke.
env=dict(os.environ,ROCR_VISIBLE_DEVICES='',HIP_VISIBLE_DEVICES='',CUDA_VISIBLE_DEVICES='',LAYERNORM_TYPE='torch',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',PROTENIX_ROOT_DIR=str(b/'protenix_stage0_pkg/v1_1/runtime'),PYTHONPATH=str(r/'code_v1/src'),PYTHONUNBUFFERED='1')
rsync=['rsync','-aL','--partial','--partial-dir=.rsync-partial','--info=stats2','hpc3:/data/user/shuang886/Folding/esmc_expansion_data_v1_20260927/examples/',str(r/'examples')+'/']
f=(r/'reuse_transfer.log').open('x');transfer=subprocess.Popen(rsync,stdout=f,stderr=subprocess.STDOUT)
records={'controller_pid':os.getpid(),'started':time.time(),'reuse_transfer_pid':transfer.pid,'workers':[]}
(r/'launch.json').write_text(json.dumps(records,indent=2)+'\n')
def batch(kind,count):
 procs=[]
 for i in range(count):
  cmd=[py,str(r/'code_v1/scripts/prepare_scratch_structure_data.py'),'--base',str(b),'--root',str(r/kind),'--input-root',str(r/'input'),'--worker',str(i),'--workers',str(count),'--graph',str(assets/'standard_amino_acids.cif'),'--variants',str(assets/'articulation_report.json')]
  log=(r/kind/f'worker_{i}.log').open('x');p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=env);procs.append((i,p,log))
  records['workers'].append({'kind':kind,'worker':i,'pid':p.pid});(r/'launch.json').write_text(json.dumps(records,indent=2)+'\n')
 result=[]
 for i,p,log in procs:result.append({'worker':i,'returncode':p.wait()});log.close()
 (r/kind/'exit.json').write_text(json.dumps(result,indent=2)+'\n');assert all(x['returncode']==0 for x in result),result
batch('smoke',2)
for row in json.loads((r/'smoke/selection.json').read_text()):
 (r/'new/examples'/row['group_id']).symlink_to(r/'smoke/examples'/row['group_id'])
for n,h in hashes.items():assert sha(b/'esmc_600m_final_v1'/n)==h,n
(r/'esmc_cache_acceptance.json').write_text(json.dumps({'complete':True,'shards':len(hashes),'manifest_sha256':sha(b/'esmc_600m_final_v1/manifest.jsonl.gz')})+'\n')
batch('new',16)
rc=transfer.wait();f.close();(r/'reuse_transfer_exit.json').write_text(json.dumps({'returncode':rc})+'\n');assert rc==0
with (r/'acceptance.log').open('x') as log:rc=subprocess.call([py,str(r/'code_v1/scripts/accept_scratch_structure_data.py'),'--root',str(r)],env=env,stdout=log,stderr=subprocess.STDOUT)
(r/'pipeline_exit.json').write_text(json.dumps({'returncode':rc,'finished':time.time()})+'\n');assert rc==0
