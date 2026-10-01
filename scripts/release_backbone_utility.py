#!/usr/bin/env python3
"""Apply disclosed post-audit v1a release; never relabel the original v1 gate."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

root=Path(sys.argv[1]).resolve();(root/'utility_release.lock').open('x').close()
physical='/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding'
virtual='/data/user/shuang886/Folding/'+root.name
assert root.parent==Path(physical)
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
original=json.loads((root/'execution.json').read_text())
assert original['complete'] and original['phase']=='stopped_at_audit'
assert not list(root.glob('evaluate_*')) and not (root/'candidates_lock.json').exists()
lock=json.loads((root/'lock.json').read_text());proposals=[];hashes={};tasks=[];audits={}
for i in range(4):
    folder=root/f'audit_{i}';r=json.loads((folder/'report.json').read_text())
    assert r['complete'] and r['hard_parity_exact'] and r['near_nonregression']
    assert all(r['repeat_exact'].values()) and r['chain_audit']['local_softmax_vjp_exact'] and r['parameter_gradients_absent']
    v=r['full_logits_vjp'];assert min(v['actual_norm'],v['reference_norm'])>1e-10 and v['relative_l2_error']<=.01
    assert r['reference_primal']['max_absolute_error']<=.001
    assert len(r['directions'])==3
    for d in r['directions']:
        for key in ['native','reference']:
            c=d[key];assert min(abs(c['left']),abs(c['right']))>0 and c['relative_error']<=.05
    p=folder/'candidates.json';assert digest(p)==r['candidate_sha256']
    proposal=json.loads(p.read_text());proposals.append(proposal);hashes[virtual+f'/audit_{i}/candidates.json']=digest(p)
    audits[str(folder/'report.json')]=digest(folder/'report.json')
    tasks.extend(dict(parent_index=i,sequence_index=j,sequence=s) for j,s in enumerate(proposal['sequences']))
assignments=[[] for _ in range(8)];loads=[0]*8
for t in sorted(tasks,key=lambda t:(-len(t['sequence']),t['parent_index'],t['sequence_index'])):
    i=min(range(8),key=lambda i:(loads[i],i));assignments[i].append(t);loads[i]+=len(t['sequence'])**2
manifest=dict(lock_sha256=digest(root/'lock.json'),proposal_hashes=hashes,proposals=proposals,assignments=assignments,expected_outputs=3*len(tasks))
(root/'candidates_lock.json').write_text(json.dumps(manifest,indent=2)+'\n')
release=dict(post_audit_amendment=True,original_execution_sha256=digest(root/'execution.json'),
    original_gates=original['audit_gates'],audit_report_sha256=audits,
    amendment_sha256=digest(root/'mini_backbone_sequence_release_v1a.md'),candidate_lock_sha256=digest(root/'candidates_lock.json'),
    hard_evaluation_started=False,release_rule='all original directions relative-only plus complete nonzero VJP and unchanged other gates')
(root/'utility_release_v1a.json').write_text(json.dumps(release,indent=2)+'\n')
prefix=['timeout','1800','/media/IntelSSD/onestepfold/diamondhill_migration_20261001/tools/proot/usr/bin/proot',
        '-b',physical+':/data/user/shuang886/Folding','/home/pc/anaconda3/envs/fold/bin/python','-u']
env=os.environ.copy();env.update(OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',LAYERNORM_TYPE='torch',
    PROTENIX_ROOT_DIR='/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime',
    PYTHONPATH=virtual+'/code/src:'+virtual+'/code/scripts:'+virtual+'/code')
execution=dict(complete=False,controller_pid=os.getpid(),jobs=[],phase='evaluate',started=time.time());processes=[]
def save(): (root/'utility_execution.json').write_text(json.dumps(execution,indent=2)+'\n')
def launch(mode,index):
    cmd=prefix+[virtual+'/code/scripts/run_backbone_sequence_pilot.py','--root',virtual,'--mode',mode,'--index',str(index)]
    with (root/f'{mode}_{index}.log').open('w') as log:
        job=subprocess.Popen(cmd,env=dict(env,HIP_VISIBLE_DEVICES=str(index),CUDA_VISIBLE_DEVICES=str(index)),stdout=log,stderr=subprocess.STDOUT)
    row=dict(mode=mode,index=index,pid=job.pid,started=time.time());execution['jobs'].append(row);processes.append(job);save();return job,row
def join(batch):
    for job,row in batch: row.update(exit_code=job.wait(),seconds=time.time()-row['started']);save()
    assert all(row['exit_code']==0 for job,row in batch),'utility worker execution failure'
try:
    join([launch('evaluate',i) for i in range(8)])
    execution['phase']='score';save();join([launch('score',0)])
    execution.update(complete=True,success=True,phase='finished')
except Exception:execution.update(complete=True,success=False,error=traceback.format_exc())
finally:
    for job in processes:
        if job.poll() is None:job.terminate()
    execution['seconds']=time.time()-execution['started'];save()
