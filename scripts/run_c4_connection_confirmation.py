#!/usr/bin/env python3
"""Bounded C4/S1 raw generation and sealing for the frozen paired repair."""
import argparse
import concurrent.futures
import copy
import importlib
import inspect
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback

import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256, write_json

SEEDS = [12345, 54321]
BASE = Path('/media/PM982/onestepfold')


def prepare_c4_confirmation(root):
    assert not (root / 'runtime_lock.json').exists()
    original = BASE / 'local_fit_gt_source_v1_20260930'
    source = root / 'source'; source.mkdir()
    rows = json.loads((original / 'selection.json').read_text())
    assert len(rows) == 8
    for row in rows:
        row.pop('native_predictions', None)
        group = row['group_id']
        packet = source / 'chemistry' / group; packet.parent.mkdir(exist_ok=True)
        packet.symlink_to(original / 'chemistry' / group, target_is_directory=True)
        folder = source / 'data' / group; folder.mkdir(parents=True)
        for name in ['gt.npz', 'gt.json', 'inventory.npz', 'prepared.json']:
            folder.joinpath(name).symlink_to(original / 'data' / group / name)
    write_json(source / 'selection.json', rows)
    hashes = {str(p): sha256(p) for p in (root / 'code').rglob('*')
              if p.is_file() and p.suffix in ['.py', '.md']}
    for name in ['protenix', 'esm', 'runner', 'configs']:
        folder = Path(inspect.getfile(importlib.import_module(name))).parent
        hashes.update({str(p): sha256(p) for p in folder.rglob('*.py')})
    inputs = {str(source / 'selection.json'): sha256(source / 'selection.json')}
    for row in rows:
        packet = source / 'chemistry' / row['group_id']
        for p in packet.iterdir():
            if p.is_file(): inputs[str(p)] = sha256(p)
        for p in (source / 'data' / row['group_id']).iterdir():
            if p.exists(): inputs[str(p)] = sha256(p)
    previous = json.loads((BASE / 'independent32_v2_20260930/runtime_lock.json').read_text())
    weights = previous['weights_sha256']
    for p, digest in weights.items(): assert sha256(Path(p)) == digest
    write_json(root / 'runtime_lock.json', dict(source=str(source), source_hashes=hashes,
        input_hashes=inputs, weights_sha256=weights,
        weight_stats={p: [Path(p).stat().st_size, Path(p).stat().st_mtime_ns] for p in weights},
        model='protenix_mini_esm_v0.5.0', dtype='fp32', cycles=4, steps=1,
        seeds=SEEDS, torch_version=torch.__version__, gt_in_model=False,
        source_slots=8, expected_supported=7, raw_timeout=5400))


def raw_c4_confirmation(root, index):
    from fastglycan import stage0_confirm_runtime as rt
    from fastglycan.models.soft_sequence_chart import device_tree
    from fastglycan.models.differentiable_mini import (
        full_recycle_pairformer, diffusion_from_conditioning, prepare_atom_pairs)
    from fastglycan.hybrid_proposals import identity_noise
    lock = json.loads((root / 'runtime_lock.json').read_text())
    source = Path(lock['source']); rows = json.loads((source / 'selection.json').read_text())
    row = rows[index]; group = row['group_id']; packet = source / 'chemistry' / group
    folder = root / 'raw' / group; folder.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    report = dict(index=index, group_id=group, pdb_id=row['pdb_id'], complete=False,
        results={}, runtime_lock_sha256=sha256(root / 'runtime_lock.json'))
    try:
        for p, digest in lock['source_hashes'].items(): assert sha256(Path(p)) == digest
        # Raw model execution deliberately does not open GT or chemistry mapping.
        for p in [packet / 'report.json', packet / 'native.pt']:
            if p.exists(): assert sha256(p) == lock['input_hashes'][str(p)]
        chemistry = json.loads((packet / 'report.json').read_text())
        if not chemistry['passed']:
            report.update(not_run=True, source_failure=chemistry['error'])
            return
        for p, stat in lock['weight_stats'].items():
            assert [Path(p).stat().st_size, Path(p).stat().st_mtime_ns] == stat
        torch.set_num_threads(1)
        runner = rt.runner_setup(folder / 'work'); runner.configs.dtype = 'fp32'
        model = runner.model.eval().requires_grad_(False)
        assert all(p.dtype == torch.float32 for p in model.parameters() if p.is_floating_point())
        torch.serialization.add_safe_globals([argparse.Namespace])
        from protenix.data.esm.compute_esm import load_esm_model
        esm, alphabet = load_esm_model('esm2-3b', local_esm_dir=runner.configs.load_checkpoint_dir)
        esm.eval().requires_grad_(False)
        native = torch.load(packet / 'native.pt', map_location='cpu', weights_only=False)
        atoms = native['atoms']; base = device_tree(native['features'], 'cuda')
        assert len(set(atoms.chain_id)) == 1
        report.update(model=rt.MODEL, resolved_config=runner.configs.to_dict(),
            device=torch.cuda.get_device_name(0), load_seconds=time.monotonic()-start,
            effective=dict(dtype='fp32', autocast=False, cycles=4, steps=1, mc_dropout=False,
                gamma0=0, noise_scale_lambda=1, step_scale_eta=1, stable_euler=True,
                augmentation='identity', initial_noise='identity-key', conditioning_shared=True),
            gt_in_model=False, native_packet_sha256=sha256(packet / 'native.pt'))
        write_json(folder / 'report.json', report)
        counts = dict(pairformer=0, diffusion=0)
        def counted(name):
            def hook(module, args, output): counts[name] += 1
            return hook
        ph = model.pairformer_stack.register_forward_hook(counted('pairformer'))
        dh = model.diffusion_module.register_forward_hook(counted('diffusion'))
        with torch.no_grad():
            tokens = alphabet.get_batch_converter()([('sequence', row['sequence'])])[2].cuda()
            base['esm_token_embedding'] = esm(tokens, repr_layers=[esm.num_layers],
                return_contacts=False)['representations'][esm.num_layers][0, 1:-1]
            del esm, tokens; torch.cuda.empty_cache()
            features = prepare_atom_pairs(model.relative_position_encoding.generate_relp(copy.deepcopy(base)))
            t = time.monotonic()
            point = full_recycle_pairformer(model, features, N_cycle=4, inplace_safe=False, mc_dropout=False)
            shapes = [x.shape for x in point]; sizes = [x.numel() for x in point]
            conditioning = tuple(x.reshape(s) for x, s in zip(
                torch.cat([x.flatten() for x in point]).split(sizes), shapes))
            del point
            assert counts['pairformer'] == 4
            torch.cuda.synchronize(); report['conditioning_seconds'] = time.monotonic()-t
            for seed in SEEDS:
                t = time.monotonic(); before = counts['diffusion']
                noise = identity_noise(atoms, seed, device='cuda')
                x = diffusion_from_conditioning(model, features, noise, conditioning, steps=1)
                torch.cuda.synchronize()
                assert counts['diffusion']-before == 1 and torch.isfinite(x).all()
                array = x.cpu().numpy().reshape(-1, 3)
                assert array.dtype == np.float32 and len(array) == len(atoms)
                file = source / 'data' / group / f'native_{seed}.npy'
                np.save(file, array)
                report['results'][str(seed)] = dict(file=str(file), sha256=sha256(file),
                    seconds=time.monotonic()-t, diffusion_nfe=1,
                    schedule=model.inference_noise_scheduler(N_step=1, device='cpu', dtype=torch.float32).tolist())
                if seed == SEEDS[0]:
                    replay = diffusion_from_conditioning(model, features,
                        identity_noise(atoms, seed, device='cuda'), conditioning, steps=1)
                    assert torch.equal(replay, x)
                    report['exact_replay'] = dict(seed=seed, bitwise=True, extra_nfe=1)
                write_json(folder / 'report.json', report)
            ph.remove(); dh.remove()
        np.savez_compressed(folder / 'identity.npz', atom_names=atoms.atom_name,
            residue_ids=atoms.res_id, chain_ids=atoms.chain_id, sequence=row['sequence'])
        assert counts == dict(pairformer=4, diffusion=3)
        report.update(complete=True, counts=counts,
            identity_sha256=sha256(folder / 'identity.npz'),
            peak_allocated_bytes=torch.cuda.max_memory_allocated())
    except Exception:
        report['error'] = traceback.format_exc()
    finally:
        report['seconds'] = time.monotonic()-start
        write_json(folder / 'report.json', report)
    if not report['complete']: raise RuntimeError(report.get('error', 'raw failed'))


def batch_c4_confirmation(root):
    assert not (root / 'raw_controller.json').exists()
    write_json(root / 'raw_controller.json', dict(pid=os.getpid(), phase='running'))
    def worker(index):
        env = dict(os.environ, ROCR_VISIBLE_DEVICES=str(index), OMP_NUM_THREADS='1',
                   OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
        with (root / f'raw_{index}.log').open('x') as log:
            try:
                p = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--root', str(root),
                    '--mode', 'raw', '--index', str(index)], env=env, stdout=log, stderr=log, timeout=5400)
                return dict(index=index, returncode=p.returncode)
            except subprocess.TimeoutExpired:
                return dict(index=index, returncode=124)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(worker, range(8)))
    write_json(root / 'raw_execution.json', dict(results=results))
    write_json(root / 'raw_controller.json', dict(pid=os.getpid(), phase='finished'))
    assert all(r['returncode'] == 0 for r in results), results


def seal_c4_confirmation(root):
    lock = json.loads((root / 'runtime_lock.json').read_text()); source = Path(lock['source'])
    for p, digest in {**lock['source_hashes'], **lock['input_hashes'], **lock['weights_sha256']}.items():
        assert sha256(Path(p)) == digest
    rows = json.loads((source / 'selection.json').read_text()); verified = []
    hashes = dict(lock['input_hashes'])
    # Solver processes check small code/input assets; giant checkpoint files were
    # hashed before and after inference here, not repeatedly by every CPU solve.
    hashes.update({p: d for p, d in lock['source_hashes'].items() if p.startswith(str(root))})
    for row in rows:
        group = row['group_id']; packet = source / 'chemistry' / group
        folder = root / 'raw' / group; report = json.loads((folder / 'report.json').read_text())
        hashes[str(folder / 'report.json')] = sha256(folder / 'report.json')
        if not json.loads((packet / 'report.json').read_text())['passed']:
            assert report['not_run']; continue
        assert report['complete'] and report['counts'] == dict(pairformer=4, diffusion=3)
        assert report['exact_replay']['bitwise'] and not report['gt_in_model']
        assert report['runtime_lock_sha256'] == sha256(root / 'runtime_lock.json')
        identity = dict(np.load(folder / 'identity.npz'))
        mapping = dict(np.load(packet / 'mapping.npz'))
        for field in ['atom_names', 'residue_ids', 'chain_ids']:
            assert np.array_equal(identity[field], mapping[field])
        assert str(identity['sequence']) == row['sequence']
        for seed in SEEDS:
            entry = report['results'][str(seed)]; file = Path(entry['file'])
            assert sha256(file) == entry['sha256'] and entry['diffusion_nfe'] == 1
            assert entry['schedule'] == [2560., 0.]
            x = np.load(file); assert x.shape == (len(mapping['atom_names']), 3)
            assert x.dtype == np.float32 and np.isfinite(x).all()
            hashes[str(file)] = sha256(file)
        verified.append(group)
    assert len(verified) == 7
    calibration = BASE / 'connection_calibration_measure_v1_20260930/fitted_windows.json'
    document = json.loads(calibration.read_text())
    assert document['calibration_proteins'] == 32 and not document['failures']
    assert document['not_acceptance_thresholds']
    for p in [calibration, root / 'runtime_lock.json', root / 'raw_execution.json']:
        hashes[str(p)] = sha256(p)
    write_json(root / 'raw_audit.json', dict(complete=True, verified_proteins=len(verified),
        verified_predictions=14, exact_forward_replays=7, source_skipped=1,
        weights_before_after_identical=True, scope='artifact/call/replay audit; no independent model rerun'))
    hashes[str(root / 'raw_audit.json')] = sha256(root / 'raw_audit.json')
    assert not (root / 'lock.json').exists()
    write_json(root / 'lock.json', dict(source=str(source), baseline=None,
        prediction_contract='c4_s1_confirmation_v1', calibration=str(calibration), hashes=hashes,
        planned=32, supported=28, seeds=SEEDS, arms=['original', 'calibrated'], workers=2,
        timeout_seconds=900, device='cpu', dtype='float64', joint_iterations=180,
        scope='C4/S1 development confirmation; old gates, fixed solver, no GT in objective'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--mode', choices=['prepare', 'raw', 'batch', 'seal'], required=True)
    parser.add_argument('--index', type=int)
    args = parser.parse_args(); root = args.root.resolve()
    if args.mode == 'raw': raw_c4_confirmation(root, args.index)
    else: globals()[{'prepare': 'prepare_c4_confirmation', 'batch': 'batch_c4_confirmation',
                     'seal': 'seal_c4_confirmation'}[args.mode]](root)
