#!/usr/bin/env python3
"""Lock TRAIN128-only factorial evaluation after the three terminal audits."""
import argparse
import json
from pathlib import Path

from fastglycan.paired_teacher_protocol import sha256, write_json


def prepare_recipe_evaluation(root):
    assert not (root/'lock.json').exists()
    train=root.parent/'diffusion_recipe_scale_v1_20260930'
    old=root.parent/'diffusion_learning_evaluation_v1_20260930'
    training=json.loads((train/'lock.json').read_text())
    audit=json.loads((train/'training_audit.json').read_text())
    assert audit['complete'] and audit['lock_sha256']==sha256(train/'lock.json')
    cache=Path(training['cache']);cache_lock=json.loads((cache/'lock.json').read_text())
    assert sha256(cache/'lock.json')==training['cache_lock_sha256']
    rows=training['rows'];assert len(rows)==128 and all(r['role']=='train' for r in rows)
    inputs={str(train/'training_audit.json'):sha256(train/'training_audit.json'),
        str(train/'lock.json'):sha256(train/'lock.json')}
    for checkpoint in audit['checkpoints'].values():assert sha256(Path(checkpoint['path']))==checkpoint['sha256']
    for row in rows:
        g=row['group_id'];folder=cache/'examples'/g
        for name,digest in json.loads((folder/'report.json').read_text())['files'].items():
            assert sha256(folder/name)==digest;inputs[str(folder/name)]=digest
        previous=old/'examples'/g/'report.json';report=json.loads(previous.read_text())
        assert report['role']=='train' and report['group_id']==g
        assert report['lock_sha256']==sha256(old/'lock.json')
        inputs[str(previous)]=sha256(previous)
        for entry in report['entries']:
            if entry['model']=='gt_s2':
                path=previous.parent/entry['name'];assert sha256(path)==entry['sha256'];inputs[str(path)]=entry['sha256']
        # Bind all chemical identities and experimental labels used by CPU scoring.
        source=Path(training['source'])
        for path in [source/'chemistry'/g/'native.pt',source/'chemistry'/g/'mapping.npz']:
            assert sha256(path)==cache_lock['input_hashes'][str(path)];inputs[str(path)]=sha256(path)
        gt=source/'data/examples'/g/'gt.npz';inputs[str(gt)]=sha256(gt)
    old_lock=json.loads((old/'lock.json').read_text())
    assert old_lock['checkpoints']['gt_s2']==training['old_low']
    hashes={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.md']}
    bands=root/'code/docs/connection_reference_bands.json';hashes[str(bands)]=sha256(bands)
    for relative in ['models/differentiable_mini.py','models/diffusion_adapter.py','models/soft_sequence_chart.py']:
        assert sha256(root/'code/src/fastglycan'/relative)==sha256(train/'code/src/fastglycan'/relative)
    assignments=[[] for _ in range(8)];loads=[0]*8
    for row in sorted(rows,key=lambda r:(-len(r['sequence']),r['group_id'])):
        i=min(range(8),key=lambda j:(loads[j],j));assignments[i].append(row);loads[i]+=len(row['sequence'])**2
    arms=['old_low','old_high','calibrated_low','calibrated_high']
    contrasts=[['native_s2','native_s1']]+[[a,'native_s1'] for a in arms]+[
        ['old_high','old_low'],['calibrated_high','calibrated_low'],
        ['calibrated_low','old_low'],['calibrated_high','old_high']]
    write_json(root/'lock.json',dict(train=str(train),cache=str(cache),source=training['source'],
        rows=rows,assignments=assignments,checkpoints=audit['checkpoints'],
        old_low=training['old_low'],reuse_models=dict(old_low=dict(root=str(old/'examples'),model='gt_s2')),
        hashes=hashes,input_hashes=inputs,weights_sha256=training['weights_sha256'],weight_stats=training['weight_stats'],
        train_seeds=cache_lock['train_seeds'],models=['native_s1','native_s2']+arms,
        probe=rows[0],contrasts=contrasts,bootstrap=dict(replicates=10000,seed=20260930,unit='protein after mean over two noises'),
        primary='TRAIN-only fixed-budget 2x2 fitting comparison; no validation/generalization/deployment claim',
        expected_outputs=1536,expected_new_predictions=768,expected_probe_nfe=80))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True)
    prepare_recipe_evaluation(parser.parse_args().root)
