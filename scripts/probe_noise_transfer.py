#!/usr/bin/env python3
"""Prepare and score a bounded held-noise transfer experiment on existing TRAIN proteins."""
import argparse
import json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.noise_transfer import make_noise_transfer_lock,summarize_noise_transfer
from fastglycan.folding_scale import PARENT_SHA256


def prepare_noise_transfer(root):
    import torch
    assert not (root/'lock.json').exists()
    previous=root.parent/'rocm_matched_evaluation_v1_20261001'
    prior=json.loads((previous/'lock.json').read_text());train=Path(prior['train'])/'weak'
    tl=json.loads((train/'lock.json').read_text())
    parent=Path(tl['initial_checkpoint']);assert sha256(parent)==PARENT_SHA256
    state=torch.load(parent,map_location='cpu',weights_only=False)
    assert state['schema']=='native_dense_diffusion_v1' and state['update']==512
    audit=json.loads((train.parent/'terminal_audit.json').read_text());assert audit['complete']
    assert audit['checkpoints']['weak']==prior['checkpoints']['weak']
    groups=set(tl['probe_groups'])|{prior['probe']['group_id']}
    inputs={p:h for p,h in prior['input_hashes'].items() if any(g in p for g in groups)}
    for p,h in inputs.items():assert sha256(Path(p))==h
    for p in [previous/'lock.json',train/'lock.json',train.parent/'terminal_audit.json',parent]:inputs[str(p)]=sha256(p)
    for f in ['evaluate_diffusion_learning.py','score_diffusion_learning.py']:
        assert sha256(root/'code/scripts'/f)==sha256(previous/'code/scripts'/f)
    hashes={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.md','.json']}
    lock=make_noise_transfer_lock(prior,tl,parent=dict(path=str(parent),sha256=PARENT_SHA256),
        parent_lock=state['lock_sha256'],hashes=hashes,input_hashes=inputs)
    lock['previous']=str(previous);lock['protocol_sha256']=sha256(root/'code/docs/mini_noise_transfer_v1.md')
    write_json(root/'lock.json',lock)


def score_noise_transfer(root):
    from score_diffusion_learning import score_diffusion_case
    lock=json.loads((root/'lock.json').read_text());execution=json.loads((root/'inference_execution.json').read_text())
    assert execution['complete'] and all(j['exit_code']==0 for j in execution['jobs'])
    assert sorted(j['index'] for j in execution['jobs'])==list(range(8))
    assert execution['lock_sha256']==sha256(root/'lock.json')
    for p,h in lock['hashes'].items():assert sha256(Path(p))==h
    seen=[]
    for i,assignment in enumerate(lock['assignments']):
        p=root/f'worker_{i}/report.json';report=json.loads(p.read_text())
        assert report['complete'] and report['lock_sha256']==sha256(root/'lock.json')
        assert report['calls']==dict(native=0,retained=6*len(assignment),weak=6*len(assignment))
        assert report['probe_nfe']==7 and all(all(x.values()) for x in report['probe'].values())
        assert [r['group_id'] for r in report['rows']]==[r['group_id'] for r in assignment]
        for row in report['rows']:
            g=row['group_id'];seen.append(g);assert json.loads((root/'examples'/g/'report.json').read_text())==row
            for e in row['entries']:assert sha256(root/'examples'/g/e['name'])==e['sha256']
            for seed in lock['noise_sets']['seen']:
                old=Path(lock['previous'])/'examples'/g/f'weak_seed{seed}.npy'
                assert sha256(old)==sha256(root/'examples'/g/f'weak_seed{seed}.npy')
    assert len(seen)==len(set(seen))==32
    with ProcessPoolExecutor(max_workers=8) as pool:
        results=list(pool.map(score_diffusion_case,[(str(root),r) for r in lock['rows']]))
    assert all(r['complete'] for r in results)
    records=[x for r in results for x in r['records']]
    report=summarize_noise_transfer(records,lock)
    report.update(records=records,lock_sha256=sha256(root/'lock.json'),seen_weak_exact=64,
        metric_max_abs=max(r['metric_max_abs'] for r in results),prediction_nfe=384,engineering_nfe=56)
    write_json(root/'report.json',report)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--mode',choices=['prepare','score'],required=True)
    a=p.parse_args()
    if a.mode=='prepare':prepare_noise_transfer(a.root)
    else:score_noise_transfer(a.root)
