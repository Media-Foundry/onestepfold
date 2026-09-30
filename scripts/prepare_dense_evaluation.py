#!/usr/bin/env python3
"""Bind audited dense terminals to the frozen full-TRAIN evaluation and old controls."""
import argparse
import json
from pathlib import Path
from fastglycan.paired_teacher_protocol import sha256, write_json


def prepare_dense_evaluation(root):
    assert not (root/'lock.json').exists()
    train=root.parent/'diffusion_dense_learning_v1_20260930';prior=root.parent/'diffusion_recipe_evaluation_v1_20260930'
    training=json.loads((train/'lock.json').read_text());audit=json.loads((train/'training_audit.json').read_text())
    assert audit['complete'] and audit['lock_sha256']==sha256(train/'lock.json')
    old=json.loads((prior/'lock.json').read_text());assert old['rows']==training['rows']
    assert all(r['role']=='train' for r in training['rows']) and len(training['rows'])==128
    lock=dict(old);inputs=dict(old['input_hashes'])
    for row in training['rows']:
        g=row['group_id'];p=prior/'examples'/g/'report.json';report=json.loads(p.read_text())
        assert report['role']=='train' and report['lock_sha256']==sha256(prior/'lock.json')
        inputs[str(p)]=sha256(p)
        for e in report['entries']:
            if e['model']=='calibrated_high':
                f=p.parent/e['name'];assert sha256(f)==e['sha256'];inputs[str(f)]=e['sha256']
    inputs[str(train/'training_audit.json')]=sha256(train/'training_audit.json');inputs[str(train/'lock.json')]=sha256(train/'lock.json')
    for c in audit['checkpoints'].values():assert sha256(Path(c['path']))==c['sha256']
    for f in ['differentiable_mini.py','soft_sequence_chart.py']:
        assert sha256(root/'code/src/fastglycan/models'/f)==sha256(train/'code/src/fastglycan/models'/f)
    lock.pop('old_low',None)
    lock.update(train=str(train),training_lock_sha256=sha256(train/'lock.json'),checkpoints=audit['checkpoints'],
        selected_names={a:x['selected_names'] for a,x in training['preflights'].items()},
        models=['native_s1','native_s2','calibrated_high','token_dense','diffusion_dense'],
        reuse_models=dict(calibrated_high=dict(root=str(prior/'examples'),model='calibrated_high')),
        contrasts=[['diffusion_dense','token_dense'],['token_dense','native_s1'],['diffusion_dense','native_s1'],
            ['token_dense','calibrated_high'],['diffusion_dense','calibrated_high'],
            ['token_dense','native_s2'],['diffusion_dense','native_s2'],['native_s2','native_s1']],
        input_hashes=inputs,hashes={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.md']},
        expected_outputs=1280,expected_new_predictions=512,expected_probe_nfe=56,
        primary='TRAIN-only native dense scope comparison; no new acceptance gate or validation reuse')
    p=root/'code/docs/connection_reference_bands.json';lock['hashes'][str(p)]=sha256(p)
    write_json(root/'lock.json',lock)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();prepare_dense_evaluation(a.root)
