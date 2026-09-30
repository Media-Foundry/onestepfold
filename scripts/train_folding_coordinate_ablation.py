#!/usr/bin/env python3
"""Prepare, preflight and run one matched loss ablation using the frozen trainer."""
import argparse
import collections
import json
import math
import os
from pathlib import Path
import time

import numpy as np
import torch
from fastglycan.folding_ablation import (
    CONTROL_LOCK_SHA256, CONTROL_TERMINAL_SHA256,
    make_coordinate_ablation_lock, verify_coordinate_ablation_lock,
)
from fastglycan.folding_scale import PARENT_SHA256
from fastglycan.paired_teacher_protocol import sha256, write_json
from train_folding_scale import run_folding_training


def prepare_coordinate_ablation(root, control, evaluation):
    assert not (root/'lock.json').exists()
    old=json.loads((control/'lock.json').read_text())
    assert sha256(control/'lock.json')==CONTROL_LOCK_SHA256
    audit=json.loads((control/'training_audit.json').read_text())
    assert audit['complete'] and audit['checkpoints']['expanded']['sha256']==CONTROL_TERMINAL_SHA256
    assert sha256(control/'expanded/update_2048.pt')==CONTROL_TERMINAL_SHA256
    assert sha256(Path(old['initial_checkpoint']))==PARENT_SHA256
    execution=json.loads((evaluation/'execution.json').read_text())
    assert execution['complete'] and all(w['exit_code']==0 for w in execution['workers'])
    el=json.loads((evaluation/'lock.json').read_text())
    assert sha256(evaluation/'lock.json')==execution['lock_sha256']
    copied={}
    for path,digest in old['hashes'].items():
        original=Path(path);new=root/'code'/original.relative_to(control/'code')
        assert sha256(original)==sha256(new)==digest,original
        copied[str(new)]=digest
    references={}
    for g in old['engineering_groups']:
        p=evaluation/'examples'/g/'report.json';r=json.loads(p.read_text())
        assert r['lock_sha256']==execution['lock_sha256']
        entry,=[x for x in r['entries'] if x['model']=='retained' and x['seed']==old['training_seeds'][0]]
        coordinate=p.parent/entry['name'];assert sha256(coordinate)==entry['sha256']
        references[g]=dict(path=str(coordinate),sha256=entry['sha256'],report_sha256=sha256(p))
    hashes={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.json','.md']}
    protocol=root/'code/docs/mini_folding_coordinate_ablation_v1.md'
    provenance=dict(control=str(control),control_lock_sha256=CONTROL_LOCK_SHA256,
        control_audit_sha256=sha256(control/'training_audit.json'),control_terminal_sha256=CONTROL_TERMINAL_SHA256,
        control_preflight_sha256=sha256(control/'preflight/report.json'),evaluation=str(evaluation),
        evaluation_lock_sha256=sha256(evaluation/'lock.json'),evaluation_execution_sha256=sha256(evaluation/'execution.json'),
        retained_engineering_coordinates=references,original_code_identical=copied,
        preflight_comparison=dict(loss_atol=1e-8,loss_rtol=1e-6,coordinate_max_abs=old['coordinate_replay_bound']),
        semantic_candidate_name='coordinate_zero',checkpoint_arm='expanded',
        validation_role='previously observed development validation; not new independent confirmation')
    lock=make_coordinate_ablation_lock(old,protocol_sha256=sha256(protocol),script_sha256=sha256(Path(__file__)),hashes=hashes,provenance=provenance)
    write_json(root/'lock.json',lock)
    write_json(root/'prepare.json',dict(complete=True,lock_sha256=sha256(root/'lock.json'),
        identical_original_code_files=len(copied),only_scientific_change='coordinate weight .01 to 0'))


def run_coordinate_ablation(root, mode):
    lock=json.loads((root/'lock.json').read_text());meta=lock['ablation'];control=Path(meta['control'])
    assert sha256(control/'lock.json')==CONTROL_LOCK_SHA256
    original=json.loads((control/'lock.json').read_text());verify_coordinate_ablation_lock(lock,original)
    assert sha256(control/'training_audit.json')==meta['control_audit_sha256']
    assert sha256(control/'preflight/report.json')==meta['control_preflight_sha256']
    assert Path(os.environ['PROTENIX_ROOT_DIR']).resolve()==root.parent/'protenix_stage0_pkg/v1_1/runtime'
    assert os.environ.get('LAYERNORM_TYPE')=='torch'
    if mode=='train':
        release=json.loads((root/'release.json').read_text())
        assert release['objective_preflight_sha256']==sha256(root/'objective_preflight.json')
        assert json.loads((root/'objective_preflight.json').read_text())['complete']
        run_folding_training(root,'train','expanded')
        return
    assert mode=='preflight'
    import fastglycan.adapter_supervision as supervision
    original_loss=supervision.adapter_loss_parts
    previous=json.loads((control/'preflight/report.json').read_text())
    previous_cases={r['group_id']:r for r in previous['cases']}
    checks=[]

    def checked_loss(x, labels, teacher, **kwargs):
        g=lock['engineering_groups'][len(checks)]
        parts=original_loss(x,labels,teacher,**kwargs)
        with torch.no_grad():
            again=original_loss(x.detach(),labels,teacher,**kwargs)
            assert parts.keys()==again.keys() and all(torch.equal(parts[k],again[k]) for k in parts)
            base=sum(original['weights'][k]*v for k,v in again.items())
            candidate=sum(lock['weights'][k]*v for k,v in again.items())
            settings=meta['preflight_comparison']
            assert math.isclose(float(base),previous_cases[g]['loss'],rel_tol=settings['loss_rtol'],abs_tol=settings['loss_atol'])
            assert math.isclose(float(base-candidate),float(.01*again['coordinate']),rel_tol=settings['loss_rtol'],abs_tol=settings['loss_atol'])
            ref=meta['retained_engineering_coordinates'][g];assert sha256(Path(ref['path']))==ref['sha256']
            delta=float(np.max(np.abs(x.detach().cpu().numpy()-np.load(ref['path']))))
            assert delta<=settings['coordinate_max_abs']
        checks.append(dict(group_id=g,control_total=float(base),candidate_total=float(candidate),
            removed_coordinate=float(.01*again['coordinate']),parts_identical=True,
            retained_forward_max_abs=delta,parts={k:float(v.detach()) for k,v in parts.items()}))
        return parts

    # A preflight-only observer: the returned loss terms and training implementation are unchanged.
    supervision.adapter_loss_parts=checked_loss
    try:
        run_folding_training(root,'preflight',None)
    finally:
        supervision.adapter_loss_parts=original_loss
    preflight=json.loads((root/'preflight/report.json').read_text())
    assert len(checks)==2 and preflight['complete'] and 'H100' in preflight['device']
    assert preflight['initial_sha256']==previous['initial_sha256']
    write_json(root/'objective_preflight.json',dict(complete=True,cases=checks,parameter_updates=0,
        lock_sha256=sha256(root/'lock.json'),same_parent_fingerprint=True,original_loss_function_restored=True))
    write_json(root/'release.json',dict(lock_sha256=sha256(root/'lock.json'),
        preflight_sha256=sha256(root/'preflight/report.json'),objective_preflight_sha256=sha256(root/'objective_preflight.json'),
        arms=['expanded'],updates_each=2048,validation_during_training=False))


def audit_coordinate_ablation(root):
    torch.set_num_threads(1)
    lock=json.loads((root/'lock.json').read_text());control=Path(lock['ablation']['control'])
    assert sha256(control/'lock.json')==CONTROL_LOCK_SHA256
    old=json.loads((control/'lock.json').read_text());verify_coordinate_ablation_lock(lock,old)
    for p,d in lock['hashes'].items():assert sha256(Path(p))==d
    folder=root/'expanded';report=json.loads((folder/'report.json').read_text())
    assert report['complete'] and report['updates']==2048 and report['exposures']==8192
    assert report['lock_sha256']==sha256(root/'lock.json') and not report['validation_read']
    assert report['excluded_parameters_unchanged'] and report['counts']==dict(pairformer=0,diffusion=8448)
    original_report=json.loads((control/'expanded/report.json').read_text())
    assert report['initial_sha256']==sha256(folder/'initial_fingerprints.json')==original_report['initial_sha256']
    assert sha256(folder/'history.jsonl')==report['history_sha256']
    history=[json.loads(line) for line in (folder/'history.jsonl').read_text().splitlines()]
    assert len(history)==8192;counts=collections.Counter()
    for i,(x,y) in enumerate(zip(history,old['orders']['expanded']),1):
        assert x['exposure']==i and all(x[k]==y[k] for k in ['group_id','epoch','seed']);counts[x['group_id']]+=1
        assert set(x['parts'])==set(lock['weights']) and all(math.isfinite(v) for v in x['parts'].values())
        total=sum(lock['weights'][k]*v for k,v in x['parts'].items())
        assert math.isclose(total,x['loss'],rel_tol=1e-6,abs_tol=1e-8)
        if i%4==0:
            u=i//4;lr=1e-5*u/64 if u<=64 else 1e-6+.5*9e-6*(1+math.cos(math.pi*(u-64)/1984))
            assert x['update']==u and abs(x['lr']-lr)<1e-18 and math.isfinite(x['unclipped_accumulated_grad_norm'])
        else:assert 'update' not in x
    assert set(counts)==set(old['arms']['expanded'])
    curves=[]
    for update in lock['probe_updates']:
        path=folder/f'probe_{update:04d}';p=json.loads((path/'report.json').read_text())
        assert p['update']==update and p['role']=='train_probe_only' and len(p['records'])==64
        assert {(x['group_id'],x['seed']) for x in p['records']}=={(g,s) for g in lock['probe_groups'] for s in lock['training_seeds']}
        if update==0:
            prior=json.loads((control/'expanded/probe_0000/report.json').read_text())
            assert {(x['group_id'],x['seed']):x['sha256'] for x in p['records']}=={(x['group_id'],x['seed']):x['sha256'] for x in prior['records']}
        for x in p['records']:
            file=path/f'{x["group_id"]}_{x["seed"]}.npy';assert sha256(file)==x['sha256'] and np.isfinite(np.load(file)).all()
        curves.append({k:v for k,v in p.items() if k!='records'})
    checkpoint=folder/'update_2048.pt';assert sha256(checkpoint)==report['terminal_sha256']
    state=torch.load(checkpoint,map_location='cpu',weights_only=False)
    assert state['schema']==lock['checkpoint_schema'] and state['arm']=='expanded'
    assert state['lock_sha256']==sha256(root/'lock.json') and state['parent_sha256']==PARENT_SHA256
    assert state['update']==2048 and state['exposures']==8192 and list(state['trained'])==lock['selected_names']
    assert sum(v.numel() for v in state['trained'].values())==69777841 and all(torch.isfinite(v).all() for v in state['trained'].values())
    assert len(state['optimizer']['state'])==288 and all(int(v['step'])==2048 for v in state['optimizer']['state'].values())
    group,=state['optimizer']['param_groups'];assert group['betas']==(.9,.999) and group['eps']==1e-8 and group['weight_decay']==0 and group['lr']==1e-6
    write_json(root/'ablation_training_audit.json',dict(complete=True,lock_sha256=sha256(root/'lock.json'),
        checkpoint=dict(path=str(checkpoint),sha256=sha256(checkpoint)),same_start=True,initial_probe_replay_exact=True,
        same_exposure_order=True,exposure_min=min(counts.values()),exposure_max=max(counts.values()),curves=curves,
        seconds=report['seconds'],peak_gpu_bytes=report['peak_gpu_bytes'],scope='execution and TRAIN probes; no validation conclusion'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--mode',choices=['prepare','preflight','train','audit'],required=True)
    p.add_argument('--control',type=Path);p.add_argument('--evaluation',type=Path)
    a=p.parse_args();root=a.root.resolve()
    if a.mode=='prepare':prepare_coordinate_ablation(root,a.control.resolve(),a.evaluation.resolve())
    elif a.mode=='audit':audit_coordinate_ablation(root)
    else:run_coordinate_ablation(root,a.mode)
