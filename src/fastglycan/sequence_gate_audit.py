"""Independent integrity checks for the four-stage sequence experiment artifacts."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import torch
from .models.soft_esm import hard_sequence
from .paired_teacher_protocol import sha256
from .sequence_gate_metrics import contact_objective


def validate_run(folder: Path) -> dict:
    report=json.loads((folder/'report.json').read_text())
    if not report.get('complete') or report.get('stage')!='complete':
        raise ValueError('experiment is incomplete')
    steps=report['gates']['3_optimization']['updates']
    trajectory=report['trajectory']
    if steps<50 or [r['update'] for r in trajectory]!=list(range(steps+1)):
        raise ValueError('missing optimization updates')
    for row in trajectory:
        if row['update']%10==0 or row['update']==steps:
            if set(row.get('cross_losses',{}))!={'1','2'}:
                raise ValueError('missing matched S1/S2 cross-evaluation')
    logits=torch.load(folder/'logits.pt',map_location='cpu',weights_only=True)
    for name in ('initial_logits','final_logits'):
        if logits[name].shape!=(report['length'],20) or not torch.isfinite(logits[name]).all():
            raise ValueError('invalid saved logits')
    if hard_sequence(logits['initial_logits'])!=report['sequence']:
        raise ValueError('initial sequence disagrees with logits')
    if hard_sequence(logits['final_logits'])!=report['final_sequence']:
        raise ValueError('final sequence disagrees with logits')
    if trajectory[-1]['sequence']!=report['final_sequence']:
        raise ValueError('final trajectory sequence mismatch')
    for s in (1,2):
        gate=report['gates'][f'2_s{s}_local_derivative']
        if len(gate['directions'])<3:
            raise ValueError('fewer than three gradient directions')
        plateaus=[]
        for direction in gate['directions']:
            rows=direction['rows']
            if [r['h'] for r in rows]!=[.3,.1,.03,.01,.003]:
                raise ValueError('finite-difference step protocol mismatch')
            valid=[]
            for row in rows:
                analytic=row['analytic'];fd=row['finite_difference']
                error=abs(analytic-fd)
                valid.append(error<=1e-6+.05*max(abs(analytic),abs(fd)))
            plateau=any(a and b for a,b in zip(valid,valid[1:]))
            if plateau!=direction['plateau_pass']:
                raise ValueError('finite-difference acceptance disagrees with values')
            plateaus.append(plateau)
        passed=gate['finite'] and gate['norm']>0 and gate['repeat_max_abs']==0 and all(plateaus)
        if bool(passed)!=gate['passed']:
            raise ValueError('gradient gate acceptance mismatch')
    observations=report['gates']['4_independent_noise']
    index={(r['seed'],r['label'],r['steps']):r for r in observations}
    expected={(seed,label,s) for seed in (103,107) for label in ('initial','optimized') for s in (1,2)}
    if set(index)!=expected or len(observations)!=8:
        raise ValueError('missing or duplicate hard/noise observations')
    expected_names={f'{label}_seed{seed}_s{s}.npz' for seed,label,s in expected}
    if {p.name for p in folder.glob('*_seed*_s*.npz')}!=expected_names:
        raise ValueError('missing or extra coordinate artifacts')
    paths=[folder/'report.json',folder/'logits.pt']
    loss_errors=[]
    for seed,label,s in sorted(expected):
        path=folder/f'{label}_seed{seed}_s{s}.npz';paths.append(path)
        with np.load(path) as data:
            sequence=report['sequence'] if label=='initial' else report['final_sequence']
            if str(data['sequence'])!=sequence:raise ValueError('coordinate sequence mismatch')
            x=data['coordinates'];names=data['atom_names'];residues=data['residue_ids']
            if x.shape!=(1,len(names),3) or len(residues)!=len(names) or not np.isfinite(x).all():
                raise ValueError('invalid coordinates or atom inventory')
            ca=np.flatnonzero(names=='CA')
            if len(ca)!=len(sequence) or len(set(residues[ca].tolist()))!=len(sequence):
                raise ValueError('invalid backbone inventory')
            loss,_=contact_objective(torch.from_numpy(x),torch.from_numpy(ca))
            error=abs(float(loss)-index[seed,label,s]['loss'])
            if error>2e-5:raise ValueError('saved coordinates do not reproduce reported objective')
            loss_errors.append(error)
    return dict(artifacts_complete=True,artifact_sha256={p.name:sha256(p) for p in paths},
                max_cpu_objective_replay_error=max(loss_errors),report=report)
