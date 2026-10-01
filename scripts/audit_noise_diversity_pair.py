#!/usr/bin/env python3
"""Audit the fixed/diverse terminal pair; retain the original parameter/loss/history checks."""
import argparse
import collections
import json
import math
from pathlib import Path
import numpy as np
import torch
from fastglycan.rocm_matched_training import verify_rocm_matched_lock, validate_rocm_pair, BASE_LOCK_SHA256
from fastglycan.folding_scale import PARENT_SHA256, folding_scale_lr
from fastglycan.paired_teacher_protocol import sha256, write_json


def audit_noise_diversity_pair(root):
    torch.set_num_threads(1)
    base_root = root.parent/'folding_global_distance_training_v1_20260930'
    assert sha256(base_root/'lock.json') == BASE_LOCK_SHA256
    base = json.loads((base_root/'lock.json').read_text())
    locks = {a: json.loads((root/a/'lock.json').read_text()) for a in ['fixed', 'diverse']}
    preflights = {a: json.loads((root/a/'preflight/report.json').read_text()) for a in locks}
    plan = json.loads((root/'cache_plan.json').read_text())
    control = json.loads((Path(plan['control'])/'lock.json').read_text())
    a, b = locks['fixed'], locks['diverse']
    assert all(a[k] == b[k] for k in a if k not in ['orders','noise_diversity'])
    assert a['orders'] == control['orders']
    assert b['orders']['expanded'] == [dict(x,seed=1800000+i) for i,x in enumerate(a['orders']['expanded'],1)]
    assert preflights['fixed']['initial_sha256'] == preflights['diverse']['initial_sha256']
    execution = json.loads((root/'controller_execution.json').read_text())
    assert execution['complete'] and len(execution['jobs']) == 15
    assert {j['label'] for j in execution['jobs']} == {f'teacher_{i}' for i in range(8)} | {'teacher_collect'} | {f'{m}_{a}' for a in locks for m in ['prepare','preflight','train']}
    assert all(j['exit_code'] == 0 for j in execution['jobs'])
    release = json.loads((root/'pair_release.json').read_text()); assert release['complete']
    summary, checkpoints, starts = {}, {}, {}
    verified = {}
    for arm, lock in locks.items():
        assert lock['noise_diversity']['arm'] == arm and lock['weights'] == control['weights']
        assert release['locks'][arm] == sha256(root/arm/'lock.json')
        own_release = json.loads((root/arm/'release.json').read_text())
        assert own_release['lock_sha256'] == sha256(root/arm/'lock.json')
        assert own_release['preflight_sha256'] == sha256(root/arm/'preflight/report.json')
        for p, digest in lock['hashes'].items():
            if p not in verified: verified[p] = sha256(Path(p))
            assert verified[p] == digest, p
        folder = root/arm/'expanded'; report = json.loads((folder/'report.json').read_text())
        assert report['complete'] and report['updates'] == 2048 and report['exposures'] == 8192
        assert report['lock_sha256'] == sha256(root/arm/'lock.json') and not report['validation_read']
        assert report['counts'] == dict(pairformer=0, diffusion=8448)
        assert report['excluded_parameters_unchanged'] and report['selected_names'] == lock['selected_names']
        assert report['initial_sha256'] == sha256(folder/'initial_fingerprints.json') == preflights[arm]['initial_sha256']
        assert report['initial_sha256'] == sha256(base_root/'expanded/initial_fingerprints.json')
        assert sha256(folder/'history.jsonl') == report['history_sha256']
        history = [json.loads(s) for s in (folder/'history.jsonl').read_text().splitlines()]
        assert len(history) == len(lock['orders']['expanded']) == 8192
        counts = collections.Counter()
        for i, (x,y) in enumerate(zip(history,lock['orders']['expanded']),1):
            assert x['exposure'] == i and all(x[k] == y[k] for k in ['group_id','epoch','seed'])
            counts[x['group_id']] += 1
            assert set(x['parts']) == set(lock['weights']) and all(math.isfinite(v) for v in x['parts'].values())
            assert math.isclose(x['loss'],sum(lock['weights'][k]*v for k,v in x['parts'].items()),rel_tol=1e-6,abs_tol=1e-8)
            if i%4 == 0:
                assert x['update'] == i//4 and abs(x['lr']-folding_scale_lr(i//4,lock['learning_rate'],2048)) < 1e-18
                assert math.isfinite(x['unclipped_accumulated_grad_norm'])
            else: assert 'update' not in x
        assert set(counts) == set(lock['arms']['expanded']) and len(counts) == 423
        curves = []
        for update in lock['probe_updates']:
            path = folder/f'probe_{update:04d}'; p = json.loads((path/'report.json').read_text())
            assert p['update'] == update and p['role'] == 'train_probe_only' and len(p['records']) == 64
            assert {(x['group_id'],x['seed']) for x in p['records']} == {(g,s) for g in lock['probe_groups'] for s in lock['training_seeds']}
            coordinates = {}
            for x in p['records']:
                file = path/f'{x["group_id"]}_{x["seed"]}.npy'; assert sha256(file) == x['sha256']
                v = np.load(file); assert v.dtype == np.float32 and v.ndim == 2 and v.shape[1] == 3 and np.isfinite(v).all()
                coordinates[file.name] = x['sha256']
            if update == 0: starts[arm] = coordinates
            curves.append({k:v for k,v in p.items() if k != 'records'})
        file = folder/'update_2048.pt'; assert sha256(file) == report['terminal_sha256']
        state = torch.load(file,map_location='cpu',weights_only=False)
        assert state['schema'] == lock['checkpoint_schema'] and state['arm'] == 'expanded'
        assert state['lock_sha256'] == sha256(root/arm/'lock.json') and state['parent_sha256'] == PARENT_SHA256
        assert state['update'] == 2048 and state['exposures'] == 8192
        assert list(state['trained']) == lock['selected_names'] and len(state['trained']) == 288
        assert sum(v.numel() for v in state['trained'].values()) == 69777841
        assert all(torch.isfinite(v).all() for v in state['trained'].values())
        assert len(state['optimizer']['state']) == 288
        assert all(int(v['step']) == 2048 and torch.isfinite(v['exp_avg']).all() and torch.isfinite(v['exp_avg_sq']).all() for v in state['optimizer']['state'].values())
        group, = state['optimizer']['param_groups']
        assert group['betas'] == (.9,.999) and group['eps'] == 1e-8 and group['weight_decay'] == 0 and group['lr'] == 1e-6
        checkpoints[arm] = dict(path=str(file),sha256=sha256(file)); del state
        summary[arm] = dict(curves=curves,seconds=report['seconds'],peak_gpu_bytes=report['peak_gpu_bytes'],
            exposure_min=min(counts.values()),exposure_max=max(counts.values()),
            clipped_updates=sum(x.get('unclipped_accumulated_grad_norm',0)>1 for x in history),
            coefficient=lock['weights']['global_distance'])
    assert starts['fixed'] == starts['diverse']
    write_json(root/'terminal_audit.json',dict(complete=True,checkpoints=checkpoints,summary=summary,
        training_locks={a:sha256(root/a/'lock.json') for a in locks},
        inputs={str(root/'controller_execution.json'):sha256(root/'controller_execution.json'),**verified},
        same_protein_epoch_order=True,only_noise_order_changed=True,initial_probe_exact_coordinates=64,validation_read=False,
        script_sha256=sha256(Path(__file__)),scope='terminal execution and TRAIN probes, not held-out quality'))


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    audit_noise_diversity_pair(p.parse_args().root)
