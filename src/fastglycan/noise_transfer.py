"""TRAIN-only diagnostic of continuation gains on unused initial diffusion noise."""
import copy
import numpy as np
from .evaluation_reuse import expected_evaluation_calls

NEW_NOISES = [920003, 920009, 920021, 920033]


def make_noise_transfer_lock(prior, training, *, parent, parent_lock, hashes, input_hashes):
    groups=training['probe_groups'];rows={r['group_id']:r for r in prior['rows']}
    if len(groups)!=32 or len(set(groups))!=32 or any(rows[g]['role']!='train' for g in groups):
        raise ValueError('use the original TRAIN32 only')
    if training['training_seeds']!=[600001,600011]:raise ValueError('unexpected old noise definition')
    lock=copy.deepcopy(prior);chosen=[rows[g] for g in groups]
    shards=[[] for _ in range(8)];loads=[0]*8
    for r in sorted(chosen,key=lambda r:(-len(r['sequence']),r['group_id'])):
        i=min(range(8),key=lambda j:(loads[j],j));shards[i].append(r);loads[i]+=len(r['sequence'])**2
    lock.update(schema='mini_noise_transfer_v1',rows=chosen,assignments=shards,
        models=['retained','weak'],checkpoints={'retained':copy.deepcopy(parent),'weak':prior['checkpoints']['weak']},
        checkpoint_arms={'retained':'diffusion_dense','weak':'expanded'},
        checkpoint_training_locks={'retained':parent_lock,'weak':prior['checkpoint_training_locks']['weak']},
        selected_names={m:list(training['selected_names']) for m in ['retained','weak']},reuse_models={},
        train_seeds=[600001,600011]+NEW_NOISES,noise_sets={'seen':[600001,600011],'new':NEW_NOISES},
        hashes=copy.deepcopy(hashes),input_hashes=copy.deepcopy(input_hashes),
        planned_outputs=384,planned_prediction_nfe=384,planned_probe_nfe=56,
        cohorts={'original_train_probe32':list(groups)},cohort_order=['original_train_probe32'],
        contrasts=[['weak','retained']],primary='TRAIN32 weak-minus-retained gain on four new noises versus two seen noises')
    assert expected_evaluation_calls(lock,chosen)==dict(native=0,retained=192,weak=192)
    return lock


def summarize_noise_transfer(records,lock):
    groups=[r['group_id'] for r in lock['rows']];seeds=lock['train_seeds'];models=lock['models']
    lookup={(r['group_id'],r['seed'],r['model']):r for r in records}
    expected={(g,s,m) for g in groups for s in seeds for m in models}
    if len(records)!=len(expected) or set(lookup)!=expected:raise ValueError('missing or duplicate prediction score')
    boot=np.random.default_rng(20261001).integers(0,len(groups),size=(10000,len(groups)))
    result={};gains={};paired=[]
    for label,noises in lock['noise_sets'].items():
        data={};gain={}
        for m in models:
            rr=[lookup[g,s,m] for g in groups for s in noises]
            data[m]={k:float(np.mean([r[k] for r in rr])) for k in ['all_atom_lddt','ca_lddt','ca_aligned_rmsd']}
            data[m].update(instances=len(rr),severe_pairs=sum(r['geometry']['severe_pairs'] for r in rr),
                zero_and_strict=sum(r['geometry']['severe_pairs']==0 and r['geometry']['strict_checked_chirality'] for r in rr))
        for key in ['all_atom_lddt','ca_lddt','ca_aligned_rmsd']:
            d=np.array([np.mean([lookup[g,s,'weak'][key]-lookup[g,s,'retained'][key] for s in noises]) for g in groups])
            gains[label,key]=d
            gain[key]=dict(mean=float(d.mean()),ci95=np.quantile(d[boot].mean(1),[.025,.975]).tolist(),positive=int((d>0).sum()))
        result[label]=dict(models=data,gain=gain)
    interaction={}
    for key in ['all_atom_lddt','ca_lddt','ca_aligned_rmsd']:
        d=gains['new',key]-gains['seen',key]
        interaction[key]=dict(mean=float(d.mean()),ci95=np.quantile(d[boot].mean(1),[.025,.975]).tolist())
    for i,g in enumerate(groups):
        paired.append(dict(group_id=g,gains={label:{key:float(gains[label,key][i]) for key in ['all_atom_lddt','ca_lddt','ca_aligned_rmsd']} for label in ['seen','new']}))
    return dict(complete=True,summary=result,new_minus_seen_gain=interaction,paired=paired,
        scope='TRAIN32 conditional on six locked noises; not sequence generalization or deployment approval')
