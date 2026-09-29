#!/usr/bin/env python3
"""Fixed old-six CPU fitting diagnosis, with separate prepare/batch/case modes."""
import argparse
import concurrent.futures
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

import numpy as np
import torch

from fastglycan.articulated_output import ArticulatedOutput, AA
from fastglycan.articulated_reference import geometry_invariants
from fastglycan.anchored_geometry import PoseVariables, JointObjective
from fastglycan.geometry_repair import preservation
from fastglycan.local_projection_fit import fit_local_projection
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.repair_outcomes import absolute_failures


def prepare(args):
    root = args.root
    assert not (root / 'lock.json').exists()
    old = json.loads((args.source / 'lock.json').read_text())
    assert [(x['arm'], x['seed']) for x in old['cases']] == [
        (arm, seed) for arm in ['controlled_s1', 'native_s5'] for seed in [211, 200003, 200009]]
    for key in ['reference', 'variants', 'topology']:
        assert sha256(Path(old[key])) == old[key + '_sha256']
    for case in old['cases']:
        assert sha256(Path(case['file'])) == case['sha256']
    sources = {}
    modules = ['local_projection_fit', 'anchored_geometry', 'articulated_output',
               'articulated_reference', 'hybrid_geometry', 'geometry_repair',
               'repair_outcomes', 'paired_teacher_protocol']
    for name in modules:
        path = Path(inspect.getfile(__import__('fastglycan.' + name, fromlist=['x'])))
        sources[str(path)] = sha256(path)
        if name in ['anchored_geometry', 'articulated_output', 'articulated_reference']:
            expected = [v for k, v in old['source_hashes'].items() if Path(k).name == path.name]
            assert expected == [sources[str(path)]]
    for path in [Path(__file__), root / 'code/docs/mini_local_projection_fit_execution_v1.md']:
        sources[str(path)] = sha256(path)
    root.mkdir(exist_ok=True)
    write_json(root / 'lock.json', dict(
        source=str(args.source), source_lock_sha256=sha256(args.source / 'lock.json'),
        sequence=old['sequence'], cases=old['cases'],
        **{k: old[k] for key in ['reference', 'variants', 'topology'] for k in [key, key + '_sha256']},
        source_hashes=sources, device='cpu', dtype='float64', workers=2, timeout_seconds=900,
        max_iter=60, max_eval=90, scope='old same-parent development inputs; no GT or new model forward',
    ))


def run_case(args):
    root = args.root
    lock = json.loads((root / 'lock.json').read_text())
    item = lock['cases'][args.case]
    folder = root / 'cases' / f'{args.case:02d}'
    folder.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    result = dict(case=args.case, arm=item['arm'], seed=item['seed'], success=False,
                  lock_sha256=sha256(root / 'lock.json'))
    try:
        torch.set_num_threads(1)
        for path, digest in lock['source_hashes'].items():
            assert sha256(Path(path)) == digest
        for key in ['reference', 'variants', 'topology']:
            assert sha256(Path(lock[key])) == lock[key + '_sha256']
        assert sha256(Path(item['file'])) == item['sha256']
        ref = dict(np.load(lock['reference']))
        data = dict(np.load(item['file']))
        for key in ['atom_names', 'residue_ids', 'chain_ids']:
            assert np.array_equal(ref[key], data[key])
        names, residues = ref['atom_names'], ref['residue_ids']
        variants = json.loads(Path(lock['variants']).read_text())
        raw = torch.tensor(data['coordinates'].reshape(-1, 3), dtype=torch.float64)
        adapter = ArticulatedOutput(ref['reference'], names, residues, lock['sequence'], variants).double()
        fit = fit_local_projection(adapter, raw, max_iter=lock['max_iter'], max_eval=lock['max_eval'])
        result['fit_seconds'] = time.monotonic() - start
        with torch.no_grad():
            replay = PoseVariables(adapter, raw).coordinates(fit.values)
        result['parameter_replay_max_abs'] = float((replay - fit.coordinates).abs().max())
        assert result['parameter_replay_max_abs'] < 1e-10
        old_path = Path(lock['source']) / 'cases' / f'{args.case:02d}' / 'coordinates.npz'
        old_report = json.loads((old_path.parent / 'report.json').read_text())
        assert sha256(old_path) == old_report['coordinates_sha256']
        previous = np.load(old_path)
        result['old_initial_max_abs'] = float(np.abs(fit.initial.numpy() - previous['initial']).max())
        assert result['old_initial_max_abs'] < 1e-8
        topology = torch.load(lock['topology'], map_location='cpu', weights_only=False)['topology']
        anchors = [[int(np.flatnonzero((residues == i) & (names == n))[0]) for n in ['N', 'CA', 'C', 'O']]
                   for i in range(1, len(lock['sequence']) + 1)]
        objective = JointObjective(raw, anchors, lock['sequence'], topology.pairs, topology.radii)
        side = [[int(np.flatnonzero((residues == i) & (names == n))[0])
                 for n in ['CB', 'CA', 'CG1' if aa == 'I' else 'OG1', 'CG2']]
                for i, aa in enumerate(lock['sequence'], 1) if aa in 'IT']
        side = np.asarray(side, dtype=int).reshape(-1, 4)
        def volumes(x):
            c, a, b, d = side.T
            return (np.cross(x[a] - x[c], x[b] - x[c]) * (x[d] - x[c])).sum(-1)
        reference_side = volumes(ref['reference'])
        bone = np.isin(names, ['N', 'CA', 'C', 'O'])
        result['metrics'] = {}
        arrays = dict(raw=raw.numpy(), initial=fit.initial.numpy(), final=fit.coordinates.numpy())
        for label, x in arrays.items():
            _, geometry = topology.terms(torch.tensor(x))
            residuals = objective.residuals(torch.tensor(x))
            maxima = {key: float(value.abs().max()) for key, value in residuals.items()}
            tolerances = dict(cn=.03, angle_c=.04, angle_n=.04, omega=.1, carbonyl=.1)
            failures = absolute_failures(geometry)
            pres = preservation(arrays['raw'], x, np.asarray(anchors)[:, 1])
            chirality = geometry['chirality_fraction'] == 1. and bool((volumes(x) * reference_side > 0).all())
            connection = all(maxima[k] <= value + 1e-6 for k, value in tolerances.items())
            squared = ((x - arrays['raw']) ** 2).sum(-1)
            result['metrics'][label] = dict(
                geometry=geometry, absolute_failures=failures, connection_max=maxima,
                connection_pass=connection, all_checked_chirality_pass=chirality,
                preservation=pres, joint_pass=not failures and pres['accepted'] and chirality and connection,
                mse=float(squared.mean()), backbone_mse=float(squared[bone].mean()),
                sidechain_mse=float(squared[~bone].mean()),
            )
        local = []
        for i, aa in enumerate(lock['sequence'], 1):
            selected = residues == i
            bonds = variants[AA[aa] + ':' + ','.join(names[selected])]['bonds']
            lengths, angles = geometry_invariants(ref['reference'][selected], bonds)
            after_lengths, after_angles = geometry_invariants(arrays['final'][selected], bonds)
            local.append(dict(residue=i, bond_error=float(np.abs(lengths - after_lengths).max()),
                              angle_cosine_error=float(np.abs(angles - after_angles).max()),
                              initial_mse=float(((arrays['initial'][selected] - arrays['raw'][selected]) ** 2).sum(-1).mean()),
                              final_mse=float(((arrays['final'][selected] - arrays['raw'][selected]) ** 2).sum(-1).mean())))
        result.update(local_residues=local, initial_mse=fit.initial_mse, final_mse=fit.final_mse,
                      iterations=fit.iterations, closure_calls=fit.closure_calls,
                      final_gradient_norm=fit.final_gradient_norm, improved=fit.improved)
        np.savez_compressed(folder / 'coordinates.npz', **arrays, atom_names=names,
                            residue_ids=residues, chain_ids=ref['chain_ids'])
        torch.save(fit.values, folder / 'values.pt')
        result.update(success=True, coordinates_sha256=sha256(folder / 'coordinates.npz'),
                      values_sha256=sha256(folder / 'values.pt'))
    except Exception:
        result['error'] = traceback.format_exc()
    result['seconds'] = time.monotonic() - start
    write_json(folder / 'report.json', result)
    if not result['success']:
        raise RuntimeError(result['error'])


def batch(args):
    lock = json.loads((args.root / 'lock.json').read_text())
    def worker(index):
        with (args.root / f'case_{index:02d}.log').open('x') as log:
            try:
                p = subprocess.run([sys.executable, __file__, '--root', str(args.root),
                                    '--mode', 'case', '--case', str(index)], stdout=log, stderr=log,
                                   timeout=lock['timeout_seconds'], env=dict(os.environ, ROCR_VISIBLE_DEVICES='',
                                   OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1'))
                return dict(case=index, returncode=p.returncode)
            except subprocess.TimeoutExpired:
                return dict(case=index, returncode=124, timeout=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=lock['workers']) as pool:
        execution = list(pool.map(worker, range(6)))
    cases = []
    for row in execution:
        path = args.root / 'cases' / f"{row['case']:02d}" / 'report.json'
        cases.append(json.loads(path.read_text()) if path.exists() else dict(case=row['case'], success=False, error='missing report'))
    write_json(args.root / 'report.json', dict(complete=True, expected=6, execution=execution,
        cases=cases, lock_sha256=sha256(args.root / 'lock.json'),
        scope='raw-coordinate fitting diagnosis; no experimental GT or design acceptance'))
    write_json(args.root / 'exit.json', dict(exit_code=0 if all(x['returncode'] == 0 for x in execution) else 1))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--mode', choices=['prepare', 'batch', 'case'], required=True)
    parser.add_argument('--case', type=int)
    options = parser.parse_args()
    {'prepare': prepare, 'batch': batch, 'case': run_case}[options.mode](options)
