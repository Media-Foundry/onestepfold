"""Frozen pair generator: balanced multi-context training and direct S1 assessment."""
import argparse
import copy
import gzip
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import torch

from fastglycan import stage0_confirm_runtime as rt
from fastglycan.adapter_supervision import build_adapter_supervision
from fastglycan.deep_response_student import response_diagnostics
from fastglycan.factor_memorization import response_nmse
from fastglycan.factor_student_data import FactorTeacherStore
from fastglycan.functional_response_rank import (
    pack_conditioning, prepare_fidelity_pairs, response_geometry, response_structure_metrics,
)
from fastglycan.hip_device_policy import guarded_hip_runtime
from fastglycan.hybrid_proposals import identity_noise
from fastglycan.models.differentiable_mini import prepare_atom_pairs, diffusion_from_conditioning
from fastglycan.models.soft_sequence_chart import native_sequence_features, device_tree
from fastglycan.multicontext_response import (
    TRAIN_CONTEXTS, HELD_CONTEXTS, ALL_CONTEXTS, SNAPSHOTS, NOISES,
    context_role, exposure_counts, score_fidelity, noise_selection, chirality_trace,
)
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.response_readouts import NonlinearResponseReadout
from run_deep_validation_v2 import site_tensors
from run_global_response_rank import backbone_target_pairs, backbone_target_loss


def prepare_pair_multicontext(root):
    assert not (root/'lock.json').exists()
    teacher = root.parent/'factor_student_pilot_v1_20261002'
    old = rt.load_json(teacher/'teacher_lock.json')
    assert old['seeds'] == list(NOISES[:2])
    expected = {3: ('1w53', 84), 4: ('1jhg', 101), 5: ('1a7g', 82), 6: ('4pt4', 99)}
    for pi, pos in ALL_CONTEXTS:
        row = old['rows'][pi]
        assert (row['pdb_id'].lower(), len(row['sequence'])) == expected[pi]
        assert pos in row['positions']
    rows = copy.deepcopy(old['rows'])
    contexts = [dict(parent_index=pi, position=pos, role=context_role(pi, pos),
                     pdb_id=rows[pi]['pdb_id'], wt=rows[pi]['sequence'][pos]) for pi, pos in ALL_CONTEXTS]
    jobs = [dict(id=f'pair_raw_s{seed}', seed=seed, architecture='pair', label='raw',
                 train_sites=[list(x) for x in TRAIN_CONTEXTS], steps=32768, lr=.001,
                 weight_decay=.0001, initial_checkpoint=None) for seed in (231301, 231303)]
    lock = dict(schema='pair_multicontext_v1', teachers=str(teacher), rows=rows, contexts=contexts,
                aa=old['aa'], seeds=list(NOISES), gt=old['gt'], weights_sha256=old['weights_sha256'],
                teacher_lock_sha256=sha256(teacher/'teacher_lock.json'),
                teacher_manifest_sha256=sha256(teacher/'teacher_manifest.json'),
                jobs=jobs, snapshots=list(SNAPSHOTS), primary_step=32768,
                assignments=[[3], [4], [5], [6]], expected_s1_calls=6112,
                protocol_sha256=sha256(root/'code/docs/mini_pair_multicontext_v1.md'),
                code_hashes={str(p): sha256(p) for p in (root/'code').rglob('*')
                             if p.is_file() and p.suffix in ('.py', '.md', '.json')})
    write_json(root/'lock.json', lock)
    for job in jobs:
        write_json(root/'jobs'/f'{job["id"]}.json', job)


def verify_pair_lock(root):
    lock = rt.load_json(root/'lock.json')
    for p, h in lock['code_hashes'].items():
        assert sha256(Path(p)) == h, p
    for file, field in [('teacher_lock.json', 'teacher_lock_sha256'), ('teacher_manifest.json', 'teacher_manifest_sha256')]:
        assert sha256(Path(lock['teachers'])/file) == lock[field]
    return lock


def pair_predict(model, data):
    return model(data['s'], data['z'], data['pos'], data['wt'], data['ids'])


def train_pair_contexts(root, jobid):
    runtime = guarded_hip_runtime()
    lock = verify_pair_lock(root)
    job = rt.load_json(root/'jobs'/f'{jobid}.json')
    assert job['train_sites'] == [list(x) for x in TRAIN_CONTEXTS] and job['initial_checkpoint'] is None
    out = root/'runs'/jobid
    out.mkdir(parents=True, exist_ok=False)
    store = FactorTeacherStore(Path(lock['teachers']), training_only=True)
    data = [site_tensors(store, *site, oracle_floor=False) for site in TRAIN_CONTEXTS]
    torch.manual_seed(job['seed'])
    model = NonlinearResponseReadout('pair').cuda()
    assert sum(p.numel() for p in model.parameters()) == 3627904
    parameters = list(model.parameters())
    optimizer = torch.optim.AdamW(parameters, lr=job['lr'], weight_decay=job['weight_decay'], eps=1e-8)
    initial = out/'initial.pt'
    torch.save(dict(state_dict=model.state_dict(), job=job, step=0), initial)
    with torch.no_grad():
        assert pair_predict(model, data[0]).count_nonzero() == 0
    start = time.monotonic()
    report = dict(complete=False, job=job, runtime=runtime, parameters=3627904,
                  initial_sha256=sha256(initial), history=[], trace=[], s1_calls=0, c4_calls=0,
                  lock_sha256=sha256(root/'lock.json'))
    counts = [0]*4

    def snapshot(step):
        with torch.no_grad():
            metrics = [dict(parent_index=d['pi'], position=d['pos'],
                            **response_diagnostics(pair_predict(model, d), d['target'])) for d in data]
        row = dict(step=step, exposures=list(counts), sites=metrics, seconds=time.monotonic()-start)
        if step:
            path = out/f'checkpoint_{step}.pt'
            torch.save(dict(state_dict=model.state_dict(), optimizer=optimizer.state_dict(),
                            rng=torch.get_rng_state(), cuda_rng=torch.cuda.get_rng_state(),
                            job=job, step=step, exposures=list(counts)), path)
            row.update(checkpoint=str(path), sha256=sha256(path))
        report['history'].append(row)
        write_json(out/'report.json', report)

    snapshot(0)
    for step in range(1, 32769):
        index = (step-1) % 4
        d = data[index]
        optimizer.zero_grad(set_to_none=True)
        pred = pair_predict(model, d)
        loss = response_nmse(pred, d['target']).mean()
        loss.backward()
        gn = torch.nn.utils.clip_grad_norm_(parameters, 1., error_if_nonfinite=True)
        monitor = ((step-1)//4) % 64 == 63
        if monitor:
            before = [p.detach().clone() for p in parameters]
        optimizer.step()
        counts[index] += 1
        assert counts == exposure_counts(step)
        if monitor:
            with torch.no_grad():
                update = sum((p-b).double().square().sum() for p, b in zip(parameters, before))
                weight = sum(b.double().square().sum() for b in before)
            report['trace'].append(dict(step=step, parent_index=d['pi'], position=d['pos'],
                                        exposures=list(counts), loss=float(loss), gradient_norm=float(gn),
                                        update_weight_norm_ratio=float((update/weight.clamp_min(1e-30)).sqrt()),
                                        **response_diagnostics(pred, d['target'])))
            del before
            if index == 3:
                write_json(out/'report.json', report)
        if step in SNAPSHOTS:
            snapshot(step)
    torch.cuda.synchronize()
    report.update(complete=True, seconds=time.monotonic()-start,
                  peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                  candidate_exposures=32768*19, context_exposures=counts)
    write_json(out/'report.json', report)


def freeze_pair_endpoints(root):
    lock = verify_pair_lock(root)
    items = []
    for job in lock['jobs']:
        r = rt.load_json(root/'runs'/job['id']/'report.json')
        assert r['complete'] and r['context_exposures'] == [8192]*4
        assert [x['step'] for x in r['history']] == [0, *SNAPSHOTS]
        for row in r['history'][1:]:
            assert sha256(Path(row['checkpoint'])) == row['sha256']
            items.append(dict(arm=f'e{row["step"]//4}_s{job["seed"]}', job=job,
                              step=row['step'], path=row['checkpoint'], sha256=row['sha256'], terminal=row))
    assert len(items) == 6
    panel = dict(lock, checkpoints=items, arms=['exact', 'baseline', 'wt_z', 'oracle_r32']+[x['arm'] for x in items])
    assert not (root/'evaluation_lock.json').exists()
    write_json(root/'evaluation_lock.json', panel)


def decode_pair_contexts(root, index):
    runtime = guarded_hip_runtime()
    verify_pair_lock(root)
    lock = rt.load_json(root/'evaluation_lock.json')
    out = root/f'decoder_{index}'
    out.mkdir(exist_ok=False)
    start = time.monotonic()
    store = FactorTeacherStore(Path(lock['teachers']))
    runner = rt.runner_setup(out/'work')
    runner.configs.dtype = 'fp32'
    mini = runner.model.eval().requires_grad_(False)
    models = []
    for item in lock['checkpoints']:
        assert sha256(Path(item['path'])) == item['sha256']
        packet = torch.load(item['path'], map_location='cpu', weights_only=False)
        assert packet['step'] == item['step'] and packet['exposures'] == exposure_counts(item['step'])
        net = NonlinearResponseReadout('pair').cuda().eval().requires_grad_(False)
        net.load_state_dict(packet['state_dict'])
        models.append(net)
    counts = dict(s1=0, c4=0, old_replays=0, new_replays=0)
    def forbid(*args):
        counts['c4'] += 1
        raise AssertionError('no C4 allowed')
    def count_s1(*args):
        counts['s1'] += 1
    hooks = [mini.pairformer_stack.register_forward_pre_hook(forbid), mini.diffusion_module.register_forward_hook(count_s1)]
    def features(item):
        native, atoms = native_sequence_features(item['sequence'])
        inv = item['inventory']
        assert np.array_equal(atoms.atom_name, inv['atom_names'])
        assert np.array_equal(atoms.res_id, inv['residue_ids'])
        assert np.array_equal(atoms.bonds.as_array(), inv['bonds'])
        assert np.array_equal(native['ref_pos'].numpy(), inv['reference'])
        np.savez_compressed(out/f'{item["label"]}_inventory.npz', **inv)
        return prepare_atom_pairs(mini.relative_position_encoding.generate_relp(device_tree(native, 'cuda'))), atoms
    def decode_one(f, atoms, conditioning, seed):
        return diffusion_from_conditioning(mini, f, identity_noise(atoms, seed, device='cuda'),
                                           pack_conditioning(conditioning), steps=1).squeeze(0).cpu().numpy()
    def decode_all(f, atoms, conditioning):
        return np.stack([decode_one(f, atoms, conditioning, seed) for seed in NOISES])
    report = dict(complete=False, runtime=runtime, sites=[], latent=[], counts=counts,
                  evaluation_lock_sha256=sha256(root/'evaluation_lock.json'))
    with torch.no_grad():
        for pi in lock['assignments'][index]:
            row = lock['rows'][pi]
            wi = store.load(pi)
            wt = tuple(t.cuda() for t in wi['conditioning'])
            f, atoms = features(wi)
            co = decode_all(f, atoms, wt)
            assert np.array_equal(co[:2], wi['coordinates'])
            counts['old_replays'] += 2
            np.savez_compressed(out/f'p{pi}_wt_coordinates.npz', coordinates=co, seeds=NOISES)
            for pos in row['positions']:
                d = site_tensors(store, pi, pos, oracle_floor=False)
                preds = [pair_predict(net, d) for net in models]
                for item, pred in zip(lock['checkpoints'], preds):
                    m = response_diagnostics(pred, d['target'])
                    replay_error = None
                    if (pi, pos) in TRAIN_CONTEXTS:
                        old = next(x for x in item['terminal']['sites'] if (x['parent_index'], x['position']) == (pi, pos))
                        replay_error = float(np.max(np.abs(np.array(m['nmse'])-np.array(old['nmse']))))
                        assert replay_error < 1e-6
                    report['latent'].append(dict(parent_index=pi, position=pos, role=context_role(pi, pos),
                                                  arm=item['arm'], training_replay_error=replay_error, **m))
                site = dict(parent_index=pi, position=pos, role=context_role(pi, pos), mutants=[])
                for ai, j in enumerate(d['ids']):
                    item = store.load(pi, pos, lock['aa'][j])
                    f, atoms = features(item)
                    target = tuple(t.cuda() for t in item['conditioning'])
                    delta = target[2].double()-wt[2].double()
                    u, sigma, v = torch.linalg.svd(delta.permute(2, 0, 1), full_matrices=False)
                    oracle = (wt[2].double()+((u[:, :, :32]*sigma[:, None, :32])@v[:, :32]).permute(1, 2, 0)).float()
                    outputs = [decode_all(f, atoms, target), decode_all(f, atoms, (wt[0], target[1], target[2]))]
                    assert np.array_equal(outputs[0][:2], item['coordinates'][0])
                    assert np.array_equal(outputs[1][:2], item['coordinates'][1])
                    counts['old_replays'] += 4
                    if ai == 0:
                        for ni in (2, 3):
                            replay = decode_one(f, atoms, (wt[0], target[1], target[2]), NOISES[ni])
                            assert np.array_equal(replay, outputs[1][ni])
                            counts['new_replays'] += 1
                    for z in [wt[2], oracle, *[wt[2]+pred[ai] for pred in preds]]:
                        outputs.append(decode_all(f, atoms, (wt[0], target[1], z)))
                    path = out/f'{item["label"]}_coordinates.npz'
                    np.savez_compressed(path, coordinates=np.stack(outputs), arms=lock['arms'], seeds=NOISES)
                    site['mutants'].append(dict(aa=lock['aa'][j], label=item['label'], sha256=sha256(path)))
                    report.update(active=item['label'], seconds=time.monotonic()-start)
                    write_json(out/'report.json', report)
                report['sites'].append(site)
                del preds, d
    for hook in hooks:
        hook.remove()
    assert counts == dict(s1=1528, c4=0, old_replays=154, new_replays=4), counts
    report.update(complete=True, seconds=time.monotonic()-start, peak_allocated_bytes=torch.cuda.max_memory_allocated())
    write_json(out/'report.json', report)


def score_pair_contexts(root, index):
    torch.set_num_threads(1)
    lock = rt.load_json(root/'evaluation_lock.json')
    work = root/f'decoder_{index}'
    decoded = rt.load_json(work/'report.json')
    assert decoded['complete']
    out = root/f'scorer_{index}'
    out.mkdir(exist_ok=False)
    start = time.monotonic()
    results = []
    for site in decoded['sites']:
        pi, pos = site['parent_index'], site['position']
        row = lock['rows'][pi]
        info = lock['gt'][str(pi)]
        assert sha256(Path(info['path'])) == info['sha256']
        gt = dict(np.load(info['path']))
        gca = gt['atom_names'] == 'CA'
        y, observed = gt['coordinates'][gca], gt['mask'][gca]
        pairs, distance = backbone_target_pairs(y, observed)
        local = observed & (np.linalg.norm(y-y[pos], axis=1) < 8) if observed[pos] else np.zeros(len(y), bool)
        local |= abs(np.arange(len(y))-pos) <= 2
        wtindex = lock['aa'].index(row['sequence'][pos])
        tasks = np.empty((10, 4, 20))
        records = []
        for ai, aa in enumerate(lock['aa']):
            label = f'p{pi}_wt' if ai == wtindex else f'p{pi}_s{pos+1}_{aa}'
            path = work/f'{label}_coordinates.npz'
            if ai != wtindex:
                assert sha256(path) == next(x['sha256'] for x in site['mutants'] if x['aa'] == aa)
            co = np.load(path)['coordinates']
            if ai == wtindex:
                co = np.repeat(co[None], 10, axis=0)
            assert co.shape[:2] == (10, 4)
            inv = dict(np.load(work/f'{label}_inventory.npz'))
            ca = np.flatnonzero(inv['atom_names'] == 'CA')
            res = inv['residue_ids']
            assert np.array_equal(res[ca], np.arange(1, len(y)+1))
            labels = build_adapter_supervision(dict(inv, coordinates=co[0, 0], mask=np.ones(len(res), bool)),
                                               inv['bonds'], str(inv['sequence']))
            for ni, seed in enumerate(NOISES):
                refs = [co[0, ni], co[1, ni]]
                caches = [(prepare_fidelity_pairs(ref, res), prepare_fidelity_pairs(ref[ca], res[ca])) for ref in refs]
                basegeo = response_geometry(refs[1], labels)
                for ki, arm in enumerate(lock['arms']):
                    x = co[ki, ni]
                    tasks[ki, ni, ai] = float(backbone_target_loss(torch.tensor(x, dtype=torch.float64), ca, pairs, distance))
                    geometry = response_geometry(x, labels)
                    trace = chirality_trace(x, labels, inv, keep_all=(pi == 3 and pos == 36 and aa == 'N'))
                    assert len(trace['wrong']) == geometry['checked_chirality_wrong']
                    records.append(dict(arm=arm, aa=aa, noise=seed, is_wt=ai == wtindex,
                                        task=float(tasks[ki, ni, ai]), geometry=geometry, chirality=trace,
                                        new_failure=basegeo['zero_severe_strict_checked_chirality'] and not geometry['zero_severe_strict_checked_chirality'],
                                        recovered=not basegeo['zero_severe_strict_checked_chirality'] and geometry['zero_severe_strict_checked_chirality'],
                                        fidelity=response_structure_metrics(x, refs[0], ca, local, caches[0]),
                                        compression_fidelity=response_structure_metrics(x, refs[1], ca, local, caches[1])))
        ids = np.delete(np.arange(20), wtindex)
        names = [lock['aa'][j] for j in ids]
        rankings, selections = [], []
        for ki, arm in enumerate(lock['arms']):
            for refi, ref in [(0, 'exact'), (1, 'baseline')]:
                for ni, seed in enumerate(NOISES):
                    rankings.append(dict(arm=arm, reference=ref, noise=seed,
                                         **score_fidelity(tasks[refi, ni, ids], tasks[ki, ni, ids], names)))
                selections.append(dict(arm=arm, reference=ref,
                                       **noise_selection(tasks[refi][:, ids], tasks[ki][:, ids], names)))
        result = dict(parent_index=pi, pdb_id=row['pdb_id'], position=pos, role=context_role(pi, pos),
                      outputs=records, ranking=rankings, selections=selections)
        with gzip.open(out/f'p{pi}_s{pos+1}.json.gz', 'wt') as f:
            json.dump(result, f, allow_nan=False)
        results.append(result)
        write_json(out/'status.json', dict(complete=False, sites=len(results), seconds=time.monotonic()-start))
    with gzip.open(out/'report.json.gz', 'wt') as f:
        json.dump(dict(complete=True, sites=results, seconds=time.monotonic()-start), f, allow_nan=False)
    write_json(out/'status.json', dict(complete=True, sites=len(results), seconds=time.monotonic()-start))


def collect_pair_contexts(root):
    lock = rt.load_json(root/'evaluation_lock.json')
    sites, latent, decoders = [], [], []
    for index in range(4):
        d = rt.load_json(root/f'decoder_{index}/report.json')
        assert d['complete']
        decoders.append(d)
        latent += d['latent']
        with gzip.open(root/f'scorer_{index}/report.json.gz', 'rt') as f:
            r = json.load(f)
        assert r['complete']
        sites += r['sites']
    assert {(s['parent_index'], s['position']) for s in sites} == set(ALL_CONTEXTS)
    assert sum(x['counts']['s1'] for x in decoders) == 6112
    summary = {}
    for role in ('train', 'unseen_site', 'unseen_protein'):
        chosen = [s for s in sites if s['role'] == role]
        summary[role] = {}
        for arm in lock['arms']:
            parent_scores = {}
            for site in chosen:
                selection = next(x for x in site['selections'] if x['arm'] == arm and x['reference'] == 'baseline')
                parent_scores.setdefault(site['parent_index'], []).append(selection)
            group = dict(proteins=len(parent_scores), sites=len(chosen), aggregation={})
            for noisegroup in ('old', 'new', 'all'):
                group['aggregation'][noisegroup] = {}
                for metric in ('spearman', 'top1_regret', 'task_mae', 'task_rmse', 'top3_recall', 'top5_recall'):
                    perparent = {pi: float(np.mean([s['aggregate'][noisegroup][metric] for s in rows]))
                                 if all(s['aggregate'][noisegroup][metric] is not None for s in rows) else None
                                 for pi, rows in parent_scores.items()}
                    vals = [x for x in perparent.values() if x is not None]
                    group['aggregation'][noisegroup][metric] = dict(per_protein=perparent, mean=float(np.mean(vals)) if vals else None,
                                                                   valid_proteins=len(vals))
                group['aggregation'][noisegroup]['top1_sites'] = sum(s['aggregate'][noisegroup]['top1_match'] for rows in parent_scores.values() for s in rows)
            rows = [x for site in chosen for x in site['outputs'] if x['arm'] == arm and not x['is_wt']]
            rms = np.array([x['compression_fidelity']['local_ca_rmsd_global_frame'] for x in rows])
            group.update(instances=len(rows), geometry_pass=sum(x['geometry']['zero_severe_strict_checked_chirality'] for x in rows),
                         new_failures=sum(x['new_failure'] for x in rows), recovered=sum(x['recovered'] for x in rows),
                         local_mean=float(rms.mean()), local_p95=float(np.quantile(rms, .95)),
                         local_p99=float(np.quantile(rms, .99)), local_max=float(rms.max()), local_over1=int((rms > 1).sum()))
            summary[role][arm] = group
    with gzip.open(root/'report.json.gz', 'wt') as f:
        json.dump(dict(complete=True, summary=summary, sites=sites, latent=latent), f, allow_nan=False)
    write_json(root/'summary.json', dict(complete=True, summary=summary, primary_step=32768,
                                        oracle_target_s=True, deployment_accepted=False, training_extension=False))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--mode', choices=['prepare', 'train', 'freeze', 'decode', 'score', 'collect'], required=True)
    p.add_argument('--job')
    p.add_argument('--index', type=int, default=0)
    a = p.parse_args()
    if a.mode == 'prepare': prepare_pair_multicontext(a.root)
    elif a.mode == 'train': train_pair_contexts(a.root, a.job)
    elif a.mode == 'freeze': freeze_pair_endpoints(a.root)
    elif a.mode == 'decode': decode_pair_contexts(a.root, a.index)
    elif a.mode == 'score': score_pair_contexts(a.root, a.index)
    else: collect_pair_contexts(a.root)
