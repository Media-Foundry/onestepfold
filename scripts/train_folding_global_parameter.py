#!/usr/bin/env python3
"""Single stronger global weight around unchanged dense folding training."""
import argparse
import collections
import json
import math
import os
from pathlib import Path
import numpy as np
import torch
from fastglycan.global_parameter_training import (BASE_LOCK_SHA256,CALIBRATION_REPORT_SHA256,PARAMETER_MATCHED_WEIGHT,
    parameter_matched_coefficient,make_parameter_weight_lock,verify_parameter_weight_lock)
from fastglycan.global_distance_training import global_distance_training_hooks
from fastglycan.folding_scale import PARENT_SHA256,folding_scale_lr
from fastglycan.paired_teacher_protocol import sha256,write_json


def prepare_parameter_weight_training(root,baseline,calibration):
    assert not (root/'lock.json').exists()
    assert sha256(baseline/'lock.json')==BASE_LOCK_SHA256
    base=json.loads((baseline/'lock.json').read_text());audit=json.loads((baseline/'global_training_audit.json').read_text())
    assert audit['complete'] and audit['lock_sha256']==BASE_LOCK_SHA256
    assert sha256(calibration/'report.json')==CALIBRATION_REPORT_SHA256
    report=json.loads((calibration/'report.json').read_text());coefficient=parameter_matched_coefficient(report)
    assert math.isclose(coefficient,PARAMETER_MATCHED_WEIGHT,rel_tol=1e-14,abs_tol=0)
    accepted=json.loads((calibration/'acceptance.json').read_text());assert accepted['complete'] and accepted['files']['report.json']==CALIBRATION_REPORT_SHA256
    copied=0
    for p,h in base['hashes'].items():
        assert sha256(Path(p))==h,p
        if Path(p).is_relative_to(baseline/'code'):
            counterpart=root/'code'/Path(p).relative_to(baseline/'code');assert sha256(counterpart)==h,p;copied+=1
    hashes=dict(base['hashes'])
    hashes.update({str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.md','.json']})
    for p in [baseline/'lock.json',baseline/'global_training_audit.json',baseline/'objective_preflight.json',baseline/'preflight/report.json',baseline/'expanded/report.json',calibration/'report.json',calibration/'acceptance.json',calibration/'lock.json']:
        hashes[str(p)]=sha256(p)
    assert sha256(Path(base['initial_checkpoint']))==PARENT_SHA256
    meta=dict(baseline=str(baseline),baseline_lock_sha256=BASE_LOCK_SHA256,calibration=str(calibration),calibration_report_sha256=CALIBRATION_REPORT_SHA256,
        coefficient=PARAMETER_MATCHED_WEIGHT,rule='TRAIN8 initial parameter-gradient norm median ratio; no terminal or DEV selection',
        semantic_candidate_name='global_parameter_matched',checkpoint_arm='expanded',original_source_files_identical=copied)
    lock=make_parameter_weight_lock(base,protocol_sha256=sha256(root/'code/docs/mini_folding_global_parameter_weight_v1.md'),script_sha256=sha256(Path(__file__)),hashes=hashes,provenance=meta)
    write_json(root/'lock.json',lock);write_json(root/'prepare.json',dict(complete=True,coefficient=coefficient,original_source_files_identical=copied,
        reused_global_labels=len(lock['global_distance']['labels']),lock_sha256=sha256(root/'lock.json')))


def run_parameter_weight_training(root,mode):
    import train_folding_scale as trainer
    import fastglycan.adapter_supervision as supervision
    lock=json.loads((root/'lock.json').read_text());baseline=Path(lock['parameter_budget']['baseline']);assert sha256(baseline/'lock.json')==BASE_LOCK_SHA256
    base=json.loads((baseline/'lock.json').read_text());verify_parameter_weight_lock(lock,base);checks=[]
    old={x['group_id']:x for x in json.loads((baseline/'objective_preflight.json').read_text())['cases']}
    if mode=='train':
        release=json.loads((root/'release.json').read_text());assert release['objective_preflight_sha256']==sha256(root/'objective_preflight.json')
        assert json.loads((root/'objective_preflight.json').read_text())['complete']
    def observer(x,labels,teacher,parts,old_parts,kwargs):
        g=labels['_global_group'];assert g==lock['engineering_groups'][len(checks)]
        with torch.no_grad():
            original=old_parts(x.detach(),labels,teacher,**kwargs);assert set(parts)==set(original)|{'global_distance'}
            assert all(torch.equal(v,parts[k]) for k,v in original.items())
            prior=sum(base['weights'][k]*v for k,v in parts.items());candidate=sum(lock['weights'][k]*v for k,v in parts.items())
            formula=prior+(PARAMETER_MATCHED_WEIGHT-base['weights']['global_distance'])*parts['global_distance']
            assert torch.allclose(candidate,formula,rtol=1e-6,atol=1e-8)
            assert math.isclose(float(prior),old[g]['new_total'],rel_tol=1e-6,abs_tol=1e-8)
            reference=base['global_distance']['retained_engineering_coordinates'][g];assert sha256(Path(reference['path']))==reference['sha256']
            delta=float(np.max(np.abs(x.detach().cpu().numpy()-np.load(reference['path']))));assert delta<=base['coordinate_replay_bound']
        checks.append(dict(group_id=g,raw_components_exact=True,parent_coordinate_max_abs=delta,prior_total=float(prior),new_total=float(candidate),
                           global_unweighted=float(parts['global_distance'].detach()),weighted_total_formula_checked=True))
    with global_distance_training_hooks(trainer,supervision,lock,observer if mode=='preflight' else None):
        trainer.run_folding_training(root,mode,'expanded' if mode=='train' else None)
    if mode=='preflight':
        report=json.loads((root/'preflight/report.json').read_text());prior=json.loads((baseline/'preflight/report.json').read_text())
        assert report['complete'] and report['initial_sha256']==prior['initial_sha256'] and len(checks)==2
        write_json(root/'objective_preflight.json',dict(complete=True,cases=checks,lock_sha256=sha256(root/'lock.json'),parameter_updates=0,original_functions_restored=True))
        write_json(root/'release.json',dict(lock_sha256=sha256(root/'lock.json'),preflight_sha256=sha256(root/'preflight/report.json'),
            objective_preflight_sha256=sha256(root/'objective_preflight.json'),arms=['expanded'],updates_each=2048,validation_during_training=False))


def audit_parameter_weight_training(root):
    torch.set_num_threads(1);lock=json.loads((root/'lock.json').read_text());baseline=Path(lock['parameter_budget']['baseline'])
    assert sha256(baseline/'lock.json')==BASE_LOCK_SHA256;verify_parameter_weight_lock(lock,json.loads((baseline/'lock.json').read_text()))
    for p,h in lock['hashes'].items():assert sha256(Path(p))==h,p
    folder=root/'expanded';report=json.loads((folder/'report.json').read_text());assert report['complete'] and report['updates']==2048 and report['exposures']==8192
    assert report['lock_sha256']==sha256(root/'lock.json') and report['excluded_parameters_unchanged'] and not report['validation_read']
    assert report['counts']==dict(pairformer=0,diffusion=8448)
    assert report['initial_sha256']==sha256(folder/'initial_fingerprints.json')==json.loads((baseline/'expanded/report.json').read_text())['initial_sha256']
    assert sha256(folder/'history.jsonl')==report['history_sha256'];history=[json.loads(s) for s in (folder/'history.jsonl').read_text().splitlines()];assert len(history)==8192;counts=collections.Counter()
    for i,(x,y) in enumerate(zip(history,lock['orders']['expanded']),1):
        assert x['exposure']==i and all(x[k]==y[k] for k in ['group_id','epoch','seed']);counts[x['group_id']]+=1
        assert set(x['parts'])==set(lock['weights']) and all(math.isfinite(v) for v in x['parts'].values())
        assert math.isclose(x['loss'],sum(lock['weights'][k]*v for k,v in x['parts'].items()),rel_tol=1e-6,abs_tol=1e-8)
        if i%4==0:
            assert x['update']==i//4 and abs(x['lr']-folding_scale_lr(i//4,lock['learning_rate'],2048))<1e-18
            assert math.isfinite(x['unclipped_accumulated_grad_norm'])
        else:assert 'update' not in x
    assert set(counts)==set(lock['arms']['expanded']);curves=[]
    for update in lock['probe_updates']:
        path=folder/f'probe_{update:04d}';p=json.loads((path/'report.json').read_text());assert p['update']==update and p['role']=='train_probe_only' and len(p['records'])==64
        assert {(x['group_id'],x['seed']) for x in p['records']}=={(g,s) for g in lock['probe_groups'] for s in lock['training_seeds']}
        for x in p['records']:assert sha256(path/f'{x["group_id"]}_{x["seed"]}.npy')==x['sha256'] and np.isfinite(np.load(path/f'{x["group_id"]}_{x["seed"]}.npy')).all()
        if update==0:
            prior=json.loads((baseline/'expanded/probe_0000/report.json').read_text());assert {(x['group_id'],x['seed']):x['sha256'] for x in p['records']}=={(x['group_id'],x['seed']):x['sha256'] for x in prior['records']}
        curves.append({k:v for k,v in p.items() if k!='records'})
    file=folder/'update_2048.pt';assert sha256(file)==report['terminal_sha256'];state=torch.load(file,map_location='cpu',weights_only=False)
    assert state['schema']==lock['checkpoint_schema'] and state['arm']=='expanded' and state['lock_sha256']==sha256(root/'lock.json')
    assert state['parent_sha256']==PARENT_SHA256 and state['update']==2048 and state['exposures']==8192
    assert list(state['trained'])==lock['selected_names'] and sum(v.numel() for v in state['trained'].values())==69777841
    assert all(torch.isfinite(v).all() for v in state['trained'].values())
    assert len(state['optimizer']['state'])==288 and all(int(v['step'])==2048 for v in state['optimizer']['state'].values())
    group,=state['optimizer']['param_groups'];assert group['betas']==(.9,.999) and group['eps']==1e-8 and group['weight_decay']==0 and group['lr']==1e-6
    write_json(root/'parameter_weight_training_audit.json',dict(complete=True,lock_sha256=sha256(root/'lock.json'),checkpoint=dict(path=str(file),sha256=sha256(file)),
        coefficient=PARAMETER_MATCHED_WEIGHT,same_start=True,same_exposure_order=True,initial_probe_replay_exact=True,
        exposure_min=min(counts.values()),exposure_max=max(counts.values()),curves=curves,seconds=report['seconds'],peak_gpu_bytes=report['peak_gpu_bytes'],
        scope='fixed terminal execution audit; no validation quality result'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--mode',choices=['prepare','preflight','train','audit'],required=True)
    p.add_argument('--baseline',type=Path);p.add_argument('--calibration',type=Path);a=p.parse_args();root=a.root.resolve()
    assert Path(os.environ['PROTENIX_ROOT_DIR']).resolve()==root.parent/'protenix_stage0_pkg/v1_1/runtime' and os.environ.get('LAYERNORM_TYPE')=='torch'
    if a.mode=='prepare':prepare_parameter_weight_training(root,a.baseline.resolve(),a.calibration.resolve())
    elif a.mode=='audit':audit_parameter_weight_training(root)
    else:run_parameter_weight_training(root,a.mode)
