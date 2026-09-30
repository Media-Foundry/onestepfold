import copy
import gzip
import json
from pathlib import Path
import pytest
from fastglycan.noise_transfer import make_noise_transfer_lock,summarize_noise_transfer,NEW_NOISES


def test_noise_panel_is_training_only_and_fixed_budget():
    root=Path(__file__).parents[1]/'reports'
    with gzip.open(root/'mini_folding_rocm_evaluation_2026-10-01/lock.json.gz','rt') as f:p=json.load(f)
    with gzip.open(root/'mini_folding_rocm_matched_2026-10-01/weak_lock.json.gz','rt') as f:t=json.load(f)
    before=copy.deepcopy(p)
    lock=make_noise_transfer_lock(p,t,parent={'path':'p','sha256':'h'},parent_lock='l',hashes={},input_hashes={})
    assert p==before and len(lock['rows'])==32 and all(r['role']=='train' for r in lock['rows'])
    assert lock['train_seeds']==[600001,600011]+NEW_NOISES and lock['planned_outputs']==384
    t['probe_groups'][0]=next(r['group_id'] for r in p['rows'] if r['role']=='validation')
    with pytest.raises(ValueError):make_noise_transfer_lock(p,t,parent={},parent_lock='l',hashes={},input_hashes={})


def test_statistic_detects_noise_specific_gain_and_rejects_missing_records():
    lock=dict(rows=[{'group_id':'a'},{'group_id':'b'}],models=['retained','weak'],
        train_seeds=[1,2,3,4],noise_sets={'seen':[1,2],'new':[3,4]})
    records=[]
    for g in ['a','b']:
        for s in lock['train_seeds']:
            for m in lock['models']:
                v=.5+(.1 if m=='weak' and s<=2 else 0)
                records.append(dict(group_id=g,seed=s,model=m,all_atom_lddt=v,ca_lddt=v,ca_aligned_rmsd=1.,geometry=dict(severe_pairs=0,strict_checked_chirality=True)))
    result=summarize_noise_transfer(records,lock)
    assert result['new_minus_seen_gain']['all_atom_lddt']['mean']==pytest.approx(-.1)
    with pytest.raises(ValueError):summarize_noise_transfer(records[:-1],lock)
