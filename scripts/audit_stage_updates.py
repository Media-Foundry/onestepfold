"""TRAIN-only fixed-state gradient/update probes, never continued training."""
import argparse
import copy
import json
from pathlib import Path
import time

import numpy as np
import torch

from fastglycan.models.stage_pair_recovery import StagePairRecovery, aligned_pair_loss
from fastglycan.stage_pair_data import StagePairData
from fastglycan.pair_recovery_data import PairRecoveryData
from fastglycan.stage_update_diagnostic import StageUpdateProbe
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.reference_editor_multiref import multiref_update, editor_state_digest
from run_recycle_lora import LoRARuntime


def audit_stage_updates(root, arm, seed):
    begin = time.monotonic()
    lock = json.loads((root / 'audit_lock.json').read_text())
    assert sha256(root / 'protocol.md') == lock['protocol_sha256']
    for name, digest in lock['code'].items():
        assert sha256(root / 'code' / name) == digest, name
    source = Path(lock['sources'][f'{arm}_{seed}'])
    training = json.loads((source / 'training_lock.json').read_text())
    assert sha256(source / 'training_lock.json') == lock['training_locks'][f'{arm}_{seed}']
    for name, digest in training['code'].items():
        assert sha256(root / 'code' / name) == digest, name
    destination = root / 'runs' / arm / str(seed)
    destination.mkdir(parents=True, exist_ok=False)
    rt = LoRARuntime(Path(training['source']), str(destination / 'work'))
    b = rt.base
    data = PairRecoveryData(training['build_root'], training['cache_manifest_sha256'])
    stages = StagePairData(training['stage_root'], training['stage_manifest_sha256'])
    keys = training['train_sites']
    assert len(keys) == 27 and all(b.sites[k]['role_n15'] == 'train' for k in keys)
    net = StagePairRecovery(list(rt.model.pairformer_stack.blocks[-2:]), seed).cuda().train()
    native_guards = []

    def forbid_native(*args):
        raise AssertionError('No native folding/decoding allowed in update audit')

    for module in (rt.model.pairformer_stack, rt.model.input_embedder, rt.model.diffusion_module):
        native_guards.append(module.register_forward_pre_hook(forbid_native))
    counts = dict(forwards=0, backwards=0, virtual_adam_steps=0)
    report = dict(complete=False, arm=arm, seed=seed, nodes=[], counts=counts,
                  source=str(source), audit_lock_sha256=sha256(root / 'audit_lock.json'))

    def heartbeat(phase, **details):
        report.update(phase=phase, seconds=time.monotonic()-begin, **details)
        write_json(destination / 'report.json', report)
        print('UPDATE_AUDIT', arm, seed, phase, details, report['seconds'], flush=True)

    def forward(site, aa):
        assert site['site_key'] in keys and site['role_n15'] == 'train'
        pi, pos = site['parent_index'], site['position_zero_based']
        label = b.label(pi, pos, aa)
        base, target = data.base(label), data.target(label)
        boundary, warm, hint = stages.load(label, training=True)
        result, outputs = net(base, boundary, rt.prefixes[pi][0][1], pos,
                              b.aa.index(site['original_aa']), b.aa.index(aa))
        assert result[0] is base[0] and result[1] is base[1]
        loss, _ = aligned_pair_loss(outputs, target, hint,
                                    training['site_scale_squared'][site['site_key']], arm)
        assert torch.isfinite(loss)
        counts['forwards'] += 1
        return loss, outputs, target, hint

    def full_objective(probe, gradients=False):
        rows, site_gradients = [], []
        for key in keys:
            site = b.sites[key]
            net.zero_grad(set_to_none=True)
            error_sums = [None, None]
            energy = [0., 0.]
            native_losses = []
            with torch.enable_grad() if gradients else torch.no_grad():
                for aa in site['candidates']:
                    loss, outputs, target, hint = forward(site, aa)
                    native_losses.append(float(loss.detach()))
                    # Error moments in FP64; no target state becomes a predictor input.
                    for j, (pred, expected) in enumerate(((outputs[-1], target), (outputs[0], hint))):
                        error = pred.detach().cpu().double() - expected.detach().cpu().double()
                        energy[j] += float(error.square().sum())
                        error_sums[j] = error.clone() if error_sums[j] is None else error_sums[j] + error
                    if gradients:
                        (loss/19).backward(); counts['backwards'] += 1
                    del loss, outputs, target, hint, error
            parts = []
            q = training['site_scale_squared'][key]
            for total, square in zip(error_sums, energy):
                raw = square / 19 / total.numel() / q
                common = float((total/19).square().mean()) / q
                centered = raw-common
                assert centered >= -1e-10
                parts.append(dict(raw=raw, common=common, centered=centered))
            objective = parts[0]['raw'] if arm == 'final' else (parts[0]['raw']+parts[1]['raw'])/2
            assert np.isclose(objective, np.mean(native_losses), rtol=2e-5, atol=1e-7)
            rows.append(dict(site=key, parent=site['parent_index'], final=parts[0], hint=parts[1],
                             objective=objective, original_fp32_loss_mean=float(np.mean(native_losses))))
            if gradients:
                site_gradients.append(probe.vector(gradients=True))
        result = dict(objective=float(np.mean([r['objective'] for r in rows])), sites=rows)
        for stage_name in ('final', 'hint'):
            result[stage_name] = {mode: float(np.mean([r[stage_name][mode] for r in rows]))
                                  for mode in ('raw', 'common', 'centered')}
        return result, torch.stack(site_gradients) if gradients else None

    for step in lock['checkpoints']:
        heartbeat('load', step=step)
        folder = source / 'runs' / arm / str(seed)
        saved = json.loads((folder / f'evaluation_{step}.json').read_text())
        cp_path = folder / saved['checkpoint']
        assert sha256(cp_path) == saved['sha256'] == lock['checkpoints_sha256'][f'{arm}_{seed}_{step}']
        checkpoint = torch.load(cp_path, map_location='cpu', weights_only=False)
        assert checkpoint['step'] == step
        net.load_state_dict(checkpoint['state_dict'], strict=True)
        digest = editor_state_digest(net)
        probe = StageUpdateProbe(net, checkpoint['optimizer'])
        baseline, site_gradients = full_objective(probe, gradients=True)
        expected = lock['original_objectives'][f'{arm}_{seed}_{step}']
        assert np.isclose(baseline['objective'], expected, rtol=2e-5, atol=1e-7), (baseline['objective'], expected)
        full_gradient = site_gradients.mean(0)
        gram = site_gradients @ site_gradients.T
        norms = site_gradients.norm(dim=1)
        cosine = gram / torch.clamp(norms[:, None]*norms[None, :], min=1e-300)
        gradient_rows = [dict(site=k, **probe.comparison(full_gradient, g)) for k,g in zip(keys,site_gradients)]
        node = dict(step=step, checkpoint_sha256=saved['sha256'], baseline=baseline,
                    expected_objective=expected, gradient_gram=gram.tolist(), gradient_cosines=cosine.tolist(),
                    site_gradients=gradient_rows, scheduled_batches=[], probes={})
        heartbeat('full_gradient_complete', step=step, objective=baseline['objective'])
        batch_gradients, clipped_gradients, clipped_deltas, raw_deltas = [], [], [], []
        # Extend the schedule index only; each counterfactual starts at the saved state.
        schedule = dict(updates=step+len(keys), train_site_keys=keys)
        for offset in range(len(keys)):
            probe.reset()
            site, aas = multiref_update(schedule, b.sites, step+offset)
            losses = []
            for aa in aas:
                loss, outputs, target, hint = forward(site, aa)
                (loss/2).backward(); counts['backwards'] += 1
                losses.append(float(loss.detach()))
                del loss, outputs, target, hint
            gradient = probe.vector(gradients=True)
            clipped_delta, clipped_gradient, norm = probe.adam_direction(gradient, True)
            raw_delta, _, _ = probe.adam_direction(gradient, False)
            counts['virtual_adam_steps'] += 2
            batch_gradients.append(gradient); clipped_gradients.append(clipped_gradient)
            clipped_deltas.append(clipped_delta); raw_deltas.append(raw_delta)
            row = dict(site=site['site_key'], aa=aas, norm=norm, clipped=norm>1, losses=losses,
                       clip_factor=float(clipped_gradient.norm()/gradient.norm()),
                       raw_gradient=probe.comparison(full_gradient,gradient),
                       clipped_gradient=probe.comparison(full_gradient,clipped_gradient),
                       clipped_update=probe.comparison(full_gradient,clipped_delta),
                       unclipped_update=probe.comparison(full_gradient,raw_delta),
                       batch_own_clipped_update=probe.comparison(gradient,clipped_delta))
            if offset == 0 and step < 8208:
                history = [json.loads(x) for x in (folder/'history.jsonl').read_text().splitlines()]
                old = history[step]
                assert old['site'] == site['site_key'] and old['aa'] == aas
                assert np.allclose(losses+[norm],old['loss']+[old['gradient_norm']],rtol=1e-6,atol=1e-8)
                row['historical_next_step_checked'] = True
                row['historical_next_step_exact'] = losses+[norm] == old['loss']+[old['gradient_norm']]
            node['scheduled_batches'].append(row)
        batch_gradients = torch.stack(batch_gradients)
        clipped_gradients = torch.stack(clipped_gradients)
        clipped_deltas, raw_deltas = torch.stack(clipped_deltas), torch.stack(raw_deltas)
        full_adam, _, _ = probe.adam_direction(full_gradient, True)
        counts['virtual_adam_steps'] += 1
        directions = dict(mean_clipped_adam=clipped_deltas.mean(0), mean_unclipped_adam=raw_deltas.mean(0),
                          full_gradient_adam=full_adam)
        directions['negative_full_gradient'] = -full_gradient * (
            directions['mean_clipped_adam'].norm()/full_gradient.norm())
        node['mean_raw_gradient'] = probe.comparison(full_gradient,batch_gradients.mean(0))
        node['mean_clipped_gradient'] = probe.comparison(full_gradient,clipped_gradients.mean(0))
        for name, direction in directions.items():
            node['probes'][name] = dict(direction=probe.comparison(full_gradient,direction), fractions=[])
            for fraction in lock['fractions']:
                applied = probe.assign(direction,fraction)
                evaluated, _ = full_objective(probe)
                row = dict(fraction=fraction, actual_direction=probe.comparison(full_gradient,applied),
                           evaluation=evaluated, loss_change=evaluated['objective']-baseline['objective'])
                node['probes'][name]['fractions'].append(row)
                heartbeat('finite_probe',step=step,direction=name,fraction=fraction,loss_change=row['loss_change'])
        probe.reset(); assert editor_state_digest(net) == digest
        vectors = dict(origin=probe.origin, groups=probe.groups, full_gradient=full_gradient,
                       site_gradients=site_gradients.float(), batch_gradients=batch_gradients.float(),
                       clipped_gradients=clipped_gradients.float(), clipped_deltas=clipped_deltas,
                       unclipped_deltas=raw_deltas, directions=directions)
        vector_path = destination/f'vectors_{step}.pt';torch.save(vectors,vector_path)
        node['vectors'] = dict(path=vector_path.name,sha256=sha256(vector_path),bytes=vector_path.stat().st_size)
        node['state_restored'] = True
        node['complete'] = True
        write_json(destination/f'node_{step}.json',node)
        report['nodes'].append(dict(step=step,path=f'node_{step}.json',sha256=sha256(destination/f'node_{step}.json')))
        heartbeat('node_complete',step=step)
        del vectors, probe, checkpoint, site_gradients, batch_gradients, clipped_gradients, clipped_deltas, raw_deltas
    for handle in native_guards:handle.remove()
    rt.finish()
    assert all(p.grad is None for p in rt.model.parameters())
    assert b.counts == dict(c4=0,input_embedder=0,recycle=0,s1=0,updates=0)
    assert counts == dict(forwards=14013,backwards=1701,virtual_adam_steps=165), counts
    report.update(complete=True,native_counts=b.counts,peak_allocated_bytes=torch.cuda.max_memory_allocated())
    heartbeat('complete')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--arm', choices=['final','hint'], required=True)
    parser.add_argument('--seed', type=int, required=True)
    args = parser.parse_args()
    audit_stage_updates(args.root,args.arm,args.seed)
