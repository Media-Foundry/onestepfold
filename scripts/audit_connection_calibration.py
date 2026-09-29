#!/usr/bin/env python3
"""Offline archive, isolation, calibration/hold-out and result-denominator checks."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import tarfile

import numpy as np


def audit_calibration_results():
    p = argparse.ArgumentParser(); p.add_argument('root', type=Path); a = p.parse_args()
    root = a.root; m = root / 'measurement'
    digest = lambda b: hashlib.sha256(b).hexdigest()
    manifest = json.loads((m / 'source_evidence_manifest.json').read_text())
    assert digest((m / 'source_evidence.tar.gz').read_bytes()) == manifest['archive_sha256']
    with tarfile.open(m / 'source_evidence.tar.gz') as archive:
        files = {x.name: archive.extractfile(x).read() for x in archive if x.isfile()}
    assert set(files) == set(manifest['files'])
    for name, data in files.items():
        assert digest(data) == manifest['files'][name]['sha256']
        assert len(data) == manifest['files'][name]['bytes']
    read = lambda n: json.loads(files[n])
    panel = read('extension/selection.json'); old = read('source/selection.json')
    pool = read('source/pool.json'); extra = read('extension/pool.json'); peers = extra + old
    assert len(panel) == 64 and len(old) == 43
    assert len({r['group_id'] for r in panel}) == len({r['pdb_id'] for r in panel}) == 64
    accessions = [acc for r in panel for acc in r['accessions']]
    assert len(accessions) == len(set(accessions))
    for stratum in [0, 1]:
        for role in ['calibration', 'held_out']:
            assert sum(r['stratum'] == stratum and r['role'] == role for r in panel) == 16
    assert read('extension/selection_lock.json')['selection_sha256'] == digest(files['extension/selection.json'])
    assert (root / 'extension/selection.json').read_bytes() == files['extension/selection.json']
    chosen = {r['group_id'] for r in panel}; checked_hsps = 0
    for path, query, subject, reference in [
        ('source/references_hsps.tsv', pool, None, True),
        ('source/pool_hsps.tsv', pool, pool, False),
        ('extension/references.tsv', extra, None, True),
        ('extension/pairs.tsv', peers, peers, False)]:
        for line in files[path].decode().splitlines():
            q, s, ql, sl, e, qa, sa = line.split('\t'); checked_hsps += 1
            assert len(qa) == len(sa)
            pairs = [(x, y) for x, y in zip(qa, sa) if x != '-' and y != '-']
            n = len(pairs)
            excluded = n >= 50 and (float(e) <= 1e-5 or
                (float(e) <= .001 and sum(x == y for x, y in pairs) / n >= .30 and n / min(int(ql), int(sl)) >= .70))
            if not excluded:
                continue
            g = query[int(q[1:])]['group_id']
            if reference:
                assert g not in chosen
            else:
                h = subject[int(s[1:])]['group_id']
                assert g == h or not (g in chosen and h in chosen)
    for r in panel:
        for name, key in [('gt.npz', 'gt_sha256'), ('gt.json', 'metadata_sha256')]:
            assert digest(files['selected_gt/' + r['group_id'] + '/' + name]) == r[key]
    result = json.loads((m / 'report.json').read_text()); fitted = json.loads((m / 'fitted_windows.json').read_text())
    assert result['fitted_windows_sha256'] == digest((m / 'fitted_windows.json').read_bytes())
    assert result['measurement_lock_sha256'] == digest((m / 'measurement_lock.json').read_bytes())
    assert result['selected'] == result['measured'] == 64 and not result['failures']
    edges = list(csv.DictReader(io.StringIO((m / 'edges.csv').read_text())))
    roles = {r['group_id']: r['role'] for r in panel}
    assert all(r['role'] == roles[r['group_id']] for r in edges)
    summary = {}
    tolerances = dict(cn=.03, angle_c=.04, angle_n=.04, omega=.1, carbonyl=.1)
    for role in ['calibration', 'held_out']:
        rows = [r for r in edges if r['role'] == role]
        summary[role] = dict(proteins=len({r['group_id'] for r in rows}), edges=len(rows),
            active=sum(any(abs(float(r[k + '_residual'])) > .5 * t for k, t in tolerances.items()) for r in rows),
            rejected=sum(any(abs(float(r[k + '_residual'])) > t + 1e-6 for k, t in tolerances.items()) for r in rows),
            cis=sum(r['branch'] == 'cis' for r in rows))
        assert summary[role]['proteins'] == 32
        for key in ['edges', 'active', 'rejected', 'cis']:
            other = 'cis_edges' if key == 'cis' else key
            assert summary[role][key] == sum(r[other] for r in result['structures'] if r['role'] == role)
    checks = 0
    for category, info in fitted['windows'].items():
        assert info['supported']
        train = [r for r in edges if r['role'] == 'calibration' and r['branch'] == 'trans' and r['next_class'] == category]
        held = [r for r in edges if r['role'] == 'held_out' and r['branch'] == 'trans' and r['next_class'] == category]
        assert len(train) == info['edges']
        for term, windows in info['windows'].items():
            values = np.abs([float(r[term + '_residual']) for r in train])
            for label, pair in windows.items():
                q = int(label[1:]) / 100
                assert abs(float(np.quantile(values, q)) - pair['pooled']) < 1e-14
                for weighting, bound in pair.items():
                    expected = sum(abs(float(r[term + '_residual'])) <= bound for r in held) / len(held)
                    observed = result['held_out_coverage'][category][term][label][weighting]
                    assert abs(expected - observed['pooled']) < 1e-14
                    assert len(held) == observed['edges']
                    checks += 1
    audit = dict(passed=True, archive_files=len(files), panel_sources=len(panel), hsps_checked=checked_hsps,
        empirical_window_coverage_checks=checks, summary=summary, source_archive_sha256=manifest['archive_sha256'],
        report_sha256=digest((m / 'report.json').read_bytes()),
        scope='archive/isolation/CSV denominators/calibration-only pooled quantiles/held-out coverage; not a new geometry gate')
    (root / 'audit.json').write_text(json.dumps(audit, indent=2) + '\n')
    print(json.dumps(audit))


if __name__ == '__main__':
    audit_calibration_results()
