"""Preflight and fixed-budget complete-structure Mini editor learning curve."""
import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch

from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.reference_editor_multiref import (
    paired_reference_editor, editor_state_digest, multiref_update,
)
from fastglycan.reference_editor_runtime import MiniEditorRuntime, editor_cache_audit, gradient_inventory
from run_reference_editor import coordinate_objective, state_hash


def preflight_multiref(root):
    started = time.monotonic()
    rt = MiniEditorRuntime(root, 'preflight_work', building=True)
    (root / 'packets').mkdir()
    (root / 'baseline').mkdir()
    report = dict(complete=False, runtime=rt.runtime, counts=rt.counts, replay=[],
                  gradient_audits=[], baseline=[], lock_sha256=sha256(root / 'lock.json'))
    with torch.no_grad():
        for pi, reference in rt.references.items():
            item = rt.build_packet(pi)
            for ni in range(2):
                assert torch.equal(rt.decode(item, reference, ni), item['teacher'][ni]), (pi, ni)
        for site in rt.plan['sites']:
            pi, pos = site['parent_index'], site['position_zero_based']
            for aa in site['candidates']:
                item = rt.build_packet(pi, pos, aa)
                path = rt.store.path(pi, item['label'], 'conditioning.pt')
                exact_state = torch.load(path, map_location='cpu', weights_only=False)
                conditioning = tuple(t.cuda() for t in exact_state['conditioning'])
                for ni in range(2):
                    assert torch.equal(rt.decode(item, conditioning, ni), item['teacher'][ni]), (item['label'], ni)
                del exact_state, conditioning
                baseline = np.stack([rt.decode(item, rt.references[pi], ni).cpu().numpy() for ni in range(2)])
                path = root / 'baseline' / f"{item['label']}.npz"
                np.savez_compressed(path, coordinates=baseline)
                report['baseline'].append(dict(label=item['label'], path=str(path.relative_to(root)), sha256=sha256(path)))
                report['replay'].append(item['label'])
            report['seconds'] = time.monotonic() - started
            write_json(root / 'preflight.json', report)
            print('PREFLIGHT_SITE', site['site_key'], len(report['replay']), rt.counts, flush=True)
    assert len(report['replay']) == len(set(report['replay'])) == 912
    assert all('_wt' in k for k in rt.store.cache), 'target conditioning persisted in store'
    write_json(root / 'packet_manifest.json', rt.packet_manifest)
    initializations = {}
    site = rt.sites['p3_s37']
    for seed in (272001, 272003):
        common_digest = None
        for arch in ('workspace', 'direct_global'):
            net = paired_reference_editor(arch, seed)
            digest = editor_state_digest(net, True)
            if common_digest is not None:
                assert digest == common_digest
            common_digest = digest
            record = dict(seed=seed, architecture=arch, full_sha256=editor_state_digest(net), shared_sha256=digest)
            initializations[f'{arch}_{seed}'] = record
            net = net.cuda()
            invariants = editor_cache_audit(net, rt)
            ref = net.prepare_reference(rt.references[3], rt.sequences[3])
            choices = list(site['candidates'][:2])
            conditioning = net(ref, rt.edits(site, choices))
            losses = []
            for i, aa in enumerate(choices):
                item = rt.item(3, 36, aa)
                x = rt.decode(item, tuple(t[i] for t in conditioning), 0)
                losses.append(coordinate_objective(x, item['teacher'][0], item['ca'], item['labels'])[0])
            loss = torch.stack(losses).mean()
            assert torch.isfinite(loss)
            loss.backward()
            audit = gradient_inventory(net, arch)
            assert audit['registered'] == (9352387 if arch == 'workspace' else 9320643)
            assert all(p.grad is None for p in rt.decoder.parameters())
            report['gradient_audits'].append(dict(**record, invariants=invariants, gradients=audit, loss=float(loss)))
            del net, ref, conditioning, x, loss, losses
    rt.finish_checks()
    assert rt.counts == dict(c4=0, input_embedder=0, s1=3708, updates=0), rt.counts
    report.update(complete=True, seconds=time.monotonic()-started,
                  initializations=initializations, packet_manifest_sha256=sha256(root/'packet_manifest.json'),
                  peak_allocated_bytes=torch.cuda.max_memory_allocated())
    write_json(root/'preflight.json', report)
    print('PREFLIGHT_COMPLETE', rt.counts, report['seconds'], flush=True)


def evaluate_multiref(net, optimizer, rt, run, output, step, initialization):
    begin = time.monotonic()
    net.eval()
    invariants = editor_cache_audit(net, rt)
    records = []
    with torch.no_grad():
        for pi in sorted(rt.references):
            ref = net.prepare_reference(rt.references[pi], rt.sequences[pi])
            for site in rt.plan['sites']:
                if site['parent_index'] != pi:
                    continue
                choices = site['candidates']
                for start in range(0, 19, 4):
                    aas = choices[start:start+4]
                    conditioning = net(ref, rt.edits(site, aas))
                    for i, aa in enumerate(aas):
                        item = rt.item(pi, site['position_zero_based'], aa)
                        xyz = np.stack([rt.decode(item, tuple(t[i] for t in conditioning), ni).cpu().numpy() for ni in range(2)])
                        assert np.isfinite(xyz).all()
                        path = output/'coordinates'/f"{step}_{item['label']}.npz"
                        np.savez_compressed(path, coordinates=xyz)
                        records.append(dict(label=item['label'], path=str(path.relative_to(output)), sha256=sha256(path)))
                    del conditioning
            del ref
    path = output/'checkpoints'/f'{step}.pt'
    torch.save(dict(state_dict=net.state_dict(), optimizer=optimizer.state_dict(), architecture=run['architecture'],
                    config=net.config, run=run, step=step, initialization=initialization,
                    lock_sha256=sha256(rt.root/'lock.json')), path)
    assert len(records) == 912
    result = dict(step=step, predictions=records, invariants=invariants,
                  checkpoint=str(path.relative_to(output)), sha256=sha256(path),
                  seconds=time.monotonic()-begin, counts=dict(rt.counts))
    write_json(output/f'evaluation_{step}.json', result)
    print('EVALUATE', run['run_id'], step, rt.counts, flush=True)
    return {k: v for k, v in result.items() if k != 'predictions'}


def time_multiref(net, rt):
    net.eval()
    site = rt.sites['p3_s37']
    choices = site['candidates']
    results = []
    with torch.no_grad():
        # Prime prepared chemistry to avoid charging disk/native preparation to S1.
        items = [rt.item(3, 36, aa) for aa in choices]
        for repeat in range(6):
            torch.cuda.synchronize(); t = time.perf_counter()
            ref = net.prepare_reference(rt.references[3], rt.sequences[3])
            torch.cuda.synchronize(); projection = time.perf_counter()-t
            t = time.perf_counter()
            conditioning = net(ref, rt.edits(site, choices))
            torch.cuda.synchronize(); edit = time.perf_counter()-t
            t = time.perf_counter()
            for i, item in enumerate(items):
                rt.decode(item, tuple(x[i] for x in conditioning), 0)
            torch.cuda.synchronize(); decode = time.perf_counter()-t
            results.append(dict(repeat=repeat, projection_seconds=projection, edit19_seconds=edit,
                                s1_19_seconds=decode, combined_seconds=projection+edit+decode))
    return results


def train_multiref(root, run_id):
    started = time.monotonic()
    rt = MiniEditorRuntime(root, f'work_{run_id}')
    run = next(r for r in rt.plan['runs'] if r['run_id'] == run_id)
    output = root/'runs'/run_id
    output.mkdir(parents=True, exist_ok=False)
    (output/'coordinates').mkdir(); (output/'checkpoints').mkdir()
    net = paired_reference_editor(run['architecture'], run['seed'])
    initialization = dict(full_sha256=editor_state_digest(net), shared_sha256=editor_state_digest(net, True))
    expected = json.loads((root/'preflight.json').read_text())['initializations'][f"{run['architecture']}_{run['seed']}"]
    assert all(initialization[k] == expected[k] for k in initialization)
    net = net.cuda()
    optimizer = torch.optim.AdamW(net.parameters(), lr=1e-4, weight_decay=1e-4, eps=1e-8)
    references_before = {pi: state_hash(x) for pi, x in rt.references.items()}
    report = dict(complete=False, run=run, runtime=rt.runtime, initialization=initialization,
                  evaluations=[], counts=rt.counts, parameters=sum(p.numel() for p in net.parameters()),
                  lock_sha256=sha256(root/'lock.json'), seconds=0)
    write_json(output/'report.json', report)
    checkpoints = set(run['checkpoints'])
    if run['additional_equal_update_checkpoint'] is not None:
        checkpoints.add(run['additional_equal_update_checkpoint'])
    report['evaluations'].append(evaluate_multiref(net, optimizer, rt, run, output, 0, initialization))
    write_json(output/'report.json', report)
    exposure = {k: {a: 0 for a in rt.sites[k]['candidates']} for k in run['train_site_keys']}
    with (output/'history.jsonl').open('w', buffering=1) as history:
        for step in range(run['updates']):
            net.train(); optimizer.zero_grad(set_to_none=True)
            site, choices = multiref_update(run, rt.sites, step)
            pi, pos = site['parent_index'], site['position_zero_based']
            assert site['site_key'] in run['train_site_keys']
            ref = net.prepare_reference(rt.references[pi], rt.sequences[pi])
            conditioning = net(ref, rt.edits(site, choices))
            losses, components = [], []
            for i, aa in enumerate(choices):
                item = rt.item(pi, pos, aa)
                x = rt.decode(item, tuple(t[i] for t in conditioning), 0)
                loss, values = coordinate_objective(x, item['teacher'][0], item['ca'], item['labels'])
                losses.append(loss); components.append(values)
                exposure[site['site_key']][aa] += 1
            loss = torch.stack(losses).mean()
            assert torch.isfinite(loss), (step, site, choices)
            loss.backward()
            if step == 0:
                report['gradient_audit'] = gradient_inventory(net, run['architecture'])
                assert all(p.grad is None for p in rt.decoder.parameters())
            norm = torch.nn.utils.clip_grad_norm_(net.parameters(), 1., error_if_nonfinite=True)
            energy = None
            if step % 64 == 0:
                energy = [float((x.detach()-r).square().mean()) for x, r in zip(conditioning, rt.references[pi])]
            optimizer.step(); rt.counts['updates'] += 1
            try:
                net(ref, [[]])
            except RuntimeError:
                pass
            else:
                raise AssertionError('stale reference cache accepted')
            history.write(json.dumps(dict(step=step+1, site=site['site_key'], aa=choices,
                           loss=float(loss.detach()), gradient_norm=float(norm), clipped=bool(norm > 1),
                           components=components, response_mean_square=energy), allow_nan=False)+'\n')
            del ref, conditioning, x, loss, losses
            if (step+1) % 128 == 0:
                report['seconds'] = time.monotonic()-started
                write_json(output/'report.json', report)
                print('TRAIN', run_id, step+1, report['seconds'], flush=True)
            if step+1 in checkpoints:
                report['evaluations'].append(evaluate_multiref(net, optimizer, rt, run, output, step+1, initialization))
                write_json(output/f'exposure_{step+1}.json', exposure)
                write_json(output/'report.json', report)
    assert all(n == 64 for row in exposure.values() for n in row.values())
    report['timing'] = time_multiref(net, rt)
    rt.finish_checks()
    assert references_before == {pi: state_hash(x) for pi, x in rt.references.items()}
    expected_s1 = 2*run['updates'] + len(checkpoints)*(1824+1) + 6*19
    assert rt.counts == dict(c4=0, input_embedder=0, s1=expected_s1, updates=run['updates']), rt.counts
    report.update(complete=True, seconds=time.monotonic()-started, reference_hashes=references_before,
                  peak_allocated_bytes=torch.cuda.max_memory_allocated(), exposure=exposure,
                  history_sha256=sha256(output/'history.jsonl'))
    write_json(output/'report.json', report)
    print('TRAIN_COMPLETE', run_id, rt.counts, report['seconds'], flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--mode', choices=['preflight', 'train'], required=True)
    p.add_argument('--run-id')
    args = p.parse_args(); started = time.monotonic()
    status = args.root/('preflight_execution.json' if args.mode == 'preflight' else f'execution_{args.run_id}.json')
    try:
        if args.mode == 'preflight':
            preflight_multiref(args.root)
        else:
            train_multiref(args.root, args.run_id)
        write_json(status, dict(complete=True, seconds=time.monotonic()-started))
    except BaseException as error:
        write_json(status, dict(complete=False, error=repr(error), seconds=time.monotonic()-started))
        raise
