#!/usr/bin/env python3
"""One fixed TRAIN-only CPU interface fit, with no structural labels or forward."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import torch
from fastglycan.conditioning_bridge import ProjectionMoments
from fastglycan.folding_esm_bridge import select_folding_bridge_train, load_folding_bridge_pair
from fastglycan.paired_teacher_protocol import sha256, write_json


def fit_folding_esmc_bridge(root):
    begin=time.monotonic();torch.set_num_threads(4)
    assert not torch.cuda.is_available()
    lock=json.loads((root/'lock.json').read_text())
    for p,h in lock['hashes'].items():assert sha256(Path(p))==h,p
    assert lock['ridge']==1e-3 and lock['variance_floor']==1e-8
    assert not (root/'bridge.pt').exists() and not (root/'report.json').exists()
    audit=json.loads(Path(lock['paired_audit']).read_text());assert audit['complete']
    train=json.loads(Path(lock['training_lock']).read_text())
    assert audit['training_lock_sha256']==sha256(Path(lock['training_lock']))
    cache=json.loads((Path(train['cache'])/'lock.json').read_text())
    assert audit['cache_lock_sha256']==sha256(Path(train['cache'])/'lock.json')==train['cache_lock_sha256']
    rows=select_folding_bridge_train(audit['pairs'],train['rows'])
    assert [r['group_id'] for r in rows]==lock['fit_group_ids']
    for p,h in audit['shard_hashes'].items():assert sha256(Path(p))==h,p
    checkpoint=Path(lock['native_checkpoint']);assert sha256(checkpoint)==cache['weights_sha256'][str(checkpoint)]
    state=torch.load(checkpoint,map_location='cpu',weights_only=True,mmap=True)['model']
    weight=state['module.input_embedder.linear_esm.weight'].clone().float()
    assert weight.shape==(449,2560) and 'module.input_embedder.linear_esm.bias' not in state
    del state
    moments=ProjectionMoments(1152,449)
    for i,row in enumerate(rows):
        x,e=load_folding_bridge_pair(row,lock['feature_root'],audit['cache_lock_sha256'])
        y=torch.nn.functional.linear(e,weight);moments.add(x,y)
        write_json(root/'progress.json',dict(stage='moments',proteins=i+1,residues=moments.residues))
    fit=moments.solve(ridge=lock['ridge'],variance_floor=lock['variance_floor'])
    assert fit['train_proteins']==423
    fit.update(schema='folding_esmc_affine_bridge_v1',lock_sha256=sha256(root/'lock.json'),train_group_ids=lock['fit_group_ids'],
        native_projection_sha256=hashlib.sha256(weight.numpy().tobytes()).hexdigest())
    torch.save(fit,root/'bridge.pt')
    restored=torch.load(root/'bridge.pt',map_location='cpu',weights_only=True)
    assert all(torch.equal(fit[k],restored[k]) for k in ['weight','bias'])
    records=[]
    for i,row in enumerate(rows):
        x,e=load_folding_bridge_pair(row,lock['feature_root'],audit['cache_lock_sha256'])
        y=torch.nn.functional.linear(e,weight).double();prediction=torch.nn.functional.linear(x.float(),fit['weight'],fit['bias'])
        assert torch.isfinite(prediction).all()
        mse=float((prediction.double()-y).square().mean());baseline=float((y-fit['train_y_mean']).square().mean())
        records.append(dict(group_id=row['group_id'],cohort=row['cohort'],length=row['length'],mse=mse,
            train_mean_baseline_mse=baseline,relative_mse=mse/baseline if baseline>0 else None))
        write_json(root/'progress.json',dict(stage='train_residuals',proteins=i+1))
    summary={}
    for cohort in ['all_train','original_train','added_train']:
        part=[r for r in records if cohort=='all_train' or r['cohort']==cohort]
        summary[cohort]=dict(proteins=len(part),residues=sum(r['length'] for r in part),
            **{k:sum(r[k] for r in part)/len(part) for k in ['mse','train_mean_baseline_mse']},
            relative_mse=sum(r['relative_mse'] for r in part if r['relative_mse'] is not None)/sum(r['relative_mse'] is not None for r in part))
    assert sha256(Path(lock['active_training_lock']))==lock['active_training_lock_sha256']
    write_json(root/'report.json',dict(complete=True,lock_sha256=sha256(root/'lock.json'),bridge_sha256=sha256(root/'bridge.pt'),
        summary=summary,records=records,seconds=time.monotonic()-begin,train_proteins=423,validation_feature_reads=0,
        experimental_coordinate_reads=0,folding_calls=0,model_training=False,active_training_unchanged=True,
        scope='TRAIN-only affine initialization. Feature regression is not evidence of folding quality; no DEV fitting/selection or structural prediction.',
        numerical_scope='BF16 cached ESMC promoted to FP32; targets use native FP32 projection on CPU; FP64 moments/solve, stored FP32 bridge. Not GPU bitwise projection parity.',
        provenance_limit='Paired tensor hashes rechecked in both passes; full ESM2 conditioning-container hashes inherited from prior accepted audit. No unrelated cached structural tensor is accessed.'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args()
    fit_folding_esmc_bridge(a.root.resolve())
