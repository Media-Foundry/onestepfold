#!/usr/bin/env python3
"""One TRAIN-only scale calibration from initial-state component gradients."""
import argparse
import json
from pathlib import Path

import numpy as np
from fastglycan.paired_teacher_protocol import sha256, write_json


def calibrate_diffusion_objective(root,destination):
    lock=json.loads((root/'lock.json').read_text());audit=json.loads((root/'audit.json').read_text())
    summary=json.loads((root/'summary.json').read_text())
    assert audit['complete'] and summary['audit_sha256']==sha256(root/'audit.json')
    assert audit['lock_sha256']==sha256(root/'lock.json')
    points=[r for r in summary['points'] if r['state']=='initial'];assert len(points)==32
    groups=sorted({r['group_id'] for r in points});assert len(groups)==16
    medians={}
    for name in lock['names']:
        means=[]
        for group in groups:
            rows=[r for r in points if r['group_id']==group];assert {r['seed'] for r in rows}==set(lock['seeds'])
            means.append(np.mean([r['statistics']['raw_norm'][name] for r in rows]))
        medians[name]=float(np.median(means))
    target=lock['weights']['coordinate']*medians['coordinate'];assert target>0
    weights=dict(lock['weights'])
    for name in ['bond','clash','teacher']:
        assert medians[name]>0;weights[name]=target/medians[name]
    assert all(np.isfinite(v) and v>=0 for v in weights.values())
    old=np.array([lock['weights'][n] for n in lock['names']]);new=np.array([weights[n] for n in lock['names']])
    diagnostics=[]
    for row in points:
        gram=np.array(row['statistics']['raw_gram']);oldnorm=np.sqrt(old@gram@old);newnorm=np.sqrt(new@gram@new)
        gt=new.copy();gt[-1]=0;teacher=np.zeros(6);teacher[-1]=new[-1]
        diagnostics.append(dict(group_id=row['group_id'],seed=row['seed'],
            old_new_total_cosine=float(old@gram@new/(oldnorm*newnorm)),
            new_teacher_to_gt_norm_ratio=float(np.sqrt(teacher@gram@teacher)/np.sqrt(gt@gram@gt)),
            new_total_gradient_norm=float(newnorm)))
    write_json(destination,dict(schema='train_initial_gradient_calibration_v1',
        source_lock_sha256=sha256(root/'lock.json'),source_summary_sha256=sha256(root/'summary.json'),
        source_audit_sha256=sha256(root/'audit.json'),calibration_state='initial',proteins=groups,seeds=lock['seeds'],
        raw_gradient_protein_mean_medians=medians,target_weighted_coordinate_median=target,
        original_weights=lock['weights'],calibrated_weights=weights,changed_components=['bond','clash','teacher'],
        unchanged_components=['coordinate','smooth_lddt','chirality'],diagnostics=diagnostics,
        formula='w_j = median_protein(mean_noise(||w_A*g_A||)) / median_protein(mean_noise(||g_j||)), j=B,R,T',
        limitations='Matches one initial-state Euclidean norm statistic, not per-target or Adam updates; chemistry remains mandatory evaluation, no safety guarantee',
        no_training=True,no_validation_used=True,script_sha256=sha256(Path(__file__))))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    calibrate_diffusion_objective(a.root,a.output)
