#!/usr/bin/env python3
"""Posthoc explanation only: GT spans using model versus observed bond lengths."""
import argparse
import io
import json
from pathlib import Path

import numpy as np

from audit_ca_span_feasibility import digest, open_verified_archive, MARGIN
from fastglycan.ca_span_feasibility import ca_span_bounds
from fastglycan.connection_audit import TOLERANCES, measure_connections


def audit_reference_bond_counterfactual(c4_root, runtime_path, output):
    assert not output.exists()
    runtime = json.loads(runtime_path.read_text())
    runtime_rows = {r['group_id']: r for r in runtime['records']}
    archive = open_verified_archive(c4_root)
    selection = json.loads(archive.extractfile('source/selection.json').read())
    records = []
    for slot, row in enumerate(selection):
        prefix = f'cases/{slot*4+1:02d}/'
        status = json.loads(archive.extractfile(prefix+'report.json').read())
        if not status['success']:
            continue
        data = dict(np.load(io.BytesIO(archive.extractfile(prefix+'coordinates.npz').read())))
        names, residues = data['atom_names'], data['residue_ids']
        sequence = row['sequence']
        anchors = np.array([[np.flatnonzero((residues == i)&(names == n))[0]
                            for n in ['N', 'CA', 'C', 'O']] for i in range(1, len(sequence)+1)])
        gt = data['target']
        signs = measure_connections(gt, anchors, sequence)['nearest_omega_sign']
        span = np.linalg.norm(gt[anchors[1:, 1]]-gt[anchors[:-1, 1]], axis=-1)
        b0 = np.array([1.341 if aa == 'P' else 1.329 for aa in sequence[1:]])
        result = dict(pdb_id=row['pdb_id'], group_id=row['group_id'], edges=len(span), variants={})
        runtime_bonds = runtime_rows[row['group_id']]['bonds']
        native = {(b['residue'], tuple(b['atoms'])): b['native_length'] for b in runtime_bonds}
        for variant, x in [('model_reference', data['local']), ('observed_gt_lengths', gt)]:
            a = np.linalg.norm(x[anchors[:-1, 1]]-x[anchors[:-1, 2]], axis=-1)
            c = np.linalg.norm(x[anchors[1:, 0]]-x[anchors[1:, 1]], axis=-1)
            if variant == 'model_reference':
                error = max(max(abs(a[i]-native[(i+1, ('CA', 'C'))]) for i in range(len(a))),
                            max(abs(c[i]-native[(i+2, ('N', 'CA'))]) for i in range(len(c))))
                assert error < 1e-10
                result['native_to_local_length_max_abs'] = error
            box = ca_span_bounds(a, c, b0, {k:v+1e-6 for k,v in TOLERANCES.items()}, signs)
            gaps = np.maximum.reduce([box['lower']-span, span-box['upper'], np.zeros_like(span)])
            result['variants'][variant] = dict(violations=int((gaps>MARGIN).sum()),
                maximum_gap=float(gaps.max()), mean_ca_c=float(a.mean()), mean_n_ca=float(c.mean()),
                failing_left_residues=(np.flatnonzero(gaps>MARGIN)+1).tolist())
        records.append(result)
    assert len(records) == 7
    archive.close()
    result = dict(complete=True, analysis='posthoc; only intra-residue lengths substituted; GT branch and old windows fixed',
        not_a_solver=True, proteins=7, edges=sum(r['edges'] for r in records), records=records,
        total_violations={v:sum(r['variants'][v]['violations'] for r in records)
                          for v in ['model_reference', 'observed_gt_lengths']},
        hashes={str(p):digest(p) for p in [Path(__file__), runtime_path,
                    c4_root/'artifacts.tar.gz', c4_root/'artifact_manifest.json']},
        limits='GT-specific lengths are diagnostic only; no deployment inputs, new output, acceptance change or independent validation')
    output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['proteins', 'edges', 'total_violations']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ['c4-root', 'runtime', 'output']:
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    audit_reference_bond_counterfactual(args.c4_root, args.runtime, args.output)
