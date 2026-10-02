"""Independent CPU checks after the bounded run; never train or call the decoder."""
import argparse
import gzip
import json
from pathlib import Path

import numpy as np
import torch
from scipy.stats import spearmanr

from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.response_readouts import NonlinearResponseReadout
from fastglycan.scaling_metrics import lddt_observed


def audit_pair_multicontext(root):
    torch.set_num_threads(1)
    load = lambda p: json.loads(p.read_text())
    assert load(root/'execution.json')['complete']
    lock = load(root/'evaluation_lock.json')
    for p, h in lock['code_hashes'].items():
        assert sha256(Path(p)) == h
    initial_checks, checkpoint_checks = [], []
    for job in lock['jobs']:
        run = root/'runs'/job['id']
        r = load(run/'report.json')
        assert r['complete'] and r['context_exposures'] == [8192]*4
        assert len(r['trace']) == 512
        assert {(x['parent_index'], x['position']) for x in r['trace']} == {(3, 36), (3, 83), (4, 1), (5, 64)}
        assert sha256(run/'initial.pt') == r['initial_sha256']
        initial = torch.load(run/'initial.pt', map_location='cpu', weights_only=False)
        torch.manual_seed(job['seed'])
        net = NonlinearResponseReadout('pair')
        assert all(torch.equal(value, initial['state_dict'][name]) for name, value in net.state_dict().items())
        initial_checks.append(dict(seed=job['seed'],fresh_seed_initialization_exact=True))
    for item in lock['checkpoints']:
        assert sha256(Path(item['path'])) == item['sha256']
        packet = torch.load(item['path'], map_location='cpu', weights_only=False)
        assert packet['step'] == item['step'] and packet['exposures'] == [item['step']//4]*4
        steps = [int(x['step']) for x in packet['optimizer']['state'].values()]
        assert steps and min(steps) == max(steps) == item['step']
        checkpoint_checks.append(dict(arm=item['arm'],sha256=item['sha256'],optimizer_steps=sorted(set(steps)),exposures=packet['exposures']))
    with gzip.open(root/'report.json.gz', 'rt') as f:
        result = json.load(f)
    rank_checks = selection_checks = coordinate_task_checks = lddt_checks = centre_checks = 0
    manifest = []
    for worker in range(4):
        for p in sorted((root/f'decoder_{worker}').glob('*_coordinates.npz')):
            manifest.append(dict(path=str(p), sha256=sha256(p)))
    assert len(manifest) == 156
    for site in result['sites']:
        pi, pos = site['parent_index'], site['position']
        wt = lock['rows'][pi]['sequence'][pos]
        names = [aa for aa in lock['aa'] if aa != wt]
        tasks = {(arm, seed): np.array([next(x['task'] for x in site['outputs'] if x['arm'] == arm and x['noise'] == seed and x['aa'] == aa) for aa in names])
                 for arm in lock['arms'] for seed in lock['seeds']}
        for r in site['ranking']:
            x, y = tasks[r['arm'], r['noise']], tasks[r['reference'], r['noise']]
            order = np.argsort(x, kind='stable'); exact = np.argsort(y, kind='stable')
            assert abs(float(spearmanr(x, y).statistic)-r['spearman']) < 1e-12
            assert bool(order[0] == exact[0]) == r['top1_match']
            assert abs(float(y[order[0]]-y.min())-r['top1_regret']) < 1e-12
            assert abs(float(np.mean(abs(x-y)))-r['task_mae']) < 1e-12
            for k in (3, 5):
                assert len(set(order[:k]) & set(exact[:k]))/k == r[f'top{k}_recall']
                assert bool(exact[0] in order[:k]) == r[f'teacher_best_in_top{k}']
            rank_checks += 1
        for r in site['selections']:
            x = np.stack([tasks[r['arm'], seed] for seed in lock['seeds']])
            y = np.stack([tasks[r['reference'], seed] for seed in lock['seeds']])
            for name, ids in [('old', [0, 1]), ('new', [2, 3]), ('all', [0, 1, 2, 3])]:
                xx, yy = x[ids].mean(0), y[ids].mean(0)
                observed = r['aggregate'][name]
                assert abs(float(spearmanr(xx, yy).statistic)-observed['spearman']) < 1e-12
                assert names[int(np.argmin(xx))] == observed['student_choice']
                assert abs(float(yy[np.argmin(xx)]-yy.min())-observed['top1_regret']) < 1e-12
                selection_checks += 1
            ix, iy = int(np.argmin(x[:2].mean(0))), int(np.argmin(y[:2].mean(0)))
            yy = y[2:].mean(0)
            assert r['cross_noise']['student_old_choice'] == names[ix]
            assert abs(r['cross_noise']['extra_regret_vs_teacher_old_choice']-float(yy[ix]-yy[iy])) < 1e-12
        worker = next(i for i, parents in enumerate(lock['assignments']) if pi in parents)
        work = root/f'decoder_{worker}'
        gt = dict(np.load(lock['gt'][str(pi)]['path']))
        gy = np.asarray(gt['coordinates'][gt['atom_names'] == 'CA'], float)
        obs = gt['mask'][gt['atom_names'] == 'CA']
        ij = np.array(np.triu_indices(len(gy), 3)).T
        ij = ij[obs[ij].all(1)]
        distances = np.linalg.norm(gy[ij[:, 0]]-gy[ij[:, 1]], axis=1)
        # Fixed two AA per site, every arm/noise; independent NumPy task and lDDT.
        for aa in names[:2]:
            label = f'p{pi}_s{pos+1}_{aa}'
            co = np.load(work/f'{label}_coordinates.npz')['coordinates']
            inv = dict(np.load(work/f'{label}_inventory.npz'))
            ca = np.flatnonzero(inv['atom_names'] == 'CA')
            for ai, arm in enumerate(lock['arms']):
                for ni, seed in enumerate(lock['seeds']):
                    x = np.asarray(co[ai, ni], float)
                    error = abs(np.linalg.norm(x[ca[ij[:, 0]]]-x[ca[ij[:, 1]]], axis=1)-distances)
                    task = np.where(error <= 1, .5*error**2, error-.5).mean()
                    expected = next(v for v in site['outputs'] if v['arm'] == arm and v['aa'] == aa and v['noise'] == seed)
                    assert abs(float(task)-expected['task']) < 1e-12
                    coordinate_task_checks += 1
                    value = lddt_observed(x, co[1, ni], inv['residue_ids'])['score']
                    assert abs(value-expected['compression_fidelity']['all_atom_lddt']) < 1e-12
                    lddt_checks += 1
        for x in site['outputs']:
            assert len(x['chirality']['wrong']) == x['geometry']['checked_chirality_wrong']
            for centre in x['chirality'].get('all_centres', x['chirality']['wrong']):
                assert (centre['signed_volume']*centre['reference_volume'] <= 0) == centre['wrong']
                centre_checks += 1
    old_path = root.parent/'readout_endpoint_decode_v1_20261002/functional/endpoints/worker_0/p3_s37_scores.json'
    old = load(old_path)
    site = next(s for s in result['sites'] if (s['parent_index'], s['position']) == (3, 36))
    reference_checks = 0
    for x in site['outputs']:
        if x['arm'] not in ['exact', 'baseline', 'wt_z', 'oracle_r32'] or x['noise'] not in lock['seeds'][:2]:
            continue
        y = next(y for y in old['outputs'] if (y['arm'], y['aa'], y['noise']) == (x['arm'], x['aa'], x['noise']))
        assert all(x[k] == y[k] for k in ['task', 'geometry', 'fidelity', 'compression_fidelity'])
        reference_checks += 1
    write_json(root/'coordinate_manifest.json', manifest)
    write_json(root/'independent_audit.json', dict(complete=True, fresh_initializations=initial_checks,
               checkpoints=checkpoint_checks, ranking_checks=rank_checks, selection_checks=selection_checks,
               independent_coordinate_task_checks=coordinate_task_checks, independent_lddt_checks=lddt_checks,
               chirality_sign_checks=centre_checks, prior_reference_score_checks=reference_checks,
               coordinate_packets=len(manifest), audit_source_sha256=sha256(Path(__file__))))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--root', type=Path, required=True)
    audit_pair_multicontext(p.parse_args().root)
