#!/usr/bin/env python3
"""Freeze one initialization intervention, reusing audited C4 zero controls."""
import argparse
import json
from pathlib import Path

from fastglycan.paired_teacher_protocol import sha256, write_json


def prepare_c4_fit_start(root, baseline):
    assert not (root / 'lock.json').exists()
    previous = json.loads((baseline / 'lock.json').read_text())
    audit = json.loads((baseline / 'audit.json').read_text())
    assert previous['prediction_contract'] == 'c4_s1_confirmation_v1'
    assert audit['verified'] == 28 and audit['paired'] == 14
    assert audit['report_sha256'] == sha256(baseline / 'report.json')
    assert json.loads((baseline / 'pipeline_exit.json').read_text())['returncode'] == 0
    for path, digest in previous['hashes'].items():
        assert sha256(Path(path)) == digest
    hashes = dict(previous['hashes'])
    for path in [baseline / name for name in ['lock.json', 'report.json', 'audit.json', 'pipeline_exit.json']]:
        hashes[str(path)] = sha256(path)
    for folder in [baseline / 'cases', root / 'code']:
        for path in folder.rglob('*'):
            if path.is_file() and path.suffix in ['.py', '.md', '.json', '.pt', '.npz']:
                hashes[str(path)] = sha256(path)
    for name in ['anchored_geometry.py', 'anchored_tail.py', 'articulated_output.py',
                 'calibrated_connection_objective.py', 'local_projection_fit.py', 'geometry_start.py']:
        old = {h for p, h in previous['hashes'].items() if Path(p).name == name}
        assert old == {sha256(root / 'code/src/fastglycan' / name)}
    write_json(root / 'lock.json', dict(source=previous['source'], baseline=str(baseline),
        calibration=previous['calibration'], hashes=hashes,
        initialization_contract='calibrated_c4_fitted_start_v1', arms=['zero', 'fitted'],
        planned=32, supported=28, reused_controls=14, newly_computed_solves=14,
        seeds=[12345, 54321], workers=2, timeout_seconds=900, device='cpu', dtype='float64',
        joint_iterations=180, extra_fit_iterations=60, extra_fit_max_eval=90,
        scope='C4 development initialization-only; frozen calibrated objective and raw chart; no GT in solve'))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--baseline', type=Path, required=True)
    a = p.parse_args()
    prepare_c4_fit_start(a.root.resolve(), a.baseline.resolve())
