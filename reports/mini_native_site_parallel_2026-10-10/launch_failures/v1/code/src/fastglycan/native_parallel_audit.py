"""Finite native acceptance check for ordered site-parallel training."""
from collections import Counter
import ctypes
from datetime import timedelta
import json
import os
from pathlib import Path
import time

import numpy as np
import torch
import torch.distributed as dist

from fastglycan.anchor_training import AnchoredFullBatchTrainer, load_anchor_boundaries
from fastglycan.models.anchored_pair_recovery import ReferenceAnchoredPairRecovery
from fastglycan.pair_recovery_data import PairRecoveryData
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.reference_editor_multiref import editor_state_digest
from fastglycan.site_parallel import local_anchor_gradients, synchronized_anchor_step
from fastglycan.stage_fullbatch import parameter_digest
from fastglycan.stage_pair_data import StagePairData


def cpu_snapshot(value):
    """Own tensor storage so later optimizer updates cannot alter evidence."""
    if isinstance(value, torch.Tensor):
        return value.detach().cpu().clone()
    if isinstance(value, dict):
        return {key: cpu_snapshot(item) for key, item in value.items()}
    if isinstance(value, list):
        return [cpu_snapshot(item) for item in value]
    if isinstance(value, tuple):
        return tuple(cpu_snapshot(item) for item in value)
    return value


def assert_tree_equal(actual, expected, path='state'):
    """Reject dtype, structure, value or moment differences, not just weights."""
    if isinstance(expected, torch.Tensor):
        if (not isinstance(actual, torch.Tensor) or actual.dtype != expected.dtype
                or actual.shape != expected.shape or not torch.equal(
                    actual.contiguous().reshape(-1).view(torch.uint8),
                    expected.contiguous().reshape(-1).view(torch.uint8))):
            raise AssertionError(f'tensor mismatch: {path}')
    elif isinstance(expected, dict):
        if not isinstance(actual, dict) or actual.keys() != expected.keys():
            raise AssertionError(f'key mismatch: {path}')
        for key in expected:
            assert_tree_equal(actual[key], expected[key], f'{path}.{key}')
    elif isinstance(expected, (list, tuple)):
        if type(actual) is not type(expected) or len(actual) != len(expected):
            raise AssertionError(f'sequence mismatch: {path}')
        for index, (left, right) in enumerate(zip(actual, expected)):
            assert_tree_equal(left, right, f'{path}[{index}]')
    elif type(actual) is not type(expected) or actual != expected:
        raise AssertionError(f'value mismatch: {path}')


def native_parallel_audit(root, runtime_factory, original_visibility):
    """Use frozen scientific inputs; all updated replicas are audit-only."""
    root = Path(root).resolve()
    lock = json.loads((root/'audit_lock.json').read_text())
    assert sha256(root/'protocol.md') == lock['protocol_sha256']
    for name, digest in lock['code'].items():
        assert sha256(root/'code'/name) == digest, name
    assert original_visibility == lock['hip_devices'] == list(range(6))
    assert lock['seed'] == 272001 and lock['steps'] == 3
    assert lock['orders'] == [['serial', 'parallel'], ['parallel', 'serial']]
    source = Path(lock['training_root'])
    assert sha256(source/'training_lock.json') == lock['training_lock_sha256']
    training = json.loads((source/'training_lock.json').read_text())
    for name, digest in training['code'].items():
        assert sha256(root/'code'/name) == digest, name
    assert torch.__version__ == training['torch_version']
    dist.init_process_group('gloo', timeout=timedelta(seconds=300))
    rank, world = dist.get_rank(), dist.get_world_size()
    assert world == 6
    folder = root/f'rank_{rank}'; folder.mkdir(exist_ok=False)
    started = time.monotonic()
    report = dict(complete=False, rank=rank, world=world, phase='loading', steps=[],
                  audit_lock_sha256=sha256(root/'audit_lock.json'))
    counts = Counter()
    handles = []

    def save():
        report['seconds'] = time.monotonic()-started
        write_json(folder/'report.json', report)
        print('NATIVE_PARALLEL_AUDIT', rank, report['phase'], len(report['steps']), flush=True)

    try:
        torch.set_num_threads(1); torch.cuda.set_device(0)
        assert torch.cuda.device_count() == 1
        assert os.environ['HIP_VISIBLE_DEVICES'] == str(original_visibility[rank])
        hip = ctypes.CDLL('/opt/rocm/lib/libamdhip64.so')
        hip.hipDeviceGetPCIBusId.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int]
        bus = ctypes.create_string_buffer(64)
        assert hip.hipDeviceGetPCIBusId(bus, 64, 0) == 0
        pci = bus.value.decode().lower()
        assert pci == lock['pci_buses'][rank].lower(), (rank, pci)
        report.update(hip_device=original_visibility[rank], pci_bus=pci)
        rt = runtime_factory(Path(training['source']), str(folder/'runtime'))
        b = rt.base
        net = ReferenceAnchoredPairRecovery(list(rt.model.pairformer_stack.blocks[-2:]), lock['seed']).cuda().train()
        assert editor_state_digest(net) == training['initial_hashes'][str(lock['seed'])]
        initial = cpu_snapshot(net.state_dict()); native_hash = editor_state_digest(rt.model)
        data = PairRecoveryData(training['build_root'], training['cache_manifest_sha256'])
        stages = StagePairData(training['stage_root'], training['stage_manifest_sha256'])
        boundaries = load_anchor_boundaries(training, 'cuda')
        keys = training['train_sites']; sites = [b.sites[key] for key in keys]
        assert len(keys) == 27 and all(s['role_n15'] == 'train' and len(s['candidates']) == 19 for s in sites)
        indices = list(range(rank, len(sites), world))
        needed = range(len(sites)) if rank == 0 else indices
        resident, byte_count = {}, 0
        for index in needed:
            site = sites[index]
            for aa in site['candidates']:
                label = b.label(site['parent_index'], site['position_zero_based'], aa)
                base = data.base(label); boundary, warm, _ = stages.load(label, training=False)
                target = data.target(label); resident[label] = (base, boundary, target)
                tensors = (*base, boundary, target)
                assert not any(t.requires_grad for t in tensors)
                byte_count += sum(t.numel()*t.element_size() for t in tensors)
                assert byte_count <= training['resident_tensor_byte_cap']
                del warm
        references = {pi: pair[0][1] for pi, pair in rt.prefixes.items()}

        def fetch(site, aa):
            assert site['site_key'] in keys and site['role_n15'] == 'train'
            return resident[b.label(site['parent_index'], site['position_zero_based'], aa)]

        def forbid(*args):
            raise AssertionError('native C4/input/recycle/decoder execution forbidden')

        for module in (rt.model.pairformer_stack, rt.model.input_embedder, rt.model.diffusion_module):
            handles.append(module.register_forward_pre_hook(forbid))
        args = (net, sites, fetch, references, b.aa, training['site_scale_squared'], b.references, boundaries)
        trainer = AnchoredFullBatchTrainer(*args)
        report.update(cache_bytes=byte_count, loading_seconds=time.monotonic()-started,
                      local_sites=[keys[i] for i in indices], device_name=torch.cuda.get_device_name(),
                      phase='warming')
        save(); dist.barrier(); warm_start = time.monotonic()
        if rank == 0:
            result = trainer.objective()
            assert np.isclose(result['raw'], training['initial_objective'], rtol=2e-8, atol=1e-10)
            record = training['gradient_references'][str(lock['seed'])]
            assert sha256(Path(record['path'])) == record['sha256']
            reference = torch.load(record['path'], map_location='cpu', weights_only=True)['anchored']
            relative = float((trainer.last_gradient-reference).norm()/reference.norm())
            assert relative <= 5e-5, relative
            report['historical_gradient_relative_error'] = relative
            counts.update(forwards=513, backwards=513, reference_forwards=27, reference_backwards=27)
            del reference
        dist.barrier()
        warm = local_anchor_gradients(*args, indices=indices)
        for record in warm:
            counts.update({k: record['counts'][k] for k in ('forwards','backwards','reference_forwards','reference_backwards')})
        del warm
        torch.cuda.synchronize(); dist.barrier()
        report['warmup_seconds'] = time.monotonic()-warm_start
        expected = {}
        for order_index, order in enumerate(lock['orders']):
            for method in order:
                net.load_state_dict(initial); net.zero_grad(set_to_none=True)
                optimizer = torch.optim.AdamW(net.parameters(), lr=1e-4, weight_decay=1e-4, eps=1e-8) if rank == 0 else None
                torch.cuda.synchronize(); torch.cuda.reset_peak_memory_stats(); dist.barrier()
                for step in range(1, lock['steps']+1):
                    report['phase'] = f'{order_index}_{method}_{step}'; save()
                    dist.barrier(); torch.cuda.synchronize(); begin = time.monotonic()
                    gradient = objective = None
                    if method == 'serial':
                        if rank == 0:
                            parameter_digest(net.parameters())
                            result = trainer.objective(); gradient = trainer.last_gradient
                            objective = {key: result[key] for key in ('raw','common','centered','sites')}
                            torch.nn.utils.clip_grad_norm_(net.parameters(), 1., error_if_nonfinite=True)
                            optimizer.step(); parameter_digest(net.parameters())
                            counts.update(forwards=513, backwards=513, reference_forwards=27, reference_backwards=27)
                    else:
                        local, error = [], None
                        try:
                            local = local_anchor_gradients(*args, indices=indices)
                            for record in local:
                                counts.update({k: record['counts'][k] for k in ('forwards','backwards','reference_forwards','reference_backwards')})
                        except Exception as failure:
                            error = repr(failure)
                        result = synchronized_anchor_step(net, local, keys, optimizer, local_error=error)
                        gradient = result['gradient']
                        objective = {key: result['summary'][key] for key in ('raw','common','centered','sites')}
                    torch.cuda.synchronize(); dist.barrier(); seconds = time.monotonic()-begin
                    timings = [None]*world; dist.all_gather_object(timings, seconds)
                    row = dict(order=order_index, method=method, step=step, seconds=max(timings),
                               rank_seconds=timings, peak_allocated_bytes=torch.cuda.max_memory_allocated())
                    if rank == 0:
                        snapshot = dict(gradient=gradient.clone(), objective=objective,
                                        model=cpu_snapshot(net.state_dict()), optimizer=cpu_snapshot(optimizer.state_dict()))
                        path = folder/f'{order_index}_{method}_{step}.pt'
                        torch.save(snapshot, path)
                        row.update(snapshot=str(path.relative_to(root)), sha256=sha256(path))
                        key = (order_index, step)
                        if key in expected:
                            delta = snapshot['gradient']-expected[key]['gradient']
                            reference_norm = float(expected[key]['gradient'].norm())
                            row.update(gradient_max_abs=float(delta.abs().max()),
                                       gradient_relative=float(delta.norm()/reference_norm) if reference_norm else None)
                            report['pending_comparison'] = dict(row)
                            save()
                            assert_tree_equal(snapshot, expected[key])
                            row['bitwise_match'] = True
                            report.pop('pending_comparison')
                        else:
                            expected[key] = snapshot
                    report['steps'].append(row); save(); dist.barrier()
                del optimizer
        assert editor_state_digest(rt.model) == native_hash
        assert all(p.grad is None for p in rt.model.parameters())
        assert b.counts == dict(c4=0, input_embedder=0, recycle=0, s1=0, updates=0)
        for handle in handles: handle.remove()
        handles.clear(); rt.finish()
        report.update(counts=dict(counts), native_counts=dict(b.counts), phase='complete', complete=True)
        save(); dist.barrier()
    except BaseException as error:
        report.update(phase='failed', error=repr(error), counts=dict(counts)); save()
        raise
    finally:
        for handle in handles: handle.remove()
        dist.destroy_process_group()


def verify_native_parallel_audit(root):
    """Reload saved audit states on CPU; retain timing as descriptive evidence."""
    root = Path(root); lock = json.loads((root/'audit_lock.json').read_text())
    reports = [json.loads((root/f'rank_{rank}/report.json').read_text()) for rank in range(6)]
    assert all(r['complete'] and r['audit_lock_sha256'] == sha256(root/'audit_lock.json') for r in reports)
    totals = Counter()
    for report in reports:
        totals.update(report['counts'])
        assert report['native_counts'] == dict(c4=0,input_embedder=0,recycle=0,s1=0,updates=0)
        assert len(report['steps']) == 12
    assert dict(totals) == dict(forwards=7182,backwards=7182,reference_forwards=378,reference_backwards=378)
    rows = reports[0]['steps']; pairs=[]
    for order in range(2):
        for step in range(1,4):
            snapshots=[]
            for method in ('serial','parallel'):
                row = next(r for r in rows if (r['order'],r['step'],r['method']) == (order,step,method))
                path = root/row['snapshot']; assert sha256(path) == row['sha256']
                snapshots.append(torch.load(path,map_location='cpu',weights_only=True))
            assert_tree_equal(*snapshots)
            pairs.append(dict(order=order,step=step,bitwise=True))
    by_order=[]
    for order in range(2):
        times={method:sum(r['seconds'] for r in rows if r['order']==order and r['method']==method) for method in ('serial','parallel')}
        by_order.append(dict(order=lock['orders'][order],**times,speedup=times['serial']/times['parallel']))
    result=dict(complete=True,bitwise_pairs=pairs,counts=dict(totals),orders=by_order,
                aggregate_speedup=sum(x['serial'] for x in by_order)/sum(x['parallel'] for x in by_order),
                all_ranks_peak_bytes=[max(x['peak_allocated_bytes'] for x in r['steps']) for r in reports],
                inference_speedup_measured=False,model_quality_measured=False,
                audit_lock_sha256=sha256(root/'audit_lock.json'))
    write_json(root/'verification.json',result)
    return result
