#!/usr/bin/env python3
"""Cartesian corner/interior cross-check, independent of the span formula code."""
import argparse
import csv
import hashlib
import io
import itertools
import json
from pathlib import Path
import tarfile

import numpy as np


def verify_ca_span_corners(root, c4_root, calibration_path):
    lock = json.loads((root/'input_lock.json').read_text())
    for name, digest in lock['hashes'].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest
    rows = list(csv.DictReader((root/'edges.csv').open()))
    report = json.loads((root/'report.json').read_text())
    assert hashlib.sha256((root/'edges.csv').read_bytes()).hexdigest() == report['output_sha256']['edges.csv']
    calibration = json.loads(calibration_path.read_text())['windows']
    max_error = 0.; boxes = samples = 0
    rng = np.random.default_rng(9302026)
    interior = rng.uniform(0, 1, (64, 4))
    corners = np.array(list(itertools.product([0., 1.], repeat=4)))
    with tarfile.open(c4_root/'artifacts.tar.gz') as archive:
        selection = json.loads(archive.extractfile('source/selection.json').read())
        for slot, item in enumerate(selection):
            for k, seed in enumerate([12345, 54321]):
                index = slot*4+2*k+1
                meta = json.loads(archive.extractfile(f'cases/{index:02d}/report.json').read())
                if not meta['success']: continue
                data = dict(np.load(io.BytesIO(archive.extractfile(f'cases/{index:02d}/coordinates.npz').read())))
                lookup = {(int(r), str(n)): i for i, (r, n) in enumerate(zip(data['residue_ids'], data['atom_names']))}
                sequence = item['sequence']; x = data['local']
                a = np.array([np.linalg.norm(x[lookup[j, 'CA']]-x[lookup[j, 'C']]) for j in range(1, len(sequence))])
                c = np.array([np.linalg.norm(x[lookup[j, 'N']]-x[lookup[j, 'CA']]) for j in range(2, len(sequence)+1)])
                b0 = np.array([1.341 if aa == 'P' else 1.329 for aa in sequence[1:]])
                for profile in ['old_acceptance', 'calibrated_zero_penalty']:
                    expected = sorted([r for r in rows if r['pdb_id'] == item['pdb_id'] and int(r['seed']) == seed
                        and r['stage'] == 'raw' and r['profile'] == profile], key=lambda r: int(r['left_residue']))
                    assert len(expected) == len(a)
                    for sign in [-1, 1]:
                        widths = np.tile([.03, .04, .04, .1], (len(a), 1))
                        if profile == 'old_acceptance': widths += 1e-6
                        elif sign > 0: widths *= .5
                        else:
                            widths = np.array([[calibration['Pro' if aa == 'P' else 'other']['windows'][term]['q95']['pooled']
                                for term in ['cn', 'angle_c', 'angle_n', 'omega']] for aa in sequence[1:]])
                        q0 = np.ones(len(a))*(1 if sign > 0 else -1)
                        lo = np.stack([b0-widths[:, 0], -.4473-widths[:, 1], -.5203-widths[:, 2],
                            q0-widths[:, 3]**2/2 if sign > 0 else q0], axis=1)
                        hi = np.stack([b0+widths[:, 0], -.4473+widths[:, 1], -.5203+widths[:, 2],
                            q0 if sign > 0 else q0+widths[:, 3]**2/2], axis=1)
                        coordinates = lo[:, None, :]+np.concatenate([corners, interior])[None]*(hi-lo)[:, None, :]
                        b, u, v, q = np.moveaxis(coordinates, -1, 0)
                        first = np.stack([a[:, None]*u, a[:, None]*np.sqrt(1-u*u), np.zeros_like(u)], axis=-1)
                        last = np.stack([b-c[:, None]*v, c[:, None]*np.sqrt(1-v*v)*q,
                            c[:, None]*np.sqrt(1-v*v)*np.sqrt(1-q*q)], axis=-1)
                        distance = np.linalg.norm(last-first, axis=-1)
                        lower = np.array([float(r['lower'] if r['selected_branch'] == ('cis' if sign > 0 else 'trans') else r['other_lower']) for r in expected])
                        upper = np.array([float(r['upper'] if r['selected_branch'] == ('cis' if sign > 0 else 'trans') else r['other_upper']) for r in expected])
                        error = max(np.max(np.abs(distance[:, :16].min(-1)-lower)), np.max(np.abs(distance[:, :16].max(-1)-upper)))
                        max_error = max(max_error, float(error))
                        assert (distance >= lower[:, None]-1e-12).all() and (distance <= upper[:, None]+1e-12).all()
                        boxes += len(a); samples += distance.size
    assert max_error < 1e-12
    result = dict(complete=True, boxes=boxes, corners_per_box=16, random_interiors_per_box=64,
        cartesian_distances_checked=samples, corner_max_abs=max_error,
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        scope='Cartesian corner and interior numerical check; not whole-chain feasibility or formal interval rounding')
    (root/'cartesian_validation.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for name in ['root', 'c4-root', 'calibration']: p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args(); verify_ca_span_corners(a.root, a.c4_root, a.calibration)
