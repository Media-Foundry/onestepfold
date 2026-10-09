"""Fresh single-site fits with the unchanged two-block pair recovery model."""
import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch

from fastglycan.models.pair_recovery import PairRecovery
from fastglycan.pair_recovery_data import PairRecoveryData
from fastglycan.pair_candidate_fit import (
    FIT_SITE, FIT_NODES, candidate_pair, expected_exposures, validate_fit_site, gradient_groups,
)
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.reference_editor_multiref import editor_state_digest
from fastglycan.response_moments import ResponseMoments
from run_recycle_lora import LoRARuntime
from run_reference_editor import state_hash


def fit_one_context(root, arm, seed):
    start = time.monotonic()
    lock = json.loads((root / 'training_lock.json').read_text())
    for path, digest in lock['code'].items():
        assert sha256(root / 'code' / path) == digest, path
    assert sha256(root / 'protocol.md') == lock['protocol_sha256']
    previous = Path(lock['source_training_root'])
    assert sha256(previous / 'training_lock.json') == lock['source_lock_sha256']
    old = json.loads((previous / 'training_lock.json').read_text())
    assert sha256(previous / 'preflight.json') == old['preflight_sha256']
    assert lock['checkpoints'] == list(FIT_NODES) and lock['updates'] == 8208
    rt = LoRARuntime(Path(lock['source']), str(root / f'work_{arm}_{seed}'))
    b = rt.base
    torch.set_num_threads(1)
    site = b.sites[FIT_SITE]
    q = lock['site_scale_squared'][FIT_SITE]
    validate_fit_site(site, old['train_sites'], q)
    pi, pos, choices = site['parent_index'], site['position_zero_based'], site['candidates']
    data = PairRecoveryData(lock['build_root'], lock['cache_manifest_sha256'])
    # Both are immutable resident copies. Only the actual candidate B enters net.
    bases = {aa: data.base(b.label(pi, pos, aa)) for aa in choices}
    targets = {aa: data.target(b.label(pi, pos, aa)) for aa in choices}
    assert all(not t.requires_grad for v in bases.values() for t in v)
    assert all(not t.requires_grad for t in targets.values())
    data_seconds = time.monotonic() - start
    reference = rt.prefixes[pi][0][1]
    input_guard = {aa: state_hash(bases[aa]) for aa in choices}
    target_guard = state_hash(tuple(targets.values()))
    prefix_guard = {p: state_hash(v[0]) for p, v in rt.prefixes.items()}
    net = PairRecovery(list(rt.model.pairformer_stack.blocks[-2:]), arm, seed).cuda()
    initial = editor_state_digest(net)
    expected = json.loads((previous / 'preflight.json').read_text())['models'][f'{arm}_{seed}']
    assert initial == expected['initial_sha256']
    initial_parameters = {name: param.detach().clone() for name, param in net.named_parameters()}
    optimizer = torch.optim.AdamW(net.parameters(), lr=lock['lr'], weight_decay=1e-4, eps=1e-8)
    folder = root / 'runs' / arm / str(seed)
    folder.mkdir(parents=True, exist_ok=False)
    for name in ('checkpoints', 'coordinates', 'residuals'):
        (folder / name).mkdir()
    exposure = dict.fromkeys(choices, 0)
    report = dict(complete=False, arm=arm, seed=seed, site=FIT_SITE,
                  initial_sha256=initial, parameters=sum(p.numel() for p in net.parameters()),
                  counts=b.counts, runtime=b.runtime, data_seconds=data_seconds,
                  feature_forwards=0, training_forward_count=0, evaluation_forward_count=0,
                  gradient_audits=[], site_scale_squared=q)

    def predict(aa):
        c = net(bases[aa], reference, pos, b.aa.index(site['original_aa']), b.aa.index(aa))
        assert c[0] is bases[aa][0] and c[1] is bases[aa][1]
        report['feature_forwards'] += 1
        return c

    def evaluate(step):
        begin = time.monotonic()
        net.eval()
        records, candidate_stats, residuals = [], [], {}
        moments, mismatched = ResponseMoments(), ResponseMoments()
        objective = 0.
        with torch.no_grad():
            for aa in choices:
                c = predict(aa)
                report['evaluation_forward_count'] += 1
                base = bases[aa]
                if step == 0:
                    assert all(torch.equal(x, y) for x, y in zip(c, base))
                    assert net(base, reference, pos, 0, 0) is base
                p, e = c[2] - base[2], targets[aa] - base[2]
                moments.add(p, e)
                single = ResponseMoments(); single.add(p, e)
                candidate_stats.append(dict(aa=aa, moments=single.result()))
                objective += float((c[2] - targets[aa]).square().mean() / q) / 19
                residuals[aa] = p.detach().clone()
                item = b.item(pi, pos, aa)
                xyz = np.stack([b.decode(item, c, ni).cpu().numpy() for ni in (0, 1)])
                assert np.isfinite(xyz).all()
                if step == 0:
                    rec = rt.preflight['baseline'][item['label']]
                    path = Path(rt.lock['native_root']) / rec['path']
                    assert sha256(path) == rec['sha256']
                    assert np.array_equal(xyz, np.load(path)['coordinates'])
                path = folder / 'coordinates' / f'{step}_correct_{item["label"]}.npz'
                np.savez_compressed(path, coordinates=xyz)
                records.append(dict(path=str(path.relative_to(folder)), sha256=sha256(path),
                                    label=item['label'], arm='correct'))
            if step == lock['updates']:
                for index, aa in enumerate(choices):
                    donor = choices[(index + 1) % 19]
                    base = bases[aa]
                    c = (base[0], base[1], base[2] + residuals[donor])
                    mismatched.add(c[2] - base[2], targets[aa] - base[2])
                    item = b.item(pi, pos, aa)
                    xyz = np.stack([b.decode(item, c, ni).cpu().numpy() for ni in (0, 1)])
                    assert np.isfinite(xyz).all()
                    path = folder / 'coordinates' / f'{step}_mismatched_{item["label"]}.npz'
                    np.savez_compressed(path, coordinates=xyz)
                    records.append(dict(path=str(path.relative_to(folder)), sha256=sha256(path),
                                        label=item['label'], arm='mismatched', donor=donor))
                # A,B,A order and CPU checkpoint reconstruction use exact checks.
                first = predict(choices[0])[2].clone()
                predict(choices[1])
                assert torch.equal(first, predict(choices[0])[2])
                clone = PairRecovery(list(rt.model.pairformer_stack.blocks[-2:]), arm, seed).cuda()
                clone.load_state_dict(net.state_dict())
                c = clone(bases[choices[0]], reference, pos, b.aa.index('T'), b.aa.index(choices[0]))
                assert torch.equal(first, c[2])
                report['evaluation_forward_count'] += 4
                report['feature_forwards'] += 1
                del clone, first, c
        cp = folder / 'checkpoints' / f'{step}.pt'
        torch.save(dict(state_dict=net.state_dict(), optimizer=optimizer.state_dict(), step=step,
                        config=net.config, lock_sha256=sha256(root / 'training_lock.json')), cp)
        rp = folder / 'residuals' / f'{step}.pt'
        torch.save({aa: r.cpu() for aa, r in residuals.items()}, rp)
        parameter_movement = {}
        for name, param in net.named_parameters():
            group = '.'.join(name.split('.')[:2]) if name.startswith('blocks.') else name.split('.')[0]
            parameter_movement.setdefault(group, 0.)
            parameter_movement[group] += float((param.detach().double() - initial_parameters[name].double()).square().sum())
        ev = dict(complete=True, step=step, site=FIT_SITE, objective=objective, predictions=records,
                  latent=[dict(site=FIT_SITE, parent=pi, pdb=site['pdb_id'], role='train', moments=moments.result())],
                  mismatch_latent=mismatched.result() if step == lock['updates'] else None,
                  candidate_stats=candidate_stats, parameter_movement_squared=parameter_movement,
                  checkpoint=str(cp.relative_to(folder)), sha256=sha256(cp),
                  residual_file=str(rp.relative_to(folder)), residual_sha256=sha256(rp),
                  exposure=dict(exposure), seconds=time.monotonic() - begin)
        assert exposure == expected_exposures(choices, step)
        write_json(folder / f'evaluation_{step}.json', ev)
        print('FIT_EVAL', arm, seed, step, moments.result(), flush=True)
        net.train()

    evaluate(0)
    with (folder / 'history.jsonl').open('x', buffering=1) as history:
        for step in range(lock['updates']):
            net.train(); optimizer.zero_grad(set_to_none=True)
            selected = candidate_pair(choices, step)
            losses = []
            for aa in selected:
                c = predict(aa)
                loss = (c[2] - targets[aa]).square().mean() / q
                assert torch.isfinite(loss)
                (loss / 2).backward()
                losses.append(float(loss.detach()))
                exposure[aa] += 1
                report['training_forward_count'] += 1
                del c, loss
            if step < 4 or (step + 1) % 128 == 0 or step + 1 in lock['checkpoints']:
                audit = gradient_groups(net)
                assert not audit['missing'] and all(np.isfinite(v) for v in audit['norms'].values())
                report['gradient_audits'].append(dict(step=step + 1, **audit))
            norm = torch.nn.utils.clip_grad_norm_(net.parameters(), 1., error_if_nonfinite=True)
            optimizer.step(); b.counts['updates'] += 1
            history.write(json.dumps(dict(step=step + 1, site=FIT_SITE, aa=selected, loss=losses,
                                          gradient_norm=float(norm), clipped=bool(norm > 1))) + '\n')
            if (step + 1) % 128 == 0:
                report.update(step=step + 1, seconds=time.monotonic() - start)
                write_json(folder / 'report.json', report)
                print('FIT_TRAIN', arm, seed, step + 1, report['seconds'], flush=True)
            if step + 1 in lock['checkpoints']:
                evaluate(step + 1)
    assert input_guard == {aa: state_hash(bases[aa]) for aa in choices}
    assert target_guard == state_hash(tuple(targets.values()))
    assert prefix_guard == {p: state_hash(v[0]) for p, v in rt.prefixes.items()}
    assert all(p.grad is None for p in rt.model.parameters())
    rt.finish()
    assert b.counts == dict(s1=228, updates=8208, recycle=0, c4=0, input_embedder=0)
    assert report['training_forward_count'] == 16416 and report['evaluation_forward_count'] == 99
    assert report['feature_forwards'] == 16515
    report.update(complete=True, step=8208, exposure=exposure, seconds=time.monotonic() - start,
                  final_sha256=editor_state_digest(net), unchanged_inputs=True, unchanged_reference=True,
                  history_sha256=sha256(folder / 'history.jsonl'),
                  peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                  lock_sha256=sha256(root / 'training_lock.json'))
    write_json(folder / 'report.json', report)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--arm', choices=['pretrained', 'random'], required=True)
    parser.add_argument('--seed', type=int, choices=[272001, 272003], required=True)
    args = parser.parse_args()
    fit_one_context(args.root, args.arm, args.seed)
