"""Fixed full-gradient-work comparison; native folding and inputs stay frozen."""
import argparse
import inspect
import json
from pathlib import Path
import time

import numpy as np
import torch

from fastglycan.models.stage_pair_recovery import StagePairRecovery
from fastglycan.pair_recovery_data import PairRecoveryData
from fastglycan.stage_pair_data import StagePairData
from fastglycan.stage_fullbatch import BoundedLBFGS, FullBatchStageTrainer, parameter_digest
from fastglycan.response_moments import ResponseMoments
from fastglycan.reference_editor_multiref import editor_state_digest
from fastglycan.paired_teacher_protocol import sha256, write_json
from run_recycle_lora import LoRARuntime


def run_stage_fullbatch(root, arm, seed):
    begin = time.monotonic()
    lock = json.loads((root/'training_lock.json').read_text())
    assert sha256(root/'protocol.md') == lock['protocol_sha256']
    for name, digest in lock['code'].items():
        assert sha256(root/'code'/name) == digest, name
    assert torch.__version__ == lock['torch_version']
    assert sha256(Path(inspect.getsourcefile(torch.optim.LBFGS))) == lock['lbfgs_source_sha256']
    folder = root/'runs'/arm/str(seed)
    folder.mkdir(parents=True, exist_ok=False)
    (folder/'checkpoints').mkdir(); (folder/'coordinates').mkdir()
    rt = LoRARuntime(Path(lock['source']), str(folder/'work'))
    b = rt.base
    data = PairRecoveryData(lock['build_root'], lock['cache_manifest_sha256'])
    stages = StagePairData(lock['stage_root'], lock['stage_manifest_sha256'])
    net = StagePairRecovery(list(rt.model.pairformer_stack.blocks[-2:]), seed).cuda().train()
    assert editor_state_digest(net) == lock['initial_hashes'][str(seed)]
    keys = lock['train_sites']
    assert len(keys) == 27 and all(b.sites[k]['role_n15'] == 'train' for k in keys)
    report = dict(complete=False, arm=arm, seed=seed, phase='cache', gradient_passes=0,
                  optimizer_calls=0, changed_updates=0, rollbacks=0, evaluation_forwards=0,
                  isolation_forwards=0, native_counts=b.counts, checkpoints=[],
                  initial_sha256=editor_state_digest(net), training_lock_sha256=sha256(root/'training_lock.json'))

    def heartbeat():
        report['seconds'] = time.monotonic()-begin
        write_json(folder/'report.json', report)
        print('FULLBATCH_STATE', arm, seed, report['phase'], report['gradient_passes'], report['seconds'], flush=True)

    def forbid_native(*args):
        raise AssertionError('native candidate folding/input computation forbidden')

    def guard_decoder(*args):
        if report['phase'] != 'evaluation':
            raise AssertionError('decoder cannot participate in optimization')

    handles = [rt.model.pairformer_stack.register_forward_pre_hook(forbid_native),
               rt.model.input_embedder.register_forward_pre_hook(forbid_native),
               rt.model.diffusion_module.register_forward_pre_hook(guard_decoder)]
    resident = {}
    cache_bytes = 0
    cache_start = time.monotonic()
    for key in keys:
        site = b.sites[key]
        for aa in site['candidates']:
            label = b.label(site['parent_index'], site['position_zero_based'], aa)
            base = data.base(label)
            boundary, warm, _ = stages.load(label, training=False)
            target = data.target(label)
            resident[label] = (base, boundary, target)
            cache_bytes += sum(t.numel()*t.element_size() for t in (*base, boundary, target))
            assert cache_bytes <= lock['resident_tensor_byte_cap']
            assert not any(t.requires_grad for t in (*base, boundary, target))
            del warm
    report.update(cache_bytes=cache_bytes, cache_seconds=time.monotonic()-cache_start)
    heartbeat()

    def fetch(site, aa):
        assert site['site_key'] in keys and site['role_n15'] == 'train'
        return resident[b.label(site['parent_index'], site['position_zero_based'], aa)]

    trainer = FullBatchStageTrainer(net, [b.sites[k] for k in keys], fetch,
                                   {pi: pair[0][1] for pi, pair in rt.prefixes.items()},
                                   b.aa, lock['site_scale_squared'])
    bounded = BoundedLBFGS(net.parameters()) if arm == 'lbfgs' else None
    optimizer = bounded.optimizer if bounded else torch.optim.AdamW(
        net.parameters(), lr=1e-4, weight_decay=1e-4, eps=1e-8)
    native_hash = editor_state_digest(rt.model)

    def predict(site, aa):
        label = b.label(site['parent_index'], site['position_zero_based'], aa)
        base = data.base(label)
        boundary, _, _ = stages.load(label, training=False)
        result, outputs = net(base, boundary, rt.prefixes[site['parent_index']][0][1],
                              site['position_zero_based'], b.aa.index(site['original_aa']), b.aa.index(aa))
        assert result[0] is base[0] and result[1] is base[1]
        return label, base, result

    def isolation():
        with torch.no_grad():
            site = b.sites[keys[0]]
            first = predict(site, site['candidates'][0])[2][2].clone()
            predict(site, site['candidates'][1])
            again = predict(site, site['candidates'][0])[2][2]
            assert torch.equal(first, again)
        report['isolation_forwards'] += 3

    def evaluate(step):
        start = time.monotonic(); report['phase'] = 'evaluation'; heartbeat()
        net.eval(); rows, latent = [], []
        with torch.no_grad():
            for key in lock['eval_sites']:
                site = b.sites[key]
                moments, mismatch, residual = ResponseMoments(), ResponseMoments(), {}
                for aa in site['candidates']:
                    label, base, conditioning = predict(site, aa)
                    report['evaluation_forwards'] += 1
                    if step == 0:
                        assert torch.equal(conditioning[2], base[2])
                    target = data.target(label)
                    moments.add(conditioning[2]-base[2], target-base[2])
                    residual[aa] = (conditioning[2]-base[2]).cpu()
                    item = b.item(site['parent_index'], site['position_zero_based'], aa)
                    xyz = np.stack([b.decode(item, conditioning, ni).cpu().numpy() for ni in (0,1)])
                    assert np.isfinite(xyz).all()
                    if step == 0:
                        rec = rt.preflight['baseline'][label]
                        path = Path(rt.lock['native_root'])/rec['path']
                        assert sha256(path) == rec['sha256']
                        assert np.array_equal(xyz, np.load(path)['coordinates'])
                    path = folder/'coordinates'/f'{step}_correct_{label}.npz'
                    np.savez_compressed(path, coordinates=xyz)
                    rows.append(dict(path=str(path.relative_to(folder)), sha256=sha256(path), label=label, arm='correct'))
                if step == lock['gradient_budget']:
                    for i, aa in enumerate(site['candidates']):
                        donor = site['candidates'][(i+1)%19]
                        label = b.label(site['parent_index'], site['position_zero_based'], aa)
                        base = data.base(label)
                        conditioning = (base[0], base[1], base[2]+residual[donor].cuda())
                        mismatch.add(conditioning[2]-base[2], data.target(label)-base[2])
                        item = b.item(site['parent_index'], site['position_zero_based'], aa)
                        xyz = np.stack([b.decode(item, conditioning, ni).cpu().numpy() for ni in (0,1)])
                        assert np.isfinite(xyz).all()
                        path = folder/'coordinates'/f'{step}_mismatched_{label}.npz'
                        np.savez_compressed(path, coordinates=xyz)
                        rows.append(dict(path=str(path.relative_to(folder)), sha256=sha256(path), label=label,
                                         arm='mismatched', donor=donor))
                latent.append(dict(site=key, pdb=site['pdb_id'], parent=site['parent_index'], role=site['role_n15'],
                                   moments=moments.result(), mismatch=mismatch.result() if mismatch.n else None))
                print('FULLBATCH_EVAL_SITE', arm, seed, step, key, flush=True)
        cp = folder/'checkpoints'/f'{step}.pt'
        torch.save(dict(state_dict=net.state_dict(), optimizer=optimizer.state_dict(), step=step,
                        gradient_passes=trainer.counts['gradient_passes'], config=net.config,
                        training_lock_sha256=sha256(root/'training_lock.json')), cp)
        write_json(folder/f'evaluation_{step}.json', dict(complete=True, step=step, latent=latent,
            predictions=rows, checkpoint=str(cp.relative_to(folder)), sha256=sha256(cp),
            gradient_passes=trainer.counts['gradient_passes'], optimizer_calls=report['optimizer_calls'],
            changed_updates=report['changed_updates'], seconds=time.monotonic()-start))
        report['checkpoints'].append(step)
        net.train(); report['phase'] = 'training'; heartbeat()

    isolation(); evaluate(0)
    with (folder/'history.jsonl').open('x', buffering=1) as history:
        def closure():
            report['phase'] = 'training'
            result = trainer.objective()
            n = trainer.counts['gradient_passes']
            result.update(gradient_pass=n, parameter_sha256=parameter_digest(net.parameters()))
            if n == 1:
                path = Path(lock['gradient_references'][str(seed)]['path'])
                assert sha256(path) == lock['gradient_references'][str(seed)]['sha256']
                ref = torch.load(path, map_location='cpu', weights_only=False)['full_gradient']
                relative = float((trainer.last_gradient-ref).norm()/ref.norm())
                assert relative <= 5e-6
                assert np.isclose(result['raw'], lock['initial_objective'], rtol=2e-8, atol=1e-10)
                report['initial_gradient_relative_error'] = relative
                del ref
            history.write(json.dumps(dict(kind='gradient', **result))+'\n')
            report.update(gradient_passes=n, training_counts=trainer.counts, last_objective=result['raw'],
                          last_centered_error=result['centered'])
            heartbeat()
            return result

        for target_pass in lock['checkpoints'][1:]:
            while trainer.counts['gradient_passes'] < target_pass:
                remaining = target_pass-trainer.counts['gradient_passes']
                if bounded:
                    outcome = bounded.step(closure, min(16, remaining))
                    report['changed_updates'] += int(outcome['changed'])
                    report['rollbacks'] += int(outcome['status'].endswith('rollback'))
                    # Gradient records already persist every trial, so this ledger stays small.
                    outcome.pop('observations')
                else:
                    result = closure()
                    before = parameter_digest(net.parameters())
                    norm = torch.nn.utils.clip_grad_norm_(net.parameters(), 1., error_if_nonfinite=True)
                    optimizer.step()
                    changed = parameter_digest(net.parameters()) != before
                    report['changed_updates'] += int(changed)
                    outcome = dict(status='adamw_step', calls=1, before=result['raw'],
                                   gradient_norm=float(norm), clipped=bool(norm>1), changed=changed)
                report['optimizer_calls'] += 1
                history.write(json.dumps(dict(kind='update', gradient_passes=trainer.counts['gradient_passes'], **outcome))+'\n')
                heartbeat()
            evaluate(target_pass)
    isolation()
    assert trainer.counts == dict(forwards=65664, backwards=65664, gradient_passes=128)
    assert report['evaluation_forwards'] == 2736 and report['isolation_forwards'] == 6
    assert b.counts == dict(c4=0, input_embedder=0, recycle=0, s1=7296, updates=0)
    assert editor_state_digest(rt.model) == native_hash
    assert all(p.grad is None for p in rt.model.parameters())
    for handle in handles:
        handle.remove()
    rt.finish()
    report.update(complete=True, phase='complete', final_sha256=editor_state_digest(net),
                  history_sha256=sha256(folder/'history.jsonl'), peak_allocated_bytes=torch.cuda.max_memory_allocated())
    heartbeat()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--arm', choices=['adamw','lbfgs'], required=True)
    parser.add_argument('--seed', type=int, required=True)
    args = parser.parse_args()
    run_stage_fullbatch(args.root, args.arm, args.seed)
