#!/usr/bin/env python3
"""Post-hoc effect sizes from frozen pilot artifacts; no new predictions or tuning."""
import argparse
import json
from pathlib import Path

import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256, write_json


def analyze_diffusion_effects(root):
    lock=json.loads((root/'lock.json').read_text());train=Path(lock['train']);source=Path(lock['source'])
    evaluation=json.loads((root/'evaluation.json').read_text());assert evaluation['complete']
    base_path=next(p for p in lock['weights_sha256'] if Path(p).name=='protenix_mini_esm_v0.5.0.pt')
    assert sha256(Path(base_path))==lock['weights_sha256'][base_path]
    checkpoint=torch.load(base_path,map_location='cpu',weights_only=False)
    base=checkpoint['model'] if 'model' in checkpoint else checkpoint
    checkpoints=dict(lock['checkpoints'])
    checkpoints.update(lock.get('analysis_checkpoints',{}))
    if 'old_low' in lock:checkpoints['old_low']=lock['old_low']
    trained={a:torch.load(c['path'],map_location='cpu',weights_only=False)['trained'] for a,c in checkpoints.items()}
    matrices=[]
    for name in next(iter(trained.values())):
        weight=base['module.'+name+'.weight'].double()
        delta={a:trained[a][name]['up'].double()@trained[a][name]['down'].double() for a in trained}
        matrix=dict(name=name,weight_norm=float(weight.norm()),
            delta_norm={a:float(d.norm()) for a,d in delta.items()},
            relative_delta={a:float(d.norm()/weight.norm()) for a,d in delta.items()})
        if 'gt' in delta and 'gt_s2' in delta:
            matrix['between_arms_relative']=float((delta['gt_s2']-delta['gt']).norm()/delta['gt'].norm())
        matrices.append(matrix)
    arm_summary={}
    for a in trained:
        history=[json.loads(line) for line in (Path(checkpoints[a]['path']).parent/'history.jsonl').read_text().splitlines()]
        norms=np.array([r['unclipped_accumulated_grad_norm'] for r in history if 'update' in r])
        arm_summary[a]=dict(clipped_updates=int((norms>1).sum()),updates=len(norms),mean_unclipped_norm=float(norms.mean()),
            median_relative_matrix_delta=float(np.median([r['relative_delta'][a] for r in matrices])),
            max_relative_matrix_delta=max(r['relative_delta'][a] for r in matrices),
            total_delta_to_weight_frobenius_ratio=float(np.sqrt(sum(r['delta_norm'][a]**2 for r in matrices)/sum(r['weight_norm']**2 for r in matrices))))
    shifts=[]
    for row in lock['rows']:
        g=row['group_id'];names=np.load(source/'chemistry'/g/'mapping.npz')['atom_names'];ca=names=='CA'
        seeds=lock['train_seeds'] if row['role']=='train' else lock['validation_seeds']
        for seed in seeds:
            folder=root/'examples'/g;x=np.load(folder/f'native_s1_seed{seed}.npy').astype(float)
            for model in [*trained,'native_s2']:
                y=np.load(folder/f'{model}_seed{seed}.npy').astype(float);difference=np.sum((y-x)**2,axis=1)
                shifts.append(dict(group_id=g,role=row['role'],seed=seed,model=model,
                    raw_heavy_rms=float(np.sqrt(difference.mean())),raw_ca_rms=float(np.sqrt(difference[ca].mean())),
                    max_atom_shift=float(np.sqrt(difference.max()))))
    shift_summary={}
    for role in sorted({r['role'] for r in lock['rows']}):
        shift_summary[role]={}
        for model in [*trained,'native_s2']:
            rows=[r for r in shifts if r['role']==role and r['model']==model]
            shift_summary[role][model]={k:dict(mean=float(np.mean([r[k] for r in rows])),
                median=float(np.median([r[k] for r in rows])),max=max(r[k] for r in rows)) for k in ['raw_heavy_rms','raw_ca_rms','max_atom_shift']}
    lookup={(r['group_id'],r['seed'],r['model']):r for r in evaluation['records']}
    new_severe=[]
    for row in evaluation['records']:
        if row['model'] not in trained:continue
        raw=lookup[row['group_id'],row['seed'],'native_s1']
        if row['geometry']['severe_pairs'] and raw['geometry']['severe_pairs']==0:
            new_severe.append(dict(group_id=row['group_id'],pdb_id=row['pdb_id'],seed=row['seed'],model=row['model'],role=row['role'],
                before=raw['geometry'],after=row['geometry']))
    write_json(root/'effects.json',dict(complete=True,posthoc=True,no_new_predictions=True,
        evaluation_sha256=sha256(root/'evaluation.json'),matrices=matrices,arms=arm_summary,
        shifts=shifts,shift_summary=shift_summary,new_severe=new_severe,
        note='Scalar loss scales and clipping do not establish component gradient dominance or a causal remedy.'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args()
    torch.set_num_threads(1);analyze_diffusion_effects(a.root)
