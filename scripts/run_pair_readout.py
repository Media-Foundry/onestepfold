"""Frozen-feature TRAIN-only QR fits and fixed full-head decoder evaluation."""
import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from fastglycan.models.pair_recovery import PairRecovery
from fastglycan.pair_recovery_data import PairRecoveryData
from fastglycan.pair_readout import WeightedReadoutQR, site_row_weight
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.reference_editor_multiref import editor_state_digest
from fastglycan.response_moments import ResponseMoments
from run_recycle_lora import LoRARuntime
from run_reference_editor import state_hash


def readout_lock(root):
    lock = json.loads((root / 'readout_lock.json').read_text())
    assert sha256(root / 'protocol.md') == lock['protocol_sha256']
    for path, digest in lock['code'].items():
        assert sha256(root / 'code' / path) == digest, path
    source = Path(lock['recovery_root'])
    assert sha256(source / 'training_lock.json') == lock['source_lock_sha256']
    previous = json.loads((source / 'training_lock.json').read_text())
    assert lock['train_sites'] == previous['train_sites']
    assert lock['site_scale_squared'] == previous['site_scale_squared']
    return lock, previous


class ReadoutFeatures:
    """Observe the exact tensor consumed by the frozen native output layer."""

    def __init__(self, net):
        self.net, self.value, self.calls = net, None, 0
        self.handle = net.out.register_forward_pre_hook(self.capture)

    def capture(self, module, args):
        self.value = args[0].detach()

    def forward(self, base, reference, position, old, target):
        self.value = None
        output = self.net(base, reference, position, old, target)
        h = self.value
        assert h is not None and output[0] is base[0] and output[1] is base[1]
        assert torch.equal(base[2] + F.linear(h, self.net.out.weight), output[2])
        self.calls += 1
        return h, output

    def close(self):
        self.handle.remove()


def run_pair_readout(root, arm, seed):
    start = time.monotonic()
    lock, previous = readout_lock(root)
    folder = root / 'runs' / arm / str(seed)
    folder.mkdir(parents=True, exist_ok=False)
    (folder / 'coordinates').mkdir()
    source = Path(lock['recovery_root']) / 'runs' / arm / str(seed)
    old_evaluation = json.loads((source / 'evaluation_8208.json').read_text())
    checkpoint_path = source / old_evaluation['checkpoint']
    assert sha256(checkpoint_path) == lock['checkpoints'][f'{arm}_{seed}']['sha256'] == old_evaluation['sha256']
    checkpoint = torch.load(checkpoint_path, map_location='cpu', weights_only=False)
    assert checkpoint['step'] == 8208 and checkpoint['lock_sha256'] == lock['source_lock_sha256']
    rt = LoRARuntime(Path(previous['source']), str(root / f'work_{arm}_{seed}'))
    b = rt.base
    torch.set_num_threads(lock['cpu_threads'])
    net = PairRecovery(list(rt.model.pairformer_stack.blocks[-2:]), arm, seed).cuda()
    net.load_state_dict(checkpoint['state_dict'], strict=True)
    net.requires_grad_(False).eval()
    digest = editor_state_digest(net)
    references = {pi: state_hash(state[0]) for pi, state in rt.prefixes.items()}
    data = PairRecoveryData(previous['build_root'], previous['cache_manifest_sha256'])
    observe = ReadoutFeatures(net)
    old_files = {r['label']: r for r in old_evaluation['predictions'] if r['arm'] == 'correct'}
    original = net.out.weight.detach().cpu().double().T.contiguous()
    solvers = {name: WeightedReadoutQR(chunk_rows=lock['chunk_rows']) for name in ('full', 'centered')}
    fit_sites = []
    report = dict(complete=False, arm=arm, seed=seed, phase='preflight', fit_sites=[],
                  source_checkpoint_sha256=sha256(checkpoint_path), frozen_sha256=digest)

    def status(phase, **fields):
        report.update(phase=phase, seconds=time.monotonic() - start, **fields)
        write_json(folder / 'report.json', report)

    def replay(site, aa, conditioning):
        item = b.item(site['parent_index'], site['position_zero_based'], aa)
        record = old_files[item['label']]
        path = source / record['path']
        assert sha256(path) == record['sha256']
        expected = np.load(path)['coordinates']
        for ni in range(2):
            assert np.array_equal(b.decode(item, conditioning, ni).cpu().numpy(), expected[ni])

    with torch.no_grad():
        site = b.sites[lock['train_sites'][0]]
        aa = site['candidates'][0]; pi, pos = site['parent_index'], site['position_zero_based']
        base = data.base(b.label(pi, pos, aa))
        _, old_c = observe.forward(base, rt.prefixes[pi][0][1], pos, b.aa.index(site['original_aa']), b.aa.index(aa))
        replay(site, aa, old_c)
        status('fit', preflight_replays=2)
        # Only TRAIN sites reach the solver. Held labels are first read below,
        # after both heads and their diagnostics have been persisted.
        for site_key in lock['train_sites']:
            site = b.sites[site_key]
            assert site['role_n15'] == 'train'
            pi, pos = site['parent_index'], site['position_zero_based']
            hs, es = [], []
            for aa in site['candidates']:
                label = b.label(pi, pos, aa); base = data.base(label)
                h, _ = observe.forward(base, rt.prefixes[pi][0][1], pos, b.aa.index(site['original_aa']), b.aa.index(aa))
                hs.append(h); es.append(data.target(label).double() - base[2].double())
            h = torch.stack(hs); e = torch.stack(es)
            mean_h, mean_e = h.double().mean(0), e.mean(0)
            length = h.shape[1]
            weight = site_row_weight(length, lock['site_scale_squared'][site_key])
            for ai in range(19):
                solvers['full'].add(h[ai].reshape(-1, 128), e[ai].reshape(-1, 128), weight)
                solvers['centered'].add((h[ai].double() - mean_h).reshape(-1, 128),
                                        (e[ai] - mean_e).reshape(-1, 128), weight)
            fit_sites.append(dict(site=site_key, length=length, rows=19*length*length, row_weight=weight))
            data.inputs.clear(); data.labels.clear()
            del hs, es, h, e, mean_h, mean_e
            status('fit', fit_sites=fit_sites)
            print('READOUT_FIT_SITE', arm, seed, site_key, report['seconds'], flush=True)
        solutions, audits = {}, {}
        for name, solver in solvers.items():
            solutions[name], audits[name] = solver.solve(original, lock['rcond'])
        torch.save(dict(solutions=solutions, original=original,
                        qr={name: solver.r for name, solver in solvers.items()},
                        checkpoint_sha256=sha256(checkpoint_path), lock_sha256=sha256(root/'readout_lock.json')),
                   folder / 'readouts.pt')
        write_json(folder/'fit.json', dict(complete=True, audits=audits, fit_sites=fit_sites,
                    readouts_sha256=sha256(folder/'readouts.pt'), seconds=time.monotonic()-start,
                    norm_gamma=net.norm.weight.detach().cpu().tolist(), norm_beta=net.norm.bias.detach().cpu().tolist()))
        status('evaluate', fit_complete=True)
        matrices = dict(old=original.cuda(), full=solutions['full'].cuda(), centered=solutions['centered'].cuda())
        head32 = solutions['full'].T.contiguous().float().cuda()
        direct = {obj: {method: 0. for method in ('old', 'fit', 'zero')} for obj in ('full', 'centered')}
        native_objective = {method: 0. for method in ('old', 'full')}
        site_metrics, predictions, numerical = [], [], []
        for site in b.plan['sites']:
            pi, pos = site['parent_index'], site['position_zero_based']
            hs, es, old_pairs, new_pairs, residuals = [], [], [], [], []
            old_moments, new_moments = ResponseMoments(), ResponseMoments()
            max_rounding = 0.
            for ai, aa in enumerate(site['candidates']):
                label = b.label(pi, pos, aa); base = data.base(label)
                h, old_c = observe.forward(base, rt.prefixes[pi][0][1], pos, b.aa.index(site['original_aa']), b.aa.index(aa))
                target = data.target(label)
                e = target.double() - base[2].double()
                r32 = F.linear(h, head32)
                pair = base[2] + r32
                hs.append(h); es.append(e); old_pairs.append(old_c[2]); new_pairs.append(pair)
                residuals.append(r32)
                old_moments.add(old_c[2]-base[2], target-base[2])
                new_moments.add(pair-base[2], target-base[2])
                if ai == 0:
                    replay(site, aa, old_c)
                item = b.item(pi, pos, aa)
                coords = np.stack([b.decode(item, (base[0], base[1], pair), ni).cpu().numpy() for ni in range(2)])
                path = folder/'coordinates'/f'full_{label}.npz'; np.savez_compressed(path, coordinates=coords)
                predictions.append(dict(arm='full',label=label,path=str(path.relative_to(folder)),sha256=sha256(path)))
                pred64 = h.double() @ matrices['full']
                max_rounding = max(max_rounding, float((r32.double()-pred64).abs().max()))
                if site['role_n15'] == 'train':
                    scale = lock['site_scale_squared'][site['site_key']]
                    for name, z in (('old',old_c[2]),('full',pair)):
                        native_objective[name] += float((z-target).square().mean()) / (27*19*scale)
            h = torch.stack(hs).double(); e = torch.stack(es)
            hc, ec = h-h.mean(0), e-e.mean(0)
            moments = {name: ResponseMoments() for name in ('old64','full64','centered64')}
            for ai in range(19):
                for name, w in matrices.items():
                    moments[name+'64'].add(h[ai] @ w, e[ai])
                if site['role_n15'] == 'train':
                    weight = site_row_weight(h.shape[1], lock['site_scale_squared'][site['site_key']])
                    for obj, x, y, fit in (('full',h[ai],e[ai],'full'), ('centered',hc[ai],ec[ai],'centered')):
                        direct[obj]['old'] += float((x@matrices['old']-y).square().sum())*weight
                        direct[obj]['fit'] += float((x@matrices[fit]-y).square().sum())*weight
                        direct[obj]['zero'] += float(y.square().sum())*weight
            for ai, aa in enumerate(site['candidates']):
                item = b.item(pi,pos,aa); base = data.base(item['label']); donor = (ai+1)%19
                c = (base[0],base[1],base[2]+residuals[donor])
                coords = np.stack([b.decode(item,c,ni).cpu().numpy() for ni in range(2)])
                path=folder/'coordinates'/f'mismatched_{item["label"]}.npz';np.savez_compressed(path,coordinates=coords)
                predictions.append(dict(arm='mismatched',label=item['label'],donor=site['candidates'][donor],
                                        path=str(path.relative_to(folder)),sha256=sha256(path)))
            results = {name: value.result() for name,value in moments.items()}
            # Centered fit does not identify the common response; publish only
            # the component that this separate diagnostic objective supervises.
            centered_result = results.pop('centered64')['centered']
            site_metrics.append(dict(site=site['site_key'],parent=pi,pdb=site['pdb_id'],role=site['role_n15'],
                    length=h.shape[1],old=old_moments.result(),full=new_moments.result(),
                    linear64=results,centered_fit=centered_result))
            gamma = net.norm.weight.detach().double()
            relation = None
            if bool((gamma != 0).all()):
                normal = gamma.reciprocal();normal /= normal.norm()
                relation = float((hc@normal).norm()/hc.norm().clamp_min(1e-300))
            numerical.append(dict(site=site['site_key'],fp32_full_head_max_error=max_rounding,
                                  centered_layernorm_normal_relative=relation))
            data.inputs.clear();data.labels.clear()
            del hs,es,h,e,hc,ec,old_pairs,new_pairs,residuals,moments
            status('evaluate',evaluated_sites=len(site_metrics))
            print('READOUT_EVAL_SITE',arm,seed,site['site_key'],report['seconds'],flush=True)
        for obj, checks in direct.items():
            for name, value in checks.items():
                expected = audits[obj]['objective_'+name]
                assert abs(value-expected) <= max(1e-10,2e-8*abs(expected)), (obj,name,value,expected)
        observe.close()
        assert editor_state_digest(net)==digest and all(p.grad is None for p in net.parameters())
        assert references=={pi:state_hash(state[0]) for pi,state in rt.prefixes.items()}
        rt.finish()
        assert b.counts['recycle']==0 and b.counts['updates']==0 and b.counts['s1']==3746,b.counts
        assert observe.calls==1426
        write_json(folder/'evaluation.json',dict(complete=True,arm=arm,seed=seed,sites=site_metrics,
                   predictions=predictions,numerical=numerical,direct_objectives=direct,
                   native_fp32_objectives=native_objective,fit_sha256=sha256(folder/'fit.json'),
                   readouts_sha256=sha256(folder/'readouts.pt'),counts=b.counts,feature_forwards=observe.calls,
                   frozen_sha256_after=editor_state_digest(net),seconds=time.monotonic()-start))
        readout_lock(root)
        status('complete',complete=True,counts=b.counts,feature_forwards=observe.calls,
               peak_allocated_bytes=torch.cuda.max_memory_allocated())


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--arm',choices=['pretrained','random'],required=True);parser.add_argument('--seed',type=int,required=True)
    args=parser.parse_args();run_pair_readout(args.root,args.arm,args.seed)
