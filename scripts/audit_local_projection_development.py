#!/usr/bin/env python3
"""Independent NumPy pose replay and coordinate metric audit; no optimizer rerun."""
import argparse
import json
from pathlib import Path

import numpy as np
import torch

from audit_anchored_geometry import replay, phase, cosine
from fastglycan.articulated_output import ArticulatedOutput
from fastglycan.anchored_geometry import PoseVariables
from fastglycan.paired_teacher_protocol import sha256, write_json

parser = argparse.ArgumentParser()
parser.add_argument('--root', type=Path, required=True)
args = parser.parse_args()
root = args.root
lock = json.loads((root / 'lock.json').read_text())
report = json.loads((root / 'report.json').read_text())
assert report['complete'] and len(report['cases']) == 6
assert report['lock_sha256'] == sha256(root / 'lock.json')
for path, digest in lock['source_hashes'].items():
    assert sha256(Path(path)) == digest
ref = dict(np.load(lock['reference']))
names, residues = ref['atom_names'], ref['residue_ids']
top = torch.load(lock['topology'], map_location='cpu', weights_only=False)['topology']
bonds, pairs = top.bonds.numpy(), top.pairs.numpy()
ca, n, c, cb = top.centres.numpy().T
side = [[int(np.flatnonzero((residues == i) & (names == name))[0])
         for name in ['CB', 'CA', 'CG1' if aa == 'I' else 'OG1', 'CG2']]
        for i, aa in enumerate(lock['sequence'], 1) if aa in 'IT']
sc, s1, s2, s3 = np.asarray(side, dtype=int).reshape(-1, 4).T
reference = ref['reference']
side_ref = (np.cross(reference[s1] - reference[sc], reference[s2] - reference[sc])
            * (reference[s3] - reference[sc])).sum(-1)
anchors = np.array([[int(np.flatnonzero((residues == i) & (names == name))[0])
                     for name in ['N', 'CA', 'C', 'O']] for i in range(1, len(lock['sequence']) + 1)])
adapter = ArticulatedOutput(reference, names, residues, lock['sequence'],
                            json.loads(Path(lock['variants']).read_text())).double()
audits = []
for result in report['cases']:
    if not result['success']:
        audits.append(dict(case=result['case'], verified=False, reason='fit failed'))
        continue
    folder = root / 'cases' / f"{result['case']:02d}"
    assert sha256(folder / 'coordinates.npz') == result['coordinates_sha256']
    assert sha256(folder / 'values.pt') == result['values_sha256']
    data = dict(np.load(folder / 'coordinates.npz'))
    source = lock['cases'][result['case']]
    assert sha256(Path(source['file'])) == source['sha256']
    assert np.array_equal(data['raw'], np.load(source['file'])['coordinates'].reshape(-1, 3))
    for key in ['atom_names', 'residue_ids', 'chain_ids']:
        assert np.array_equal(data[key], ref[key])
    variables = PoseVariables(adapter, torch.tensor(data['raw']))
    values = torch.load(folder / 'values.pt', map_location='cpu', weights_only=True)
    with torch.no_grad():
        for parameter, value in zip(variables.variables, values, strict=True):
            parameter.copy_(value)
    replay_error = float(np.abs(replay(variables) - data['final']).max())
    assert replay_error < 1e-8
    metric_error = 0.
    for stage in ['raw', 'initial', 'final']:
        x = data[stage]
        stored = result['metrics'][stage]
        lengths = np.linalg.norm(x[bonds[:, 0]] - x[bonds[:, 1]], axis=-1)
        residual = lengths - top.ideal.numpy()
        distance = np.linalg.norm(x[pairs[:, 0]] - x[pairs[:, 1]], axis=-1)
        volume = (np.cross(x[n] - x[ca], x[c] - x[ca]) * (x[cb] - x[ca])).sum(-1)
        geometry = dict(bond_rmse=float(np.sqrt(np.mean(residual ** 2))),
            peptide_mae=float(np.abs(residual[top.peptide.numpy()]).mean()),
            chirality_fraction=float((volume * top.volumes.numpy() > 0).mean()),
            severe_pairs=int((distance < 1).sum()), severe_pairs_per_atom=float((distance < 1).sum() / len(x)),
            max_penetration=float(np.maximum(0, top.radii.numpy()[pairs].sum(-1) - distance).max()))
        for key, value in geometry.items():
            metric_error = max(metric_error, abs(value - stored['geometry'][key]))
        side_wrong = ((np.cross(x[s1] - x[sc], x[s2] - x[sc]) * (x[s3] - x[sc])).sum(-1) * side_ref <= 0).any()
        chirality = geometry['chirality_fraction'] == 1 and not side_wrong
        assert bool(chirality) == stored['all_checked_chirality_pass']
        errors = {key: [] for key in ['cn', 'angle_c', 'angle_n', 'omega', 'carbonyl']}
        for i, (previous, following) in enumerate(zip(anchors, anchors[1:])):
            _, pa, pc, po = previous
            nn, na, _, _ = following
            target = 1 if phase(data['raw'], [pa, pc, nn, na])[0] >= 0 else -1
            errors['cn'].append(np.linalg.norm(x[pc] - x[nn]) - (1.341 if lock['sequence'][i + 1] == 'P' else 1.329))
            errors['angle_c'].append(cosine(x[pa], x[pc], x[nn]) + .4473)
            errors['angle_n'].append(cosine(x[pc], x[nn], x[na]) + .5203)
            errors['omega'].append(np.linalg.norm(phase(x, [pa, pc, nn, na]) - [target, 0]))
            errors['carbonyl'].append(np.linalg.norm(phase(x, [nn, pa, pc, po]) - [-1, 0]))
        for key, vector in errors.items():
            metric_error = max(metric_error, abs(float(np.abs(vector).max()) - stored['connection_max'][key]))
        squared = ((x - data['raw']) ** 2).sum(-1)
        metric_error = max(metric_error, abs(float(squared.mean()) - stored['mse']))
        cr, hr = float(np.sqrt(squared[anchors[:, 1]].mean())), float(np.sqrt(squared.mean()))
        metric_error = max(metric_error, abs(cr - stored['preservation']['ca_rms']), abs(hr - stored['preservation']['heavy_rms']))
        connected = all(np.abs(errors[key]).max() <= value + 1e-6
                        for key, value in dict(cn=.03, angle_c=.04, angle_n=.04, omega=.1, carbonyl=.1).items())
        accepted = (geometry['bond_rmse'] <= .25 and geometry['peptide_mae'] <= .15
                    and chirality and geometry['severe_pairs_per_atom'] <= .02
                    and geometry['max_penetration'] <= 2 and cr <= 1 and hr <= 2 and connected)
        assert bool(accepted) == stored['joint_pass'] and bool(connected) == stored['connection_pass']
    assert metric_error < 1e-8
    audits.append(dict(case=result['case'], verified=True, numpy_replay_max_abs=replay_error,
                       metric_max_abs=metric_error))
write_json(root / 'audit.json', dict(complete=True, report_sha256=sha256(root / 'report.json'),
    script_sha256=sha256(Path(__file__)), replay_source_sha256=sha256(Path(__file__).with_name('audit_anchored_geometry.py')),
    cases=audits, verified=sum(x['verified'] for x in audits)))
print(json.dumps(audits))
