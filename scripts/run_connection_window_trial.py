#!/usr/bin/env python3
"""Paired old/calibrated connection onsets in the frozen anchored solver."""
import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
import traceback

import numpy as np
import torch

from run_projection_joint_start import buffer_digest
from fastglycan.anchored_geometry import PoseVariables, solve
from fastglycan.anchored_tail import TailObjective
from fastglycan.calibrated_connection_objective import CalibratedConnectionObjective
from fastglycan.articulated_output import ArticulatedOutput
from fastglycan.connection_audit import measure_connections
from fastglycan.geometry_repair import preservation
from fastglycan.hybrid_geometry import GeometryTopology
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.repair_outcomes import absolute_failures
from fastglycan.scaling_metrics import lddt_observed


def prepare_window_trial(root, source, baseline, calibration):
    assert not (root / 'lock.json').exists()
    earlier = json.loads((baseline / 'lock.json').read_text())
    assert earlier['source'] == str(source)
    audit = json.loads((baseline / 'audit.json').read_text())
    assert audit['verified'] == 28 and audit['paired'] == 14
    assert audit['report_sha256'] == sha256(baseline / 'report.json')
    for path, digest in earlier['hashes'].items():
        assert sha256(Path(path)) == digest
    hashes = dict(earlier['hashes'])
    for folder in [baseline / 'cases', root / 'code']:
        for path in folder.rglob('*'):
            if path.is_file() and path.suffix in ['.py', '.md', '.json', '.npz', '.pt']:
                hashes[str(path)] = sha256(path)
    for path in [baseline / 'report.json', baseline / 'audit.json', calibration]:
        hashes[str(path)] = sha256(path)
    document = json.loads(calibration.read_text())
    assert document['calibration_proteins'] == 32 and not document['failures']
    assert document['not_acceptance_thresholds']
    for name in ['anchored_geometry.py', 'anchored_tail.py', 'articulated_output.py']:
        values = {v for p, v in earlier['hashes'].items() if Path(p).name == name}
        assert values == {sha256(root / 'code/src/fastglycan' / name)}
    write_json(root / 'lock.json', dict(source=str(source), baseline=str(baseline),
        calibration=str(calibration), hashes=hashes, planned=32, supported=28,
        seeds=[12345, 54321], arms=['original', 'calibrated'], workers=2,
        timeout_seconds=900, device='cpu', dtype='float64', joint_iterations=180,
        scope='connection onset only; unchanged curvature, branches, zero chart and old gates; historical C1/S1'))


def run_window_case(root, index):
    torch.set_num_threads(1)
    lock = json.loads((root / 'lock.json').read_text()); source = Path(lock['source'])
    selection = json.loads((source / 'selection.json').read_text())
    item = selection[index // 4]; seed = lock['seeds'][(index // 2) % 2]; arm = lock['arms'][index % 2]
    group = item['group_id']; packet = source / 'chemistry' / group
    folder = root / 'cases' / f'{index:02d}'; folder.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    result = dict(index=index, group_id=group, pdb_id=item['pdb_id'], seed=seed, arm=arm,
                  success=False, lock_sha256=sha256(root / 'lock.json'))
    try:
        for path, digest in lock['hashes'].items():
            assert sha256(Path(path)) == digest
        chemistry = json.loads((packet / 'report.json').read_text())
        if not chemistry['passed']:
            result.update(not_run=True, source_failure=chemistry['error']); return
        mapping = dict(np.load(packet / 'mapping.npz')); assert mapping['mask'].all()
        names, residues = mapping['atom_names'], mapping['residue_ids']
        inv = dict(np.load(source / 'data' / group / 'inventory.npz'))
        assert np.array_equal(names, inv['atom_name']) and np.array_equal(residues, inv['residue_id'])
        raw_array = np.load(source / 'data' / group / f'native_{seed}.npy').astype(np.float64)
        raw = torch.tensor(raw_array)
        adapter = ArticulatedOutput(mapping['reference'], names, residues, item['sequence'],
            json.loads((packet / 'variants.json').read_text())).double()
        variables = PoseVariables(adapter, raw); start = variables().detach().clone()
        previous = Path(lock['baseline']) / 'cases' / f'{index // 2 * 2:02d}'
        old = dict(np.load(previous / 'coordinates.npz'))
        assert np.array_equal(raw_array, old['raw'])
        assert np.max(np.abs(start.numpy() - old['start'])) < 1e-8
        atoms = torch.load(packet / 'native.pt', map_location='cpu', weights_only=False)['atoms']
        topology = GeometryTopology(atoms, mapping['reference'])
        anchors = np.array([[int(np.flatnonzero((residues == j) & (names == name))[0])
            for name in ['N', 'CA', 'C', 'O']] for j in range(1, len(item['sequence']) + 1)])
        args = (raw, anchors, item['sequence'], topology.pairs, topology.radii)
        base = TailObjective(*args)
        objective = base if arm == 'original' else CalibratedConnectionObjective(
            *args, json.loads(Path(lock['calibration']).read_text()))
        for name, value in base.named_buffers():
            assert torch.equal(value, dict(objective.named_buffers())[name])
        result.update(chart_sha256=buffer_digest(variables), objective_sha256=buffer_digest(objective),
            shared_objective_sha256=buffer_digest(base), raw_sha256=sha256(source / 'data' / group / f'native_{seed}.npy'),
            start_replay_max_abs=float(np.max(np.abs(start.numpy() - old['start']))))
        with torch.no_grad():
            loss, terms = objective(start, variables.variables, 1.)
        result['start_objective'] = dict(loss=float(loss), terms={k: float(v) for k, v in terms.items()})
        if arm == 'calibrated':
            result['connection_onsets'] = objective.connection_onsets.tolist()
        initial_values = tuple(p.detach().clone() for p in variables.variables)
        write_json(folder / 'progress.json', dict(stage='initialized', **result))
        def callback(state):
            write_json(folder / 'progress.json', dict(stage='solving', seconds=time.monotonic()-started, **state))
        begin = time.monotonic(); final, history = solve(variables, objective, callback)
        result.update(solver_seconds=time.monotonic()-begin, history=history)
        assert buffer_digest(variables) == result['chart_sha256']
        assert buffer_digest(objective) == result['objective_sha256']
        if arm == 'original':
            result['historical_baseline_max_abs'] = float(np.max(np.abs(final.numpy() - old['final'])))
            result['historical_baseline_bitwise'] = np.array_equal(final.numpy(), old['final'])
            assert result['historical_baseline_max_abs'] < 1e-8
        arrays = dict(raw=raw_array, local=variables.initial.numpy(), start=start.numpy(), final=final.numpy(),
                      target=mapping['coordinates'].astype(np.float64))
        ca = names == 'CA'; bone = np.isin(names, ['N', 'CA', 'C', 'O'])
        side = np.array([[int(np.flatnonzero((residues == j) & (names == n))[0])
            for n in ['CB', 'CA', 'CG1' if aa == 'I' else 'OG1', 'CG2']]
            for j, aa in enumerate(item['sequence'], 1) if aa in 'IT'], dtype=int).reshape(-1, 4)
        def volume(x):
            c, a, b, d = side.T
            return (np.cross(x[a]-x[c], x[b]-x[c])*(x[d]-x[c])).sum(-1)
        reference_volume = volume(mapping['reference'])
        gt_branch = measure_connections(arrays['target'], anchors, item['sequence'])['nearest_omega_sign']
        raw_branch = base.omega_target[:, 0].numpy()
        result['raw_branch_mismatches'] = np.flatnonzero(gt_branch != raw_branch).tolist()
        result['metrics'] = {}
        for label in ['raw', 'local', 'start', 'final']:
            x = arrays[label]; tx = torch.tensor(x)
            _, geometry = topology.terms(tx)
            connection = {k: float(v.abs().max()) for k, v in base.residuals(tx).items()}
            connected = all(connection[k] <= tol+1e-6 for k, tol in
                dict(cn=.03, angle_c=.04, angle_n=.04, omega=.1, carbonyl=.1).items())
            chirality = geometry['chirality_fraction'] == 1 and bool((volume(x)*reference_volume > 0).all())
            failures = absolute_failures(geometry); pres = preservation(raw_array, x, np.flatnonzero(ca))
            squared = ((x-raw_array)**2).sum(-1)
            branch = measure_connections(x, anchors, item['sequence'])['nearest_omega_sign']
            result['metrics'][label] = dict(all_atom_lddt=lddt_observed(x, arrays['target'], residues)['score'],
                ca_lddt=lddt_observed(x[ca], arrays['target'][ca], residues[ca])['score'],
                geometry=geometry, connection_max=connection, connection_pass=connected,
                all_checked_chirality_pass=chirality, absolute_failures=failures, preservation=pres,
                joint_pass=not failures and pres['accepted'] and chirality and connected,
                zero_severe_chirality_budget=geometry['severe_pairs'] == 0 and chirality and pres['accepted'],
                branch_mismatches=np.flatnonzero(branch != gt_branch).tolist(),
                backbone_raw_mse=float(squared[bone].mean()), sidechain_raw_mse=float(squared[~bone].mean()))
        with torch.no_grad():
            a, _ = base(final, variables.variables, 100.)
            b, _ = CalibratedConnectionObjective(*args, json.loads(Path(lock['calibration']).read_text()))(final, variables.variables, 100.)
        result['final_cross_objectives'] = dict(original=float(a), calibrated=float(b))
        np.savez_compressed(folder / 'coordinates.npz', **arrays, atom_names=names, residue_ids=residues)
        torch.save(dict(initial=initial_values, final=tuple(p.detach().clone() for p in variables.variables)), folder / 'values.pt')
        result.update(success=True, coordinates_sha256=sha256(folder / 'coordinates.npz'),
            values_sha256=sha256(folder / 'values.pt'), peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    except Exception:
        result['error'] = traceback.format_exc()
    finally:
        result['seconds'] = time.monotonic()-started; write_json(folder / 'report.json', result)
    if not result['success']:
        raise RuntimeError(result.get('error', 'case failed'))


def batch_window_trial(root):
    lock = json.loads((root / 'lock.json').read_text()); assert not (root / 'controller.json').exists()
    write_json(root / 'controller.json', dict(pid=os.getpid(), phase='running', planned=32))
    def worker(index):
        with (root / f'case_{index:02d}.log').open('x') as log:
            try:
                p = subprocess.run([sys.executable, __file__, '--root', str(root), '--mode', 'case', '--index', str(index)],
                    stdout=log, stderr=log, timeout=lock['timeout_seconds'])
                return dict(index=index, returncode=p.returncode)
            except subprocess.TimeoutExpired:
                return dict(index=index, returncode=124)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        execution = list(pool.map(worker, range(32)))
    rows = []
    for i in range(32):
        f = root / 'cases' / f'{i:02d}' / 'report.json'
        rows.append(json.loads(f.read_text()) if f.exists() else dict(index=i, success=False, error='missing report'))
    write_json(root / 'report.json', dict(complete=True, lock_sha256=sha256(root / 'lock.json'),
        rows=rows, execution=execution, successful=sum(x['success'] for x in rows), expected=32))
    write_json(root / 'exit.json', dict(process_failures=sum(x['returncode'] != 0 for x in execution),
        successful=sum(x['success'] for x in rows), source_skipped=sum(x.get('not_run', False) for x in rows)))
    write_json(root / 'controller.json', dict(pid=os.getpid(), phase='finished', planned=32))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--root', type=Path, required=True)
    for key in ['source', 'baseline', 'calibration']:
        p.add_argument('--'+key, type=Path)
    p.add_argument('--mode', choices=['prepare', 'batch', 'case'], required=True); p.add_argument('--index', type=int)
    a = p.parse_args()
    if a.mode == 'prepare':
        prepare_window_trial(a.root, a.source, a.baseline, a.calibration)
    elif a.mode == 'batch':
        batch_window_trial(a.root)
    else:
        run_window_case(a.root, a.index)
