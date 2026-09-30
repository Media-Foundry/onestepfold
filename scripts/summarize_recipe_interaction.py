#!/usr/bin/env python3
"""Protein-paired factorial contrasts on a fixed TRAIN panel, including interaction."""
import argparse
import json
from pathlib import Path
import numpy as np
from fastglycan.paired_teacher_protocol import sha256, write_json


def summarize_recipe_interaction(root):
    lock=json.loads((root/'lock.json').read_text())
    evaluation=json.loads((root/'evaluation.json').read_text())
    assert evaluation['complete'] and evaluation['proteins']==128 and evaluation['outputs']==1536
    assert evaluation['lock_sha256']==sha256(root/'lock.json')
    records=evaluation['records'];assert {r['role'] for r in records}=={'train'}
    groups=sorted({r['group_id'] for r in records});seeds=lock['train_seeds']
    lookup={(r['group_id'],r['seed'],r['model']):r for r in records}
    quality=['all_atom_lddt','ca_lddt','ca_aligned_rmsd']
    geometry=['severe_pairs','severe_pairs_per_atom','max_penetration','ca_chirality_wrong',
        'sidechain_checked_wrong','observed_gt_bond_rmse']
    metrics=quality+geometry+['gt_branch_mismatches']
    values={}
    for model in lock['models']:
        values[model]={}
        for metric in metrics:
            values[model][metric]=np.array([np.mean([
                (lookup[g,s,model]['geometry'][metric] if metric in geometry else lookup[g,s,model][metric])
                for s in seeds]) for g in groups])
    coefficients=dict(lr_old=dict(old_high=1,old_low=-1),
        lr_calibrated=dict(calibrated_high=1,calibrated_low=-1),
        objective_low=dict(calibrated_low=1,old_low=-1),
        objective_high=dict(calibrated_high=1,old_high=-1),
        interaction=dict(calibrated_high=1,calibrated_low=-1,old_high=-1,old_low=1))
    bootstrap=np.random.default_rng(lock['bootstrap']['seed']).integers(0,len(groups),size=(10000,len(groups)))
    contrasts={}
    for name,weights in coefficients.items():
        contrasts[name]={}
        for metric in metrics:
            delta=sum(weight*values[model][metric] for model,weight in weights.items())
            contrasts[name][metric]=dict(mean=float(delta.mean()),median=float(np.median(delta)),
                ci95=np.quantile(delta[bootstrap].mean(1),[.025,.975]).tolist(),per_protein=delta.tolist())
    write_json(root/'factorial.json',dict(complete=True,evaluation_sha256=sha256(root/'evaluation.json'),
        groups=groups,coefficients=coefficients,contrasts=contrasts,
        means={m:{k:float(v.mean()) for k,v in items.items()} for m,items in values.items()},
        scope='TRAIN fitting evidence; protein resampling conditional on fixed two noises; no multiplicity correction or generalization claim'))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True)
    summarize_recipe_interaction(parser.parse_args().root)
