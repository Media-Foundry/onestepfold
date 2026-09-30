#!/usr/bin/env python3
"""Bind and run one global-distance candidate around an unchanged trainer."""
import argparse
import collections
import json
import math
import os
from pathlib import Path
import numpy as np
import torch
from fastglycan.folding_ablation import CONTROL_LOCK_SHA256
from fastglycan.folding_scale import PARENT_SHA256,folding_scale_lr
from fastglycan.global_distance_supervision import build_global_ca_distance_labels
from fastglycan.global_distance_training import (make_global_distance_lock,verify_global_distance_lock,
    global_distance_training_hooks,GLOBAL_DISTANCE_WEIGHT,CALIBRATION_MANIFEST_SHA256)
from fastglycan.paired_teacher_protocol import sha256,write_json


def prepare_global_distance_training(root,control,calibration,evaluation):
    assert not (root/'lock.json').exists();torch.set_num_threads(1)
    old=json.loads((control/'lock.json').read_text());assert sha256(control/'lock.json')==CONTROL_LOCK_SHA256
    assert json.loads((control/'training_audit.json').read_text())['complete']
    assert sha256(Path(old['initial_checkpoint']))==PARENT_SHA256
    c=json.loads((calibration/'report.json').read_text());a=json.loads((calibration/'acceptance.json').read_text())
    assert c['complete'] and a['complete'] and c['coefficient']==GLOBAL_DISTANCE_WEIGHT
    assert c['manifest_sha256']==sha256(calibration/'manifest.json')==CALIBRATION_MANIFEST_SHA256
    assert sha256(calibration/'report.json')==a['files']['report.json']
    assert sha256(root/'code/src/fastglycan/global_distance_supervision.py')==sha256(calibration/'code/src/fastglycan/global_distance_supervision.py')
    original={}
    for p,h in old['hashes'].items():
        new=root/'code'/Path(p).relative_to(control/'code');assert sha256(Path(p))==sha256(new)==h,p
        original[str(new)]=h
    el=json.loads((evaluation/'lock.json').read_text());execution=json.loads((evaluation/'execution.json').read_text())
    assert execution['complete'] and execution['lock_sha256']==sha256(evaluation/'lock.json')
    source=Path(old['source']);assert el['source']==old['source'];rows={r['group_id']:r for r in old['rows']}
    labels={};references={};bound={};(root/'global_labels').mkdir(exist_ok=False)
    for g in old['arms']['expanded']:
        assert rows[g]['role']=='train'
        mp=source/'chemistry'/g/'mapping.npz';gp=source/'data/examples'/g/'gt.npz'
        for p in [mp,gp]:assert sha256(p)==el['input_hashes'][str(p)];bound[str(p)]=sha256(p)
        m=dict(np.load(mp));gt=dict(np.load(gp));ca=(m['atom_names']=='CA')&m['mask'];ids=m['residue_ids'][ca]-1
        assert gt['atom37_mask'][ids,1].all() and gt['residue_mask'][ids].all()
        assert np.array_equal(gt['atom37_positions'][ids,1],m['coordinates'][ca])
        distance=build_global_ca_distance_labels(m);assert len(distance['pairs'])>0
        file=root/'global_labels'/f'{g}.pt'
        torch.save(dict(group_id=g,labels=distance,**{k:m[k] for k in ['atom_names','residue_ids','chain_ids']}),file)
        labels[g]=dict(path=str(file),sha256=sha256(file),pairs=len(distance['pairs']))
        bound[str(file)]=sha256(file)
    for g in old['engineering_groups']:
        p=evaluation/'examples'/g/'report.json';r=json.loads(p.read_text());assert r['lock_sha256']==sha256(evaluation/'lock.json')
        entry,=[x for x in r['entries'] if x['model']=='retained' and x['seed']==old['training_seeds'][0]]
        file=p.parent/entry['name'];assert sha256(file)==entry['sha256']
        references[g]=dict(path=str(file),sha256=entry['sha256']);bound[str(file)]=entry['sha256']
    hashes={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.json','.md']};hashes.update(bound)
    for p in [control/'lock.json',control/'preflight/report.json',calibration/'report.json',calibration/'acceptance.json',calibration/'manifest.json']:hashes[str(p)]=sha256(p)
    meta=dict(control=str(control),control_lock_sha256=CONTROL_LOCK_SHA256,calibration=str(calibration),calibration_manifest_sha256=CALIBRATION_MANIFEST_SHA256,
              calibration_report_sha256=sha256(calibration/'report.json'),labels=labels,retained_engineering_coordinates=references,
              original_code_identical=original,semantic_candidate_name='global_distance',checkpoint_arm='expanded')
    lock=make_global_distance_lock(old,protocol_sha256=sha256(root/'code/docs/mini_folding_global_distance_training_v1.md'),
        script_sha256=sha256(Path(__file__)),hashes=hashes,provenance=meta)
    write_json(root/'lock.json',lock)
    write_json(root/'prepare.json',dict(complete=True,labels=len(labels),pairs=sum(v['pairs'] for v in labels.values()),original_code_identical=len(original),
        lock_sha256=sha256(root/'lock.json'),coefficient=GLOBAL_DISTANCE_WEIGHT))


def run_global_distance_training(root,mode):
    import train_folding_scale as trainer
    import fastglycan.adapter_supervision as supervision
    lock=json.loads((root/'lock.json').read_text());control=Path(lock['global_distance']['control'])
    assert sha256(control/'lock.json')==CONTROL_LOCK_SHA256
    old=json.loads((control/'lock.json').read_text());verify_global_distance_lock(lock,old)
    assert Path(os.environ['PROTENIX_ROOT_DIR']).resolve()==root.parent/'protenix_stage0_pkg/v1_1/runtime'
    assert os.environ.get('LAYERNORM_TYPE')=='torch'
    checks=[]
    if mode=='train':
        release=json.loads((root/'release.json').read_text())
        assert release['objective_preflight_sha256']==sha256(root/'objective_preflight.json')
        assert json.loads((root/'objective_preflight.json').read_text())['complete']
    previous={r['group_id']:r for r in json.loads((control/'preflight/report.json').read_text())['cases']}
    def observer(x,labels,teacher,parts,original_parts,kwargs):
        g=labels['_global_group'];assert g==lock['engineering_groups'][len(checks)]
        with torch.no_grad():
            baseparts=original_parts(x.detach(),labels,teacher,**kwargs)
            assert set(parts)==set(baseparts)|{'global_distance'}
            assert all(torch.equal(parts[k],v) for k,v in baseparts.items())
            base=sum(old['weights'][k]*v for k,v in baseparts.items())
            assert math.isclose(float(base),previous[g]['loss'],rel_tol=1e-6,abs_tol=1e-8)
            candidate=sum(lock['weights'][k]*v for k,v in parts.items())
            expected=base-.01*parts['coordinate']+GLOBAL_DISTANCE_WEIGHT*parts['global_distance']
            assert torch.allclose(candidate,expected,rtol=1e-6,atol=1e-8)
            ref=lock['global_distance']['retained_engineering_coordinates'][g]
            assert sha256(Path(ref['path']))==ref['sha256']
            delta=float(np.max(np.abs(x.detach().cpu().numpy()-np.load(ref['path']))));assert delta<=lock['coordinate_replay_bound']
            gl=labels['_global_distance'];pairs=gl['pairs'];cpu=x.detach().cpu().double()
            error=((cpu[pairs[:,0]]-cpu[pairs[:,1]]).norm(dim=-1)-gl['target_distance']).abs()
            independent=torch.where(error<10,error.square()/20,error-5).mean()
            assert math.isclose(float(independent),float(parts['global_distance']),rel_tol=2e-5,abs_tol=1e-7)
        grad,=torch.autograd.grad(parts['global_distance'],x,retain_graph=True)
        ca=labels['_global_distance']['ca_indices'].to(x.device);nonca=torch.ones(len(x),device=x.device,dtype=torch.bool);nonca[ca]=False
        assert torch.isfinite(grad).all() and grad[ca].abs().max()>0 and torch.count_nonzero(grad[nonca])==0
        checks.append(dict(group_id=g,parts_identical=True,retained_forward_max_abs=delta,global_pairs=len(pairs),
            global_loss=float(parts['global_distance'].detach()),independent_global_loss=float(independent),global_coordinate_gradient_norm=float(grad.double().norm()),
            old_total=float(base),new_total=float(candidate),new_term_nonzero_ca_only=True))
    with global_distance_training_hooks(trainer,supervision,lock,observer if mode=='preflight' else None):
        trainer.run_folding_training(root,mode,'expanded' if mode=='train' else None)
    if mode=='preflight':
        report=json.loads((root/'preflight/report.json').read_text());assert report['complete'] and len(checks)==2 and 'H100' in report['device']
        assert report['initial_sha256']==json.loads((control/'preflight/report.json').read_text())['initial_sha256']
        write_json(root/'objective_preflight.json',dict(complete=True,cases=checks,lock_sha256=sha256(root/'lock.json'),parameter_updates=0,original_functions_restored=True))
        write_json(root/'release.json',dict(lock_sha256=sha256(root/'lock.json'),preflight_sha256=sha256(root/'preflight/report.json'),
            objective_preflight_sha256=sha256(root/'objective_preflight.json'),arms=['expanded'],updates_each=2048,validation_during_training=False))


def audit_global_distance_training(root):
    torch.set_num_threads(1);lock=json.loads((root/'lock.json').read_text());control=Path(lock['global_distance']['control'])
    assert sha256(control/'lock.json')==CONTROL_LOCK_SHA256
    old=json.loads((control/'lock.json').read_text());verify_global_distance_lock(lock,old)
    for p,h in lock['hashes'].items():assert sha256(Path(p))==h,p
    folder=root/'expanded';report=json.loads((folder/'report.json').read_text())
    assert report['complete'] and report['updates']==2048 and report['exposures']==8192 and not report['validation_read']
    assert report['lock_sha256']==sha256(root/'lock.json') and report['excluded_parameters_unchanged']
    assert report['counts']==dict(pairformer=0,diffusion=8448)
    assert report['initial_sha256']==sha256(folder/'initial_fingerprints.json')==json.loads((control/'expanded/report.json').read_text())['initial_sha256']
    assert sha256(folder/'history.jsonl')==report['history_sha256'];history=[json.loads(s) for s in (folder/'history.jsonl').read_text().splitlines()]
    assert len(history)==8192;counts=collections.Counter()
    for i,(x,y) in enumerate(zip(history,old['orders']['expanded']),1):
        assert x['exposure']==i and all(x[k]==y[k] for k in ['group_id','epoch','seed']);counts[x['group_id']]+=1
        assert set(x['parts'])==set(lock['weights']) and all(math.isfinite(v) for v in x['parts'].values())
        assert math.isclose(x['loss'],sum(lock['weights'][k]*v for k,v in x['parts'].items()),rel_tol=1e-6,abs_tol=1e-8)
        if i%4==0:
            assert x['update']==i//4 and abs(x['lr']-folding_scale_lr(i//4,lock['learning_rate'],2048))<1e-18
            assert math.isfinite(x['unclipped_accumulated_grad_norm'])
        else:assert 'update' not in x
    assert set(counts)==set(old['arms']['expanded']);curves=[]
    for update in lock['probe_updates']:
        path=folder/f'probe_{update:04d}';p=json.loads((path/'report.json').read_text())
        assert p['update']==update and p['role']=='train_probe_only' and len(p['records'])==64
        assert {(x['group_id'],x['seed']) for x in p['records']}=={(g,s) for g in lock['probe_groups'] for s in lock['training_seeds']}
        if update==0:
            prior=json.loads((control/'expanded/probe_0000/report.json').read_text())
            assert {(x['group_id'],x['seed']):x['sha256'] for x in p['records']}=={(x['group_id'],x['seed']):x['sha256'] for x in prior['records']}
        for x in p['records']:assert sha256(path/f'{x["group_id"]}_{x["seed"]}.npy')==x['sha256'] and np.isfinite(np.load(path/f'{x["group_id"]}_{x["seed"]}.npy')).all()
        curves.append({k:v for k,v in p.items() if k!='records'})
    file=folder/'update_2048.pt';assert sha256(file)==report['terminal_sha256'];state=torch.load(file,map_location='cpu',weights_only=False)
    assert state['schema']==lock['checkpoint_schema'] and state['arm']=='expanded' and state['lock_sha256']==sha256(root/'lock.json')
    assert state['parent_sha256']==PARENT_SHA256 and state['update']==2048 and state['exposures']==8192
    assert list(state['trained'])==lock['selected_names'] and sum(v.numel() for v in state['trained'].values())==69777841
    assert all(torch.isfinite(v).all() for v in state['trained'].values())
    assert len(state['optimizer']['state'])==288 and all(int(v['step'])==2048 for v in state['optimizer']['state'].values())
    group,=state['optimizer']['param_groups'];assert group['betas']==(.9,.999) and group['eps']==1e-8 and group['weight_decay']==0 and group['lr']==1e-6
    write_json(root/'global_training_audit.json',dict(complete=True,lock_sha256=sha256(root/'lock.json'),checkpoint=dict(path=str(file),sha256=sha256(file)),
        same_start=True,same_exposure_order=True,initial_probe_replay_exact=True,exposure_min=min(counts.values()),exposure_max=max(counts.values()),curves=curves,
        seconds=report['seconds'],peak_gpu_bytes=report['peak_gpu_bytes'],scope='execution/TRAIN only; no held-out conclusion'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--mode',choices=['prepare','preflight','train','audit'],required=True)
    p.add_argument('--control',type=Path);p.add_argument('--calibration',type=Path);p.add_argument('--evaluation',type=Path);a=p.parse_args();root=a.root.resolve()
    if a.mode=='prepare':prepare_global_distance_training(root,a.control.resolve(),a.calibration.resolve(),a.evaluation.resolve())
    elif a.mode=='audit':audit_global_distance_training(root)
    else:run_global_distance_training(root,a.mode)
