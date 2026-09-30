#!/usr/bin/env python3
"""Lock archived repulsive sidechain angles as the only joint-start change."""
import argparse
import json
from pathlib import Path

import numpy as np
import torch

from fastglycan.articulated_output import ArticulatedOutput
from fastglycan.geometry_start import pose_variables_at_start
from fastglycan.paired_teacher_protocol import sha256, write_json
from run_projection_joint_start import buffer_digest


def prepare_sidechain_joint_trial(root, baseline, warm):
    torch.set_num_threads(1)
    assert not (root / 'lock.json').exists()
    previous = json.loads((baseline / 'lock.json').read_text())
    fit_lock = json.loads((warm / 'lock.json').read_text())
    assert previous['reference_contract'] == 'calibrated_c4_ideal_reference_v1'
    assert fit_lock['contract'] == 'fixed_backbone_sidechain_repulsion_v1'
    assert fit_lock['baseline'] == str(baseline) and fit_lock['source'] == previous['source']
    hashes = dict(fit_lock['hashes'])
    for p, h in hashes.items():
        assert sha256(Path(p)) == h
    for folder, count in [(baseline, 28), (warm, 14)]:
        audit = json.loads((folder / 'audit.json').read_text())
        assert audit['verified'] == count and audit['report_sha256'] == sha256(folder / 'report.json')
        assert json.loads((folder / 'pipeline_exit.json').read_text())['returncode'] == 0
        for name in ['lock.json', 'report.json', 'audit.json', 'pipeline_exit.json']:
            hashes[str(folder / name)] = sha256(folder / name)
    for folder in [baseline / 'cases', warm / 'cases', root / 'code']:
        for path in folder.rglob('*'):
            if path.is_file() and path.suffix in ['.py', '.md', '.json', '.npz', '.pt']:
                hashes[str(path)] = sha256(path)
    for name in ['anchored_geometry.py', 'anchored_tail.py', 'articulated_output.py',
                 'articulated_reference.py', 'calibrated_connection_objective.py', 'ideal_output_reference.py']:
        assert {h for p, h in previous['hashes'].items() if Path(p).name == name} == {
            sha256(root / 'code/src/fastglycan' / name)}
    source = Path(previous['source']); selection = json.loads((source / 'selection.json').read_text())
    checks = []
    for i in range(16):
        item = selection[i // 2]; packet = source / 'chemistry' / item['group_id']
        if not json.loads((packet / 'report.json').read_text())['passed']:
            checks.append(dict(index=i, supported=False)); continue
        old_folder = baseline / 'cases' / f'{2*i+1:02d}'; fit_folder = warm / 'cases' / f'{i:02d}'
        old = json.loads((old_folder / 'report.json').read_text())
        fit = json.loads((fit_folder / 'report.json').read_text())
        assert old['success'] and fit['success'] and old['arm'] == 'ideal_ref'
        assert old['group_id'] == fit['group_id'] == item['group_id']
        assert old['seed'] == fit['seed'] == [12345, 54321][i % 2]
        for folder, row in [(old_folder, old), (fit_folder, fit)]:
            for file, key in [('coordinates.npz', 'coordinates_sha256'), ('values.pt', 'values_sha256')]:
                assert sha256(folder / file) == row[key]
        data = dict(np.load(fit_folder / 'coordinates.npz')); control = dict(np.load(old_folder / 'coordinates.npz'))
        for name in ['raw', 'target', 'output_reference', 'atom_names', 'residue_ids']:
            assert np.array_equal(data[name], control[name])
        assert np.array_equal(data['initial'], control['local'])
        values = torch.load(fit_folder / 'values.pt', map_location='cpu', weights_only=True)
        adapter = ArticulatedOutput(data['output_reference'], data['atom_names'], data['residue_ids'],
            item['sequence'], json.loads((packet / 'variants.json').read_text())).double()
        variables = pose_variables_at_start(adapter, torch.tensor(data['raw']), values['values'])
        assert buffer_digest(variables) == old['chart_sha256']
        err = float(np.max(np.abs(variables().detach().numpy() - data['final'])))
        assert err < 1e-8
        checks.append(dict(index=i, supported=True, start_max_abs=err, chart_sha256=buffer_digest(variables)))
    assert sum(c['supported'] for c in checks) == 14
    write_json(root / 'preflight.json', dict(cases=checks, verified=14))
    write_json(root / 'lock.json', dict(source=str(source), baseline=str(baseline), warm_start_root=str(warm),
        calibration=previous['calibration'], reference_templates=previous['reference_templates'], hashes=hashes,
        initialization_contract='calibrated_c4_sidechain_repulsion_start_v1', planned=32, supported=28,
        seeds=[12345, 54321], arms=['zero', 'sidechain'], workers=2, timeout_seconds=900,
        device='cpu', dtype='float64', joint_iterations=180,
        screen='positive paired protein-mean AA and CA; no loss of zero-severe/strict-chirality/raw-RMS count',
        scope='whole-ideal output fixed; load archived sidechain angles in original raw chart; reuse zero controls'))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for name in ['root', 'baseline', 'warm']:
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args(); prepare_sidechain_joint_trial(a.root, a.baseline, a.warm)
