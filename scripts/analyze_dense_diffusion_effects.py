#!/usr/bin/env python3
"""Native parameter and coordinate effect sizes from completed dense terminals."""
import argparse
import json
from pathlib import Path
import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256, write_json


def analyze_dense_effects(root):
    lock=json.loads((root/'lock.json').read_text());evaluation=json.loads((root/'evaluation.json').read_text())
    assert evaluation['complete'];source=Path(lock['source'])
    base_path=next(p for p in lock['weights_sha256'] if Path(p).name=='protenix_mini_esm_v0.5.0.pt')
    assert sha256(Path(base_path))==lock['weights_sha256'][base_path]
    checkpoint=torch.load(base_path,map_location='cpu',weights_only=False);base=checkpoint.get('model',checkpoint)
    common=set(lock['selected_names']['token_dense']);summaries={};tensors=[]
    for arm,c in lock['checkpoints'].items():
        assert sha256(Path(c['path']))==c['sha256']
        state=torch.load(c['path'],map_location='cpu',weights_only=False);weights=state['trained'];del state
        assert set(weights)==set(lock['selected_names'][arm])
        records=[]
        for name,value in weights.items():
            before=base['module.'+name].double();difference=value.double()-before
            n=float(before.norm());d=float(difference.norm())
            records.append(dict(name=name,weight_norm=n,delta_norm=d,relative_delta=d/n if n>0 else None,
                zero_reference_norm=n==0,changed=bool(torch.count_nonzero(difference)),elements=value.numel()))
        history=[json.loads(s) for s in (Path(c['path']).parent/'history.jsonl').read_text().splitlines()]
        norms=[r['unclipped_accumulated_grad_norm'] for r in history if 'update' in r]
        part=[r for r in records if r['name'] in common]
        summaries[arm]=dict(tensors=len(records),changed_tensors=sum(r['changed'] for r in records),
            zero_reference_tensors=sum(r['zero_reference_norm'] for r in records),
            selected_delta_to_weight_frobenius=float(np.sqrt(sum(r['delta_norm']**2 for r in records)/sum(r['weight_norm']**2 for r in records))),
            common56_delta_to_weight_frobenius=float(np.sqrt(sum(r['delta_norm']**2 for r in part)/sum(r['weight_norm']**2 for r in part))),
            clipped_updates=sum(n>1 for n in norms),mean_unclipped_norm=float(np.mean(norms)))
        tensors.extend(dict(arm=arm,**r) for r in records);del weights
    shifts=[]
    for row in lock['rows']:
        assert row['role']=='train';g=row['group_id'];names=np.load(source/'chemistry'/g/'mapping.npz')['atom_names'];ca=names=='CA'
        for seed in lock['train_seeds']:
            folder=root/'examples'/g;x=np.load(folder/f'native_s1_seed{seed}.npy').astype(float);xc=x-x.mean(0)
            for model in ['token_dense','diffusion_dense','calibrated_high','native_s2']:
                y=np.load(folder/f'{model}_seed{seed}.npy').astype(float);yc=y-y.mean(0);u,_,vt=np.linalg.svd(yc.T@xc)
                rotation=u@np.diag([1,1,np.linalg.det(u@vt)])@vt;aligned=yc@rotation-xc
                diff=np.sum((y-x)**2,axis=1);adiff=np.sum(aligned**2,axis=1)
                shifts.append(dict(group_id=g,pdb_id=row['pdb_id'],seed=seed,model=model,
                    unaligned_heavy_rms=float(np.sqrt(diff.mean())),unaligned_ca_rms=float(np.sqrt(diff[ca].mean())),
                    heavy_aligned_rms=float(np.sqrt(adiff.mean())),ca_after_heavy_alignment_rms=float(np.sqrt(adiff[ca].mean())),
                    max_atom_after_heavy_alignment=float(np.sqrt(adiff.max()))))
    shift_summary={}
    for model in ['token_dense','diffusion_dense','calibrated_high','native_s2']:
        rows=[r for r in shifts if r['model']==model]
        shift_summary[model]={k:dict(mean=float(np.mean([r[k] for r in rows])),median=float(np.median([r[k] for r in rows])),max=max(r[k] for r in rows))
            for k in ['unaligned_heavy_rms','unaligned_ca_rms','heavy_aligned_rms','ca_after_heavy_alignment_rms','max_atom_after_heavy_alignment']}
    lookup={(r['group_id'],r['seed'],r['model']):r for r in evaluation['records']};damage=[]
    for row in evaluation['records']:
        if row['model'] not in lock['checkpoints']:continue
        native=lookup[row['group_id'],row['seed'],'native_s1'];geom=row['geometry'];old=native['geometry']
        collision=geom['severe_pairs']>0 and old['severe_pairs']==0
        stereo=not geom['strict_checked_chirality'] and old['strict_checked_chirality']
        if collision or stereo:damage.append(dict(group_id=row['group_id'],pdb_id=row['pdb_id'],seed=row['seed'],model=row['model'],
            new_severe=collision,lost_strict_stereo=stereo,delta_aa=row['all_atom_lddt']-native['all_atom_lddt'],before=old,after=geom))
    write_json(root/'effects.json',dict(complete=True,posthoc=True,no_new_predictions=True,
        evaluation_sha256=sha256(root/'evaluation.json'),parameters=tensors,arms=summaries,
        shifts=shifts,shift_summary=shift_summary,new_damage=damage,
        note='Selected-parameter norm ratios have different denominators; common56 uses the same public matrices.'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();torch.set_num_threads(1);analyze_dense_effects(a.root)
