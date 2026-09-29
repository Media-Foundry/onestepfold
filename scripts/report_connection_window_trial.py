#!/usr/bin/env python3
"""Paired development outcomes, retaining original gates and source failures."""
import argparse
import csv
import json
from pathlib import Path

import numpy as np

from fastglycan.paired_teacher_protocol import sha256, write_json


def report_connection_window_trial(root):
    report = json.loads((root / 'report.json').read_text()); audit = json.loads((root / 'audit.json').read_text())
    assert audit['complete'] and audit['report_sha256'] == sha256(root / 'report.json')
    rows = {r['index']: r for r in report['rows']}
    arms = {}
    for arm in ['original', 'calibrated']:
        available = [r for r in rows.values() if r['success'] and r['arm'] == arm]
        stages = {}
        for stage in ['raw', 'local', 'start', 'final']:
            records = [r['metrics'][stage] for r in available]
            stages[stage] = dict(all_atom_lddt=float(np.mean([r['all_atom_lddt'] for r in records])),
                ca_lddt=float(np.mean([r['ca_lddt'] for r in records])),
                **{k: sum(r[k] for r in records) for k in ['joint_pass', 'connection_pass',
                    'all_checked_chirality_pass', 'zero_severe_chirality_budget']},
                zero_severe=sum(r['geometry']['severe_pairs'] == 0 for r in records),
                severe_pairs_total=sum(r['geometry']['severe_pairs'] for r in records),
                max_penetration=max(r['geometry']['max_penetration'] for r in records),
                preservation_pass=sum(r['preservation']['accepted'] for r in records),
                max_atom_displacement=max(r['preservation']['max_displacement'] for r in records),
                ca_rms_mean=float(np.mean([r['preservation']['ca_rms'] for r in records])),
                heavy_rms_mean=float(np.mean([r['preservation']['heavy_rms'] for r in records])),
                branch_mismatch_instances=sum(len(r['branch_mismatches']) for r in records),
                absolute_failure_counts={name: sum(name in r['absolute_failures'] for r in records)
                    for name in sorted({name for r in records for name in r['absolute_failures']})})
        arms[arm] = dict(planned=16, available=len(available), stages=stages,
            median_seconds=float(np.median([r['solver_seconds'] for r in available])),
            mean_seconds=float(np.mean([r['solver_seconds'] for r in available])),
            iterations=[sum(h['iterations'] for h in r['history']) for r in available],
            closures=[sum(h['calls'] for h in r['history']) for r in available],
            max_peak_rss_kib=max(r['peak_rss_kib'] for r in available))
    pairs = []
    for i in range(0, 32, 2):
        old, new = rows[i], rows[i+1]
        pair = dict(source_slot=i//4, seed=[12345, 54321][(i//2)%2], paired=old['success'] and new['success'])
        if pair['paired']:
            x, y = old['metrics']['final'], new['metrics']['final']; raw = old['metrics']['raw']
            pair.update(group_id=old['group_id'], pdb_id=old['pdb_id'], raw_aa=raw['all_atom_lddt'], raw_ca=raw['ca_lddt'],
                original_aa=x['all_atom_lddt'], calibrated_aa=y['all_atom_lddt'],
                original_ca=x['ca_lddt'], calibrated_ca=y['ca_lddt'],
                delta_aa=y['all_atom_lddt']-x['all_atom_lddt'], delta_ca=y['ca_lddt']-x['ca_lddt'],
                calibrated_vs_raw_aa=y['all_atom_lddt']-raw['all_atom_lddt'],
                original_joint=x['joint_pass'], calibrated_joint=y['joint_pass'],
                original_safety=x['zero_severe_chirality_budget'], calibrated_safety=y['zero_severe_chirality_budget'],
                original_max_penetration=x['geometry']['max_penetration'], calibrated_max_penetration=y['geometry']['max_penetration'])
        pairs.append(pair)
    proteins = []
    for slot in range(8):
        entries = [r for r in pairs if r['source_slot'] == slot]
        protein = dict(source_slot=slot, complete=all(r['paired'] for r in entries))
        if protein['complete']:
            protein.update(pdb_id=entries[0]['pdb_id'], group_id=entries[0]['group_id'],
                **{k: float(np.mean([r[k] for r in entries])) for k in ['raw_aa', 'raw_ca', 'original_aa', 'calibrated_aa',
                    'original_ca', 'calibrated_ca', 'delta_aa', 'delta_ca', 'calibrated_vs_raw_aa']},
                original_joint=sum(r['original_joint'] for r in entries), calibrated_joint=sum(r['calibrated_joint'] for r in entries),
                original_safety=sum(r['original_safety'] for r in entries), calibrated_safety=sum(r['calibrated_safety'] for r in entries))
        proteins.append(protein)
    good = [p for p in proteins if p['complete']]
    da = float(np.mean([p['delta_aa'] for p in good])); dc = float(np.mean([p['delta_ca'] for p in good]))
    complete = audit['verified'] == 28 and audit['paired'] == 14 and len(good) == 7
    candidate = complete and da > 0 and dc > 0 and (
        arms['calibrated']['stages']['final']['zero_severe_chirality_budget'] >=
        arms['original']['stages']['final']['zero_severe_chirality_budget'])
    summary = dict(report_sha256=sha256(root / 'report.json'), audit_sha256=sha256(root / 'audit.json'),
        arms=arms, pairs=pairs, proteins=proteins, complete_supported_pairs=complete,
        paired_protein_mean_delta_aa=da, paired_protein_mean_delta_ca=dc,
        bounded_confirmation_candidate=bool(candidate), deployment_acceptance=False,
        original_baseline_replays=sum(r.get('historical_baseline_bitwise', False) for r in rows.values()),
        scope='seven supported development proteins; eight-source denominator retained; unchanged old acceptance')
    write_json(root / 'summary.json', summary)
    for name, records in [('paired_proteins', proteins), ('paired_predictions', pairs)]:
        with (root / (name + '.csv')).open('w', newline='') as out:
            columns = list(dict.fromkeys(k for r in records for k in r))
            writer = csv.DictWriter(out, fieldnames=columns, lineterminator='\n'); writer.writeheader(); writer.writerows(records)
    print(json.dumps(dict(complete=complete, delta_aa=da, delta_ca=dc, bounded_candidate=bool(candidate))))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--root', type=Path, required=True)
    report_connection_window_trial(p.parse_args().root)
