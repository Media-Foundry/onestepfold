#!/usr/bin/env python3
"""DiamondHill controller: lock -> four audits -> gated eight-GCD evaluation."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import hashlib

root=Path(sys.argv[1]).resolve()
(root/'launch.lock').open('x').close()
physical='/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding'
virtual='/data/user/shuang886/Folding/'+root.name
assert root.parent==Path(physical)
prefix=['timeout','1800','/media/IntelSSD/onestepfold/diamondhill_migration_20261001/tools/proot/usr/bin/proot',
        '-b',physical+':/data/user/shuang886/Folding','/home/pc/anaconda3/envs/fold/bin/python','-u']
env=os.environ.copy();env.update(OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',LAYERNORM_TYPE='torch',
    PROTENIX_ROOT_DIR='/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime',
    PYTHONPATH=virtual+'/code/src:'+virtual+'/code/scripts:'+virtual+'/code')
execution=dict(complete=False,controller_pid=os.getpid(),jobs=[],phase='prepare',started=time.time())
processes=[]
def save(): (root/'execution.json').write_text(json.dumps(execution,indent=2)+'\n')
def launch(mode,index=0):
    label=f'{mode}_{index}'
    cmd=prefix+[virtual+'/code/scripts/run_backbone_sequence_pilot.py','--root',virtual,'--mode',mode,'--index',str(index)]
    with (root/(label+'.log')).open('w') as log:
        job=subprocess.Popen(cmd,env=dict(env,HIP_VISIBLE_DEVICES=str(index),CUDA_VISIBLE_DEVICES=str(index)),stdout=log,stderr=subprocess.STDOUT)
    row=dict(mode=mode,index=index,pid=job.pid,command=cmd,started=time.time());execution['jobs'].append(row);processes.append(job);save()
    return job,row
def join(batch):
    for job,row in batch: row.update(exit_code=job.wait(),seconds=time.time()-row['started']);save()
    assert all(row['exit_code']==0 for job,row in batch),'worker execution failure'
try:
    join([launch('prepare')]);lock=json.loads((root/'lock.json').read_text())
    execution['phase']='audit';save();join([launch('audit',i) for i in range(4)])
    reports=[json.loads((root/f'audit_{i}/report.json').read_text()) for i in range(4)]
    execution['audit_gates']=[r.get('gate_passed',False) for r in reports]
    if not all(execution['audit_gates']):
        execution.update(complete=True,success=False,phase='stopped_at_audit',reason='no hard evaluation released')
    else:
        tasks=[];proposals=[];hashes={}
        for i,r in enumerate(reports):
            p=root/f'audit_{i}/candidates.json';digest=hashlib.sha256(p.read_bytes()).hexdigest()
            assert r['complete'] and digest==r['candidate_sha256']
            proposal=json.loads(p.read_text());proposals.append(proposal);hashes[virtual+f'/audit_{i}/candidates.json']=digest
            tasks.extend(dict(parent_index=i,sequence_index=j,sequence=s) for j,s in enumerate(proposal['sequences']))
        assignments=[[] for _ in range(8)];loads=[0]*8
        for t in sorted(tasks,key=lambda t:(-len(t['sequence']),t['parent_index'],t['sequence_index'])):
            i=min(range(8),key=lambda i:(loads[i],i));assignments[i].append(t);loads[i]+=len(t['sequence'])**2
        manifest=dict(lock_sha256=hashlib.sha256((root/'lock.json').read_bytes()).hexdigest(),proposal_hashes=hashes,
            proposals=proposals,assignments=assignments,expected_outputs=3*len(tasks))
        (root/'candidates_lock.json').write_text(json.dumps(manifest,indent=2)+'\n')
        execution['phase']='evaluate';save();join([launch('evaluate',i) for i in range(8)])
        execution['phase']='score';save();join([launch('score')]);execution.update(complete=True,success=True,phase='finished')
except Exception:
    execution.update(complete=True,success=False,phase='execution_failed',error=traceback.format_exc())
finally:
    for job in processes:
        if job.poll() is None:job.terminate()
    execution['seconds']=time.time()-execution['started'];save()
