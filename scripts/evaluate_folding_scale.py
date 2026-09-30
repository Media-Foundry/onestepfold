#!/usr/bin/env python3
"""Release fixed terminal inference only after the two-arm training audit."""
import argparse
import json
import subprocess
from pathlib import Path

from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.folding_scale import PARENT_SHA256


def prepare_folding_evaluation(root):
    assert not (root/'lock.json').exists(), 'preserve an already locked run'
    train=root.parent/'folding_scale_training_v1_20260930'
    tl=json.loads((train/'lock.json').read_text())
    audit=json.loads((train/'training_audit.json').read_text())
    assert audit['complete'] and audit['validation_not_used'] and audit['same_update_exposure_budget']
    assert audit['lock_sha256']==sha256(train/'lock.json')
    cache=Path(tl['cache']);cl=json.loads((cache/'lock.json').read_text())
    assert sha256(cache/'lock.json')==tl['cache_lock_sha256']
    assert sha256(cache/'artifact_manifest.json')==tl['cache_manifest_sha256']
    assert sha256(cache/'audit.json')==tl['cache_audit_sha256']
    rows=tl['rows'];assert rows==cl['rows'] and len(rows)==455
    original=set(tl['original_train_ids']);training={r['group_id'] for r in rows if r['role']=='train'}
    validation={r['group_id'] for r in rows if r['role']=='validation'}
    assert len(original)==128 and original<=training and len(training)==423 and len(validation)==32
    assert not training&validation and len(training|validation)==len(rows)
    checkpoints=dict(audit['checkpoints'])
    assert set(checkpoints)=={'train128','expanded'}
    checkpoints['retained']=dict(path=tl['initial_checkpoint'],sha256=PARENT_SHA256)
    for cp in checkpoints.values():assert sha256(Path(cp['path']))==cp['sha256']
    prior=Path(tl['cycle'])/'initial_training_lock.json'
    assert sha256(prior)==tl['initial_training_lock_sha256']
    source=Path(tl['source'])
    inputs=dict(cl['input_hashes'])
    inputs.update(json.loads((cache/'artifact_manifest.json').read_text()))
    for p in [train/'lock.json',train/'training_audit.json',cache/'lock.json',cache/'audit.json',cache/'artifact_manifest.json',prior]:
        inputs[str(p)]=sha256(p)
    # Bind the exact GT/identity files independently of reference predictions.
    for row in rows:
        g=row['group_id']
        for p in [source/'chemistry'/g/'mapping.npz',source/'chemistry'/g/'native.pt',source/'data/examples'/g/'gt.npz']:
            assert str(p) in inputs and sha256(p)==inputs[str(p)],str(p)
    for f in ['models/differentiable_mini.py','models/diffusion_adapter.py','models/diffusion_scope.py',
              'models/soft_sequence_chart.py','folding_scale.py','diffusion_pilot_metrics.py']:
        assert sha256(root/'code/src/fastglycan'/f)==sha256(train/'code/src/fastglycan'/f),f
    assignments=[[] for _ in range(8)];loads=[0]*8
    for row in sorted(rows,key=lambda r:(-len(r['sequence']),r['group_id'])):
        index=min(range(8),key=lambda i:(loads[i],i))
        assignments[index].append(row);loads[index]+=len(row['sequence'])**2
    probe=min((r for r in rows if r['group_id'] in original),key=lambda r:(len(r['sequence']),r['group_id']))
    hashes={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.json','.md']}
    assert str(root/'code/docs/connection_reference_bands.json') in hashes
    contracts=json.loads((root/'submission.json').read_text())
    assert contracts['training_jobs']=={'train128':'662290','expanded':'662291'} and contracts['audit_job']=='662294'
    write_json(root/'lock.json',dict(schema='folding_scale_evaluation_v1',train=str(train),cache=str(cache),source=str(source),
        rows=rows,assignments=assignments,estimated_loads=loads,checkpoints=checkpoints,
        checkpoint_training_locks={a:tl['initial_training_lock_sha256'] if a=='retained' else sha256(train/'lock.json') for a in checkpoints},
        checkpoint_arms={'retained':'diffusion_dense'},selected_names={a:tl['selected_names'] for a in checkpoints},
        hashes=hashes,input_hashes=inputs,weights_sha256=cl['weights_sha256'],weight_stats=cl['weight_stats'],
        train_seeds=cl['train_seeds'],validation_seeds=cl['validation_seeds'],probe=probe,
        models=['native_s1','native_s2','retained','train128','expanded'],
        contrasts=[['expanded','train128'],['native_s2','native_s1'],['retained','native_s1']]
            +[[a,b] for a in ['train128','expanded'] for b in ['retained','native_s1','native_s2']],
        cohorts={'original_train128':sorted(original),'added_train295':sorted(training-original),'new_validation32':sorted(validation)},
        bootstrap=dict(replicates=10000,seed=20260930,unit='protein after mean over two noises'),
        primary='new validation32 expanded minus train128 paired AA-lDDT; fixed2048 terminal; no model/seed selection',
        planned_outputs=4550,planned_prediction_nfe=2922,planned_probe_nfe=80,
        protocol_sha256=sha256(root/'code/docs/mini_folding_terminal_evaluation_v1.md')))


def collect_folding_evaluation(root):
    lock=json.loads((root/'lock.json').read_text());submission=json.loads((root/'submission.json').read_text())
    jobs=submission['worker_jobs'];assert len(jobs)==8 and len(set(jobs))==8
    all_jobs=jobs+list(submission['training_jobs'].values())+[submission['audit_job'],submission['prepare_job']]
    raw=subprocess.check_output(['sacct','-j',','.join(all_jobs),'-n','-X','-P','--format=JobIDRaw,State,ExitCode'],text=True)
    states={p[0]:p[1:3] for line in raw.splitlines() if (p:=line.split('|')) and len(p)>=3}
    write_json(root/'scheduler_observation.json',dict(raw=raw,expected=all_jobs))
    assert all(states.get(j)==['COMPLETED','0:0'] for j in all_jobs),states
    workers=[]
    for i,job in enumerate(jobs):
        p=root/f'worker_{i}/report.json';r=json.loads(p.read_text())
        assert r['complete'] and r['lock_sha256']==sha256(root/'lock.json')
        assert [x['group_id'] for x in r['rows']]==[x['group_id'] for x in lock['assignments'][i]]
        workers.append(dict(index=i,job=job,exit_code=0,report_sha256=sha256(p)))
    write_json(root/'execution.json',dict(complete=True,workers=workers,lock_sha256=sha256(root/'lock.json'),
        scheduler_sha256=sha256(root/'scheduler_observation.json')))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--mode',choices=['prepare','collect','cohorts'],required=True);a=p.parse_args()
    if a.mode=='prepare':prepare_folding_evaluation(a.root.resolve())
    elif a.mode=='collect':collect_folding_evaluation(a.root.resolve())
    else:
        from fastglycan.folding_evaluation import summarize_folding_cohorts
        lock=json.loads((a.root/'lock.json').read_text());evaluation=json.loads((a.root/'evaluation.json').read_text())
        assert evaluation['complete'] and evaluation['lock_sha256']==sha256(a.root/'lock.json')
        result=summarize_folding_cohorts(evaluation['records'],lock)
        write_json(a.root/'cohorts.json',dict(complete=True,evaluation_sha256=sha256(a.root/'evaluation.json'),**result))
