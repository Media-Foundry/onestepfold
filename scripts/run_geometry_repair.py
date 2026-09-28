#!/usr/bin/env python3
"""Hash-bound CPU repair batch; every case is a bounded, isolated subprocess."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

from fastglycan.paired_teacher_protocol import sha256, write_json


def case(args):
    import numpy as np
    import torch
    from fastglycan.geometry_repair import repair_coordinates, preservation
    from fastglycan.sequence_gate_metrics import contact_objective
    from fastglycan.collision_audit import collision_records
    lock = json.loads((args.out/'lock.json').read_text())
    item = lock['cases'][args.case]
    target = args.out/'cases'/f'{args.case:03d}'
    target.mkdir(parents=True, exist_ok=True)
    result = dict(case=args.case, index=item['index'], seed=item['seed'], success=False,
                  lock_sha256=sha256(args.out/'lock.json'))
    started = time.monotonic()
    try:
        for key in ['coordinate', 'topology']:
            assert sha256(Path(item[key])) == item[key+'_sha256']
        for f, digest in (lock['source_hashes'] | lock['forcefield_hashes']).items():
            assert sha256(Path(f)) == digest
        packet = np.load(item['coordinate'])
        top = torch.load(item['topology'], map_location='cpu', weights_only=False)
        raw = packet['coordinates'].reshape(-1, 3)
        for key in ['atom_names', 'residue_ids', 'chain_ids']:
            assert np.array_equal(packet[key], top[key])
        repaired, full, pdb, audit = repair_coordinates(raw, top['atom_names'], top['residue_ids'],
            top['chain_ids'], item['sequence'], top['topology'].bonds.numpy())
        np.savez_compressed(target/'coordinates.npz', raw=raw, repaired=repaired, full=full,
            atom_names=top['atom_names'], residue_ids=top['residue_ids'], chain_ids=top['chain_ids'])
        (target/'full.pdb').write_text(pdb)
        def evaluate(x):
            x = torch.tensor(x, dtype=torch.float32)
            task, _ = contact_objective(x.unsqueeze(0), top['ca'])
            terms, geometry = top['topology'].terms(x)
            return dict(task=float(task), total=float(task+terms['bond']+2*terms['peptide']+terms['clash']+.2*terms['chirality']),
                        geometry=geometry, terms={k:float(v) for k,v in terms.items()})
        raw_metrics, repaired_metrics = evaluate(raw), evaluate(repaired)
        assert abs(raw_metrics['task']-item['raw_task']) < 1e-4
        for k,v in item['raw_geometry'].items():
            assert abs(raw_metrics['geometry'][k]-v) < 1e-4
        pairs = {name:collision_records(x, top['topology'], top['atom_names'], top['residue_ids'],
            top['chain_ids'], item['sequence']) for name,x in [('raw',raw),('repaired',repaired)]}
        result.update(success=True, raw=raw_metrics, repaired=repaired_metrics, audit=audit,
            preservation=preservation(raw,repaired,top['ca'].numpy()), pairs=pairs,
            coordinate_sha256=sha256(target/'coordinates.npz'), pdb_sha256=sha256(target/'full.pdb'))
    except Exception:
        result['error'] = traceback.format_exc()
    result['seconds'] = time.monotonic()-started
    write_json(target/'report.json', result)
    return 0 if result['success'] else 1


def batch(args):
    lock = json.loads((args.out/'lock.json').read_text())
    jobs = list(range(len(lock['cases'])))
    def run(index):
        directory = args.out/'cases'/f'{index:03d}'
        directory.mkdir(parents=True, exist_ok=True)
        report = directory/'report.json'
        if report.exists():
            old = json.loads(report.read_text())
            assert old['lock_sha256'] == sha256(args.out/'lock.json')
            if old['success']:
                assert sha256(directory/'coordinates.npz') == old['coordinate_sha256']
                assert sha256(directory/'full.pdb') == old['pdb_sha256']
            return old['success']  # failures are retained, not retried
        command = [sys.executable, __file__, '--out', str(args.out), '--case', str(index)]
        with (directory/'execution.log').open('w') as log:
            try:
                code = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=1800).returncode
            except subprocess.TimeoutExpired:
                code = -1
        if not report.exists():
            write_json(report, dict(case=index,index=lock['cases'][index]['index'], seed=lock['cases'][index]['seed'],
                success=False, error='timeout or process failure', returncode=code,
                lock_sha256=sha256(args.out/'lock.json')))
        return json.loads(report.read_text())['success']
    start = time.monotonic()
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(run,jobs))
    write_json(args.out/'exit.json', dict(complete=True, cases=len(results), successful=sum(results),
        failed=len(results)-sum(results), seconds=time.monotonic()-start))
    subprocess.run([sys.executable, str(Path(__file__).with_name('score_geometry_repair.py')), '--out', str(args.out)], check=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--case',type=int)
    args=parser.parse_args();args.out=args.out.resolve()
    if args.case is not None:
        sys.exit(case(args))
    batch(args)
