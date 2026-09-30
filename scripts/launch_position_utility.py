import os,sys,json,subprocess,time
from pathlib import Path
root=Path(sys.argv[1]).resolve();(root/'launch.lock').open('x').close();python='/home/pc/anaconda3/envs/fold/bin/python'
base=os.environ.copy();base.update(PROTENIX_ROOT_DIR='/media/PM982/onestepfold/protenix_stage0_pkg/v1_1/runtime',LAYERNORM_TYPE='torch',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONPATH=f'{root}/code/scripts:{root}/code/src:/media/PM982/onestepfold/independent32_v2_20260930/deps_offline')
sys.path.insert(0,str(root/'code/src'))
from fastglycan.paired_teacher_protocol import sha256,write_json
lock=json.loads((root/'lock.json').read_text())
for path,digest in lock['weights_sha256'].items():assert sha256(Path(path))==digest
execution=dict(pid=os.getpid(),complete=False,started=time.time(),phase='propose',workers=[]);write_json(root/'execution.json',execution)
for mode,count in [('propose',4),('evaluate',8)]:
 jobs=[];execution['phase']=mode;execution['workers']=[];phase=time.time()
 for i in range(count):
  env=base|{'ROCR_VISIBLE_DEVICES':str(i)};log=open(root/f'{mode}_{i}.log','w')
  job=subprocess.Popen([python,str(root/'code/scripts/run_position_utility.py'),'--root',str(root),'--mode',mode,'--worker',str(i)],env=env,stdout=log,stderr=subprocess.STDOUT);log.close();jobs.append(job)
  execution['workers'].append(dict(mode=mode,worker=i,pid=job.pid));write_json(root/'execution.json',execution)
 for row,job in zip(execution['workers'],jobs):row['exit_code']=job.wait();write_json(root/'execution.json',execution)
 execution[mode+'_seconds']=time.time()-phase;write_json(root/(mode+'_execution.json'),execution)
 if any(r['exit_code'] for r in execution['workers']):execution.update(complete=True,success=False);write_json(root/'execution.json',execution);raise SystemExit(1)
 if mode=='propose':
  if root.name=='position_utility_chain_v1_20260930':
   import torch
   original=root.parent/'position_utility_v1_20260930';replays=[]
   for j in [1,3]:
    first=torch.load(original/f'proposal_{j}/gradient.pt',map_location='cpu',weights_only=False)
    second=torch.load(root/f'proposal_{j}/gradient.pt',map_location='cpu',weights_only=False)
    equal={k:torch.equal(first[k],second[k]) for k in ['q','p','gp','gq','coordinates']}
    assert all(equal.values()),equal
    x=json.loads((original/f'proposal_{j}/candidates.json').read_text());y=json.loads((root/f'proposal_{j}/candidates.json').read_text())
    assert x['arms']==y['arms'] and x['position_scores']==y['position_scores']
    replays.append(dict(parent_index=j,exact=equal,candidates_equal=True))
   write_json(root/'engineering_replay.json',replays)
  hashes={};tasks=[];proposals=[]
  for i in range(4):
   folder=root/f'proposal_{i}';report=json.loads((folder/'report.json').read_text());assert report['complete'] and report['proposal_sha256']==sha256(folder/'candidates.json')
   p=json.loads((folder/'candidates.json').read_text());assert p['parent']==lock['rows'][i]['sequence'];proposals.append(p);hashes[str(folder/'candidates.json')]=sha256(folder/'candidates.json')
   tasks.extend(dict(parent_index=i,sequence_index=j,sequence=s) for j,s in enumerate(p['sequences']))
  assignments=[[] for _ in range(8)];loads=[0]*8
  for t in sorted(tasks,key=lambda t:(-len(t['sequence']),t['parent_index'],t['sequence_index'])):
   k=min(range(8),key=lambda j:(loads[j],j));assignments[k].append(t);loads[k]+=len(t['sequence'])**2
  write_json(root/'candidates_lock.json',dict(lock_sha256=sha256(root/'lock.json'),proposal_hashes=hashes,proposals=proposals,assignments=assignments,total_sequences=len(tasks),expected_outputs=3*len(tasks)))
execution.update(complete=True,success=True,phase='finished',seconds=time.time()-execution['started']);write_json(root/'execution.json',execution)
