#!/usr/bin/env python3
"""Freeze a new unscored folding holdout and honest training size before caching."""
import argparse
import hashlib
import json
from pathlib import Path
from fastglycan.paired_teacher_protocol import sha256, write_json


def prepare_folding_scale_split(root, source):
    assert not (root/'lock.json').exists()
    audit = json.loads((source/'audit.json').read_text())
    source_lock = json.loads((source/'selection_lock.json').read_text())
    assert audit['verified_sources'] and audit['selection_lock_sha256'] == sha256(source/'selection_lock.json')
    assert source_lock['selection_sha256'] == sha256(source/'selection.json')
    assert source_lock['data_manifest_sha256'] == sha256(source/'data_manifest.json')
    records = json.loads((source/'selection.json').read_text())
    parent = Path(json.loads((source/'source_lock.json').read_text())['parent'])
    prior = json.loads((parent/'origin/old/selection.json').read_text())
    original = {r['group_id'] for r in prior if r['role']=='train'}
    assert len(original) == 128 and original <= {r['group_id'] for r in records}
    holdout = []
    for stratum in (0,1):
        choices = [r for r in records if r['group_id'] not in original and int(len(r['sequence'])>=256)==stratum]
        choices.sort(key=lambda r:hashlib.sha256(('folding-scale-holdout-v1:20260930:'+r['group_id']).encode()).hexdigest())
        assert len(choices)>=16
        holdout.extend(choices[:16])
    held = {r['group_id'] for r in holdout}
    rows = [r | dict(role='validation' if r['group_id'] in held else 'train',
        source_role_before_split=r['role'],folding_cohort='scale_v1') for r in records]
    train = [r for r in rows if r['role']=='train']
    assert len(held)==32 and not original.intersection(held)
    assert len(train)>128 and len(rows)==source_lock['selected']
    frozen_old = json.loads((root/'initial_training_lock.json').read_text())
    assert frozen_old['schema']=='native_dense_diffusion_training_v1'
    assert {r['group_id'] for r in frozen_old['rows']}==original
    arms = dict(train128=sorted(original),expanded=sorted(r['group_id'] for r in train))
    orders = {}
    for arm,groups in arms.items():
        order=[]; epoch=0
        while len(order)<8192:
            ranked=sorted(groups,key=lambda g:hashlib.sha256(f'folding-scale-order-v1:{epoch}:{g}'.encode()).hexdigest())
            order.extend(dict(group_id=g,epoch=epoch,seed=[600001,600011][epoch%2]) for g in ranked)
            epoch+=1
        orders[arm]=order[:8192]
        assert all(r['group_id'] not in held for r in orders[arm])
    write_json(root/'selection.json',rows)
    write_json(root/'lock.json',dict(protocol='mini_folding_scaling_cycle_v1',
        source=str(source),source_audit_sha256=sha256(source/'audit.json'),
        source_selection_lock_sha256=sha256(source/'selection_lock.json'),
        source_shortfall_from512=source_lock['shortfall'],source_count=len(rows),
        selection_sha256=sha256(root/'selection.json'),train_count=len(train),validation_count=32,
        original_train_ids=sorted(original),arms=arms,orders=orders,
        initial_checkpoint_sha256='7fc01820269b6f376f8313b79c4ab2bf8fcfd2a0b2a017a432033a51b73fd829',
        initial_training_lock_sha256=sha256(root/'initial_training_lock.json'),
        training_seeds=[600001,600011],validation_seeds=[810013,810029],
        updates=2048,exposures=8192,accumulation=4,optimizer_reset=True,
        optimizer=dict(betas=[.9,.999],eps=1e-8,weight_decay=0.,clip=1.),
        learning_rate=dict(peak=1e-5,warmup_updates=64,terminal=1e-6,schedule='linear warmup then cosine through update2048'),
        weights=frozen_old['weights'],smooth_temperature=.1,cycles=4,steps=1,samples=1,
        trainable_scope='diffusion_dense',validation_only_at_terminal=True,
        checkpoint_selection='fixed terminal; no best-of-checkpoints',
        script_sha256=sha256(Path(__file__)),protocol_sha256=sha256(root/'mini_folding_scaling_cycle_v1.md'),
        training_started=False,validation_predictions=False))
    print(json.dumps(dict(source=len(rows),train=len(train),new_validation=32,source_shortfall=source_lock['shortfall'])))


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--source',type=Path,required=True)
    args=p.parse_args();prepare_folding_scale_split(args.root.resolve(),args.source.resolve())
