#!/usr/bin/env python3
"""Measure locked GT sources; fit windows before evaluating held-out coverage."""
import argparse
import csv
import json
from pathlib import Path

import gemmi
import numpy as np

from audit_experimental_connections import raw_cif_check
from fastglycan.connection_audit import measure_connections, summarize_residuals, TOLERANCES
from fastglycan.connection_calibration import fit_connection_windows, coverage_by_protein
from fastglycan.paired_teacher_protocol import sha256, write_json
from onestepfold.data.gt_materializer import ATOM37_INDEX


def measure_calibration_panel():
    p = argparse.ArgumentParser()
    for key in ['base', 'root', 'selection']:
        p.add_argument('--' + key, type=Path, required=True)
    a = p.parse_args(); root = a.root
    assert not (root / 'measurement_lock.json').exists()
    panel = json.loads(a.selection.read_text()); assert len(panel) == 64
    assert sum(r['role'] == 'calibration' for r in panel) == 32
    assert sum(r['stratum'] == 0 for r in panel) == 32
    lock = json.loads(a.selection.with_name('selection_lock.json').read_text())
    assert lock['complete'] and sha256(a.selection) == lock['selection_sha256']
    hashes = {str(a.selection): sha256(a.selection), str(a.selection.with_name('selection_lock.json')): sha256(a.selection.with_name('selection_lock.json'))}
    for file in (root / 'code').rglob('*'):
        if file.is_file() and file.suffix in ['.py', '.md']:
            hashes[str(file)] = sha256(file)
    for r in panel:
        f = Path(r['source'])
        for n, key in [('gt.npz', 'gt_sha256'), ('gt.json', 'metadata_sha256')]:
            assert sha256(f / n) == r[key]; hashes[str(f / n)] = r[key]
    write_json(root / 'measurement_lock.json', dict(hashes=hashes, no_solver=True, protocol='mini_connection_calibration_v1'))
    all_edges, structures, failures = [], [], []
    windows = None
    for role in ['calibration', 'held_out']:
        for r in (x for x in panel if x['role'] == role):
            try:
                f = Path(r['source']); meta = json.loads((f / 'gt.json').read_text()); seq = r['sequence']
                assert meta['chains'][0]['sequence'] == seq and len(meta['chains']) == 1
                with np.load(f / 'gt.npz') as z:
                    ix = [ATOM37_INDEX[n] for n in ['N', 'CA', 'C', 'O']]
                    assert z['residue_mask'].all() and z['atom37_mask'][:, ix].all()
                    x = z['atom37_positions'][:, ix].reshape(-1, 3).astype(float)
                ids = np.arange(len(x)).reshape(-1, 4)
                inv = dict(residue_id=np.repeat(np.arange(1, len(seq) + 1), 4),
                    atom_name=np.tile(['N', 'CA', 'C', 'O'], len(seq)), element=np.tile(['N', 'C', 'C', 'O'], len(seq)))
                cif = a.base / 'Dataset/raw/pdb_mmcif' / r['pdb_id'][1:3] / (r['pdb_id'] + '.cif.gz')
                assert sha256(cif) == meta['provenance']['source_mmcif_sha256']
                mapping = raw_cif_check(cif, meta, inv, x)
                tab = gemmi.cif.read(str(cif)).sole_block().get_mmcif_category('_atom_site.')
                clean = lambda v: '' if v in [None, False, '.', '?'] else str(v)
                atom_info = {}
                chain = meta['chains'][0]
                for i, label in enumerate(tab['label_asym_id']):
                    if label != chain['source_label_asym_id'] or str(tab['pdbx_PDB_model_num'][i]) != '1':
                        continue
                    key = (clean(tab['label_seq_id'][i]), tab['label_atom_id'][i], clean(tab['label_alt_id'][i]))
                    atom_info[key] = (float(tab['occupancy'][i]), float(tab['B_iso_or_equiv'][i]), bool(key[-1]))
                qualities = []
                for residue in chain['residues']:
                    local = []
                    for name in ['N', 'CA', 'C', 'O']:
                        key = (str(residue['label_seq_id']), name, clean(residue['selected_altloc']))
                        if key not in atom_info:
                            key = (key[0], name, '')
                        local.append(atom_info[key])
                    qualities.append(local)
                quality = np.asarray(qualities)
                m = measure_connections(x, ids, seq)
                phase_error = 0.
                for index, term in [(np.stack([ids[:-1, 1], ids[:-1, 2], ids[1:, 0], ids[1:, 1]], 1), 'omega'),
                                    (np.stack([ids[1:, 0], ids[:-1, 1], ids[:-1, 2], ids[:-1, 3]], 1), 'carbonyl')]:
                    phase = np.array([gemmi.calculate_dihedral(*[gemmi.Position(*v) for v in x[q]]) for q in index])
                    phase_error = max(phase_error, float(np.max(np.abs(np.exp(1j * phase) - np.exp(1j * np.radians(m[term + '_degrees']))))))
                assert phase_error < 1e-8
                edges = []
                for i in range(len(seq) - 1):
                    q = quality[i:i+2]
                    edges.append(dict(group_id=r['group_id'], pdb_id=r['pdb_id'], role=role, stratum=r['stratum'],
                        left_label=i + 1, right_label=i + 2, next_class='Pro' if seq[i + 1] == 'P' else 'other',
                        branch='cis' if m['nearest_omega_sign'][i] > 0 else 'trans',
                        min_occupancy=float(q[:, :, 0].min()), max_bfactor=float(q[:, :, 1].max()),
                        alternate_backbone=bool(q[:, :, 2].any()),
                        omega_degrees=float(m['omega_degrees'][i]), cn=float(m['cn'][i]),
                        **{k + '_residual': float(v[i]) for k, v in m['residuals'].items()}))
                stats = summarize_residuals(m['residuals'])
                active = np.logical_or.reduce([np.abs(v) > .5 * TOLERANCES[k] for k, v in m['residuals'].items()])
                reject = np.logical_or.reduce([np.abs(v) > TOLERANCES[k] + 1e-6 for k, v in m['residuals'].items()])
                structures.append(dict(group_id=r['group_id'], pdb_id=r['pdb_id'], role=role, stratum=r['stratum'],
                    edges=len(edges), active=int(active.sum()), rejected=int(reject.sum()), stats=stats,
                    mapping=mapping, phase_error=phase_error, cis_edges=sum(e['branch'] == 'cis' for e in edges)))
                all_edges.extend(edges)
            except Exception as exc:
                failures.append(dict(group_id=r['group_id'], pdb_id=r['pdb_id'], role=role, error=repr(exc)))
        if role == 'calibration':
            windows = fit_connection_windows(all_edges)
            write_json(root / 'fitted_windows.json', dict(windows=windows, calibration_proteins=len(structures),
                failures=failures.copy(), selection_sha256=sha256(a.selection), not_acceptance_thresholds=True))
    coverages = {}
    for category, info in windows.items():
        if not info['supported']:
            continue
        held = [r for r in all_edges if r['role'] == 'held_out' and r['branch'] == 'trans' and r['next_class'] == category]
        coverages[category] = {}
        for term, estimates in info['windows'].items():
            coverages[category][term] = {}
            for quantile, values in estimates.items():
                coverages[category][term][quantile] = {weight: coverage_by_protein(held, term, value) for weight, value in values.items()}
                coverages[category][term][quantile]['full_occupancy_no_altloc'] = coverage_by_protein(
                    [r for r in held if r['min_occupancy'] >= .999 and not r['alternate_backbone']], term, values['pooled'])
    write_json(root / 'report.json', dict(complete=True, selected=len(panel), measured=len(structures), failures=failures,
        structures=structures, held_out_coverage=coverages, fitted_windows_sha256=sha256(root / 'fitted_windows.json'),
        measurement_lock_sha256=sha256(root / 'measurement_lock.json'), cis_edges=[r for r in all_edges if r['branch'] == 'cis'],
        scope='descriptive GT calibration; no changed gates, no objective intervention, no folding validation'))
    with (root / 'edges.csv').open('w', newline='') as out:
        writer = csv.DictWriter(out, fieldnames=list(all_edges[0]), lineterminator='\n')
        writer.writeheader(); writer.writerows(all_edges)
    print(json.dumps(dict(measured=len(structures), failures=len(failures), edges=len(all_edges))), flush=True)


if __name__ == '__main__':
    measure_calibration_panel()
