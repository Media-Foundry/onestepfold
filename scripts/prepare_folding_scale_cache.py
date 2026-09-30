#!/usr/bin/env python3
"""Lock native folding caches for the new training/holdout split; no training."""
import argparse
import json
from pathlib import Path
import shutil
from fastglycan.paired_teacher_protocol import sha256, write_json


def prepare_folding_scale_cache(root, cycle, code):
    assert not (root/'lock.json').exists()
    experiment = json.loads((cycle/'lock.json').read_text())
    assert experiment['selection_sha256'] == sha256(cycle/'selection.json')
    source = Path(experiment['source'])
    assert experiment['source_audit_sha256'] == sha256(source/'audit.json')
    assert experiment['source_selection_lock_sha256'] == sha256(source/'selection_lock.json')
    source_lock = json.loads((source/'selection_lock.json').read_text())
    assert source_lock['data_manifest_sha256'] == sha256(source/'data_manifest.json')
    manifest = json.loads((source/'data_manifest.json').read_text())
    rows = json.loads((cycle/'selection.json').read_text())
    assert sum(r['role']=='train' for r in rows)==experiment['train_count']
    assert sum(r['role']=='validation' for r in rows)==32
    inputs = {}
    for r in rows:
        for folder in ['chemistry','data/examples']:
            for p in (source/folder/r['group_id']).iterdir():
                if p.is_file():
                    assert sha256(p)==manifest[str(p.relative_to(source))]
                    inputs[str(p)]=manifest[str(p.relative_to(source))]
    old = json.loads((cycle/'initial_training_lock.json').read_text())
    assert sha256(cycle/'initial_training_lock.json')==experiment['initial_training_lock_sha256']
    weights = {}; stats = {}
    for previous, digest in old['weights_sha256'].items():
        p = root.parent/'protenix_stage0_pkg/v1_1/runtime/checkpoint'/Path(previous).name
        assert sha256(p)==digest,p
        weights[str(p)]=digest; stats[str(p)]=[p.stat().st_size,p.stat().st_mtime_ns]
    assert shutil.disk_usage(root).free>100*1024**3
    assignments=[[] for _ in range(8)];loads=[0]*8
    for r in sorted(rows,key=lambda r:(-len(r['sequence']),r['group_id'])):
        i=min(range(8),key=lambda i:(loads[i],i));assignments[i].append(r);loads[i]+=len(r['sequence'])**2
    code_hashes={str(p):sha256(p) for p in code.rglob('*.py') if p.is_file()}
    code_hashes[str(Path(__file__))]=sha256(Path(__file__))
    write_json(root/'lock.json',dict(protocol='mini_folding_scaling_cycle_v1',
        cycle_lock_sha256=sha256(cycle/'lock.json'),source=str(source),rows=rows,
        assignments=assignments,estimated_loads=loads,input_hashes=inputs,hashes=code_hashes,
        weights_sha256=weights,weight_stats=stats,train_seeds=experiment['training_seeds'],
        validation_seeds=experiment['validation_seeds'],dtype='fp32',cycles=4,
        planned_conditioning=len(rows),planned_train_outputs=4*experiment['train_count'],
        workers=8,validation_predictions=False,training_started=False,
        note='Source count is not TRAIN count:32 new holdout rows receive conditioning only.'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--cycle',type=Path,required=True);p.add_argument('--code',type=Path,required=True)
    args=p.parse_args();prepare_folding_scale_cache(args.root.resolve(),args.cycle.resolve(),args.code.resolve())
