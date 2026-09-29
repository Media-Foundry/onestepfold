#!/usr/bin/env python3
"""Read-only peptide-span necessary conditions on frozen C4 coordinates."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import tarfile

import numpy as np

from fastglycan.ca_span_feasibility import ca_span_bounds, peptide_span_squared, ca_motion_lower_bound
from fastglycan.connection_audit import measure_connections, TOLERANCES

MARGIN = 1e-6


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def open_verified_archive(root):
    manifest = json.loads((root/'artifact_manifest.json').read_text())
    assert digest(root/'artifacts.tar.gz') == manifest['archive_sha256']
    archive = tarfile.open(root/'artifacts.tar.gz')
    assert len(archive.getmembers()) == len(manifest['files'])
    for name, expected in manifest['files'].items():
        assert hashlib.sha256(archive.extractfile(name).read()).hexdigest() == expected
    return archive


def audit_ca_span_feasibility(c4_root, fit_root, calibration_path, output):
    assert not output.exists()
    output.mkdir(parents=True)
    code_root = Path(__file__).resolve().parents[1]
    inputs = [Path(__file__), code_root/'src/fastglycan/ca_span_feasibility.py',
        code_root/'src/fastglycan/connection_audit.py', code_root/'docs/mini_ca_span_feasibility_v1.md',
        calibration_path] + [root/name for root in [c4_root, fit_root]
        for name in ['artifact_manifest.json', 'artifacts.tar.gz', 'lock.json', 'report.json', 'audit.json']]
    lock = dict(hashes={str(p.resolve()): digest(p) for p in inputs}, margin_angstrom=MARGIN,
        scope='fixed-CA necessary conditions only; no new output, solver or gate')
    (output/'input_lock.json').write_text(json.dumps(lock, indent=2)+'\n')
    c4_lock = json.loads((c4_root/'lock.json').read_text())
    assert digest(calibration_path) == c4_lock['hashes'][c4_lock['calibration']]
    calibration = json.loads(calibration_path.read_text())['windows']
    for root in [c4_root, fit_root]:
        audit = json.loads((root/'audit.json').read_text())
        assert audit['verified'] == 28 and audit['paired'] == 14
        assert audit['report_sha256'] == digest(root/'report.json')
    old = open_verified_archive(c4_root); new = open_verified_archive(fit_root)
    selection = json.loads(old.extractfile('source/selection.json').read())
    summaries, edges, skipped = [], [], []
    formula_error = length_error = 0.
    cert_db = np.inf; cert_du = cert_dv = -np.inf
    for slot, item in enumerate(selection):
        reference_gt = None
        for noise_index, seed in enumerate([12345, 54321]):
            index = slot*4+noise_index*2+1
            report = json.loads(old.extractfile(f'cases/{index:02d}/report.json').read())
            if not report['success']:
                assert report['not_run']
                skipped.append(dict(source_slot=slot, pdb_id=item['pdb_id'], seed=seed,
                    reason=report['source_failure']))
                continue
            d = dict(np.load(io.BytesIO(old.extractfile(f'cases/{index:02d}/coordinates.npz').read())))
            f = dict(np.load(io.BytesIO(new.extractfile(f'cases/{index:02d}/coordinates.npz').read())))
            for name in ['raw', 'local', 'target', 'atom_names', 'residue_ids']:
                assert np.array_equal(d[name], f[name])
            if reference_gt is None: reference_gt = d['target']
            else: assert np.array_equal(reference_gt, d['target'])
            sequence = item['sequence']; names, residues = d['atom_names'], d['residue_ids']
            anchors = np.array([[int(np.flatnonzero((residues == j)&(names == name))[0])
                for name in ['N', 'CA', 'C', 'O']] for j in range(1, len(sequence)+1)])
            ca, carbon, nitrogen, next_ca = anchors[:-1, 1], anchors[:-1, 2], anchors[1:, 0], anchors[1:, 1]
            a = np.linalg.norm(d['local'][ca]-d['local'][carbon], axis=-1)
            c = np.linalg.norm(d['local'][nitrogen]-d['local'][next_ca], axis=-1)
            target_b = np.array([1.341 if aa == 'P' else 1.329 for aa in sequence[1:]])
            raw_sign = measure_connections(d['raw'], anchors, sequence)['nearest_omega_sign']
            gt_sign = measure_connections(d['target'], anchors, sequence)['nearest_omega_sign']
            assert np.flatnonzero(raw_sign != gt_sign).tolist() == report['raw_branch_mismatches']
            bounds = {}
            for profile in ['old_acceptance', 'calibrated_zero_penalty']:
                bounds[profile] = {}
                for sign in [-1, 1]:
                    if profile == 'old_acceptance':
                        widths = {k: v+1e-6 for k, v in TOLERANCES.items()}
                    elif sign > 0:
                        widths = {k: .5*v for k, v in TOLERANCES.items()}
                    else:
                        widths = {k: np.array([calibration['Pro' if aa == 'P' else 'other']['windows'][k]['q95']['pooled']
                            for aa in sequence[1:]]) for k in TOLERANCES}
                    box = ca_span_bounds(a, c, target_b, widths, sign)
                    cert_db = min(cert_db, float(box['db_lower'].min()))
                    cert_du = max(cert_du, float(box['du_upper'].max()))
                    cert_dv = max(cert_dv, float(box['dv_upper'].max()))
                    bounds[profile][sign] = box
            stages = dict(raw=d['raw'], zero_final=d['final'], fitted_start=f['start'], fitted_final=f['final'])
            if noise_index == 0: stages['experimental_gt'] = d['target']
            for stage, x in stages.items():
                measured = measure_connections(x, anchors, sequence)
                actual_a = np.linalg.norm(x[ca]-x[carbon], axis=-1)
                actual_c = np.linalg.norm(x[nitrogen]-x[next_ca], axis=-1)
                span = np.linalg.norm(x[next_ca]-x[ca], axis=-1)
                reconstructed = np.sqrt(peptide_span_squared(actual_a, measured['cn'], actual_c,
                    measured['angle_c_cos'], measured['angle_n_cos'], np.cos(np.radians(measured['omega_degrees']))))
                formula_error = max(formula_error, float(np.max(np.abs(reconstructed-span))))
                if stage not in ['raw', 'experimental_gt']:
                    length_error = max(length_error, float(np.max(np.abs(actual_a-a))), float(np.max(np.abs(actual_c-c))))
                selected = gt_sign if stage == 'experimental_gt' else raw_sign
                for profile, branches in bounds.items():
                    lower = np.where(selected > 0, branches[1]['lower'], branches[-1]['lower'])
                    upper = np.where(selected > 0, branches[1]['upper'], branches[-1]['upper'])
                    other_lower = np.where(selected > 0, branches[-1]['lower'], branches[1]['lower'])
                    other_upper = np.where(selected > 0, branches[-1]['upper'], branches[1]['upper'])
                    gap = np.maximum.reduce([lower-span, span-upper, np.zeros_like(span)])
                    other_gap = np.maximum.reduce([other_lower-span, span-other_upper, np.zeros_like(span)])
                    union_gap = np.minimum(gap, other_gap)
                    outside = gap > MARGIN; neither = union_gap > MARGIN
                    summary = dict(pdb_id=item['pdb_id'], group_id=item['group_id'], source_slot=slot,
                        seed=seed, stage=stage, profile=profile, length=len(sequence), edges=len(span),
                        selected_branch_violations=int(outside.sum()), either_branch_violations=int(neither.sum()),
                        alternative_only_span_supported=int((outside & ~neither).sum()),
                        selected_gap_max=float(gap.max()), either_gap_max=float(union_gap.max()),
                        selected_ca_rms_lower_bound=ca_motion_lower_bound(np.maximum(gap-MARGIN, 0)),
                        either_ca_rms_lower_bound=ca_motion_lower_bound(np.maximum(union_gap-MARGIN, 0)))
                    summaries.append(summary)
                    for j in range(len(span)):
                        edges.append(dict(pdb_id=item['pdb_id'], seed=seed, stage=stage, profile=profile,
                            left_residue=j+1, right_residue=j+2, residue_pair=sequence[j:j+2],
                            distance=float(span[j]), selected_branch='cis' if selected[j] > 0 else 'trans',
                            gt_branch='cis' if gt_sign[j] > 0 else 'trans',
                            lower=float(lower[j]), upper=float(upper[j]),
                            other_lower=float(other_lower[j]), other_upper=float(other_upper[j]),
                            selected_gap=float(gap[j]), either_gap=float(union_gap[j]),
                            selected_outside=bool(outside[j]), either_outside=bool(neither[j])))
    old.close(); new.close()
    assert formula_error < 1e-10 and length_error < 1e-9
    assert len(skipped) == 2 and len(summaries) == 126
    aggregate = []
    for stage in ['raw', 'zero_final', 'fitted_start', 'fitted_final', 'experimental_gt']:
        for profile in ['old_acceptance', 'calibrated_zero_penalty']:
            rows = [r for r in summaries if r['stage'] == stage and r['profile'] == profile]
            aggregate.append(dict(stage=stage, profile=profile, instances=len(rows),
                proteins=len({r['pdb_id'] for r in rows}), edges=sum(r['edges'] for r in rows),
                selected_branch_violations=sum(r['selected_branch_violations'] for r in rows),
                either_branch_violations=sum(r['either_branch_violations'] for r in rows),
                instances_with_selected_violations=sum(r['selected_branch_violations'] > 0 for r in rows),
                instances_with_either_violations=sum(r['either_branch_violations'] > 0 for r in rows),
                alternative_only_span_supported=sum(r['alternative_only_span_supported'] for r in rows),
                max_selected_gap=max(r['selected_gap_max'] for r in rows),
                max_either_gap=max(r['either_gap_max'] for r in rows),
                max_selected_rms_lower_bound=max(r['selected_ca_rms_lower_bound'] for r in rows),
                max_either_rms_lower_bound=max(r['either_ca_rms_lower_bound'] for r in rows)))
    for name, rows in [('instances', summaries), ('edges', edges)]:
        with (output/f'{name}.csv').open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    result = dict(complete=True, input_lock_sha256=digest(output/'input_lock.json'), aggregate=aggregate,
        instances=summaries, skipped=skipped, formula_max_abs=formula_error,
        invariant_bond_max_abs=length_error, monotonicity=dict(min_db=cert_db, max_du=cert_du, max_dv=cert_dv),
        output_sha256={name:digest(output/name) for name in ['instances.csv', 'edges.csv']},
        limits='necessary per-edge bounds only; calibration zero-penalty boxes are not acceptance gates; GT unique7, model14')
    (output/'report.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(formula_error=formula_error, invariant_error=length_error, aggregate=aggregate), indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for name in ['c4-root', 'fit-root', 'calibration', 'output']: p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    audit_ca_span_feasibility(a.c4_root, a.fit_root, a.calibration, a.output)
