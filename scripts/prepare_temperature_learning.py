#!/usr/bin/env python3
"""One new width1 arm with matched initial D-gradient scale and fixed TRAIN control."""
import argparse
import json
from pathlib import Path
from fastglycan.paired_teacher_protocol import sha256, write_json


def prepare_temperature_training(root):
    assert not (root/'lock.json').exists()
    previous=root.parent/'diffusion_recipe_scale_v1_20260930'
    probe=root.parent/'diffusion_temperature_probe_v1_20260930'
    audit=json.loads((previous/'training_audit.json').read_text())
    assert audit['complete'] and audit['lock_sha256']==sha256(previous/'lock.json')
    calibration=json.loads((probe/'calibration.json').read_text())
    assert calibration['complete'] and calibration['initial_only'] and calibration['optimizer_updates']==0
    assert calibration['lock_sha256']==sha256(probe/'lock.json')
    lock=json.loads((previous/'lock.json').read_text())
    baseline=lock['arm_recipes']['calibrated_high'];weights=dict(baseline['weights'])
    assert weights['smooth_lddt']==1 and baseline['lr_multiplier']==10.
    weights['smooth_lddt']=calibration['weight_D']
    for f in ['differentiable_mini.py','diffusion_adapter.py','soft_sequence_chart.py']:
        assert sha256(root/'code/src/fastglycan/models'/f)==sha256(previous/'code/src/fastglycan/models'/f)
    lock.update(arms=['wide_matched'],arm_recipes=dict(wide_matched=dict(weights=weights,teacher=True,lr_multiplier=10.)),
        smooth_temperature_by_arm=dict(wide_matched=1.),
        temperature_control=audit['checkpoints']['calibrated_high'],
        temperature_calibration=dict(path=str(probe/'calibration.json'),sha256=sha256(probe/'calibration.json')),
        hashes={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.md']},
        evaluation_role='train_only',validation_reevaluation=False)
    write_json(root/'lock.json',lock)


def prepare_temperature_evaluation(root):
    assert not (root/'lock.json').exists()
    train=root.parent/'diffusion_temperature_learning_v1_20260930'
    prior=root.parent/'diffusion_recipe_evaluation_v1_20260930'
    training=json.loads((train/'lock.json').read_text());audit=json.loads((train/'training_audit.json').read_text())
    assert audit['complete'] and audit['lock_sha256']==sha256(train/'lock.json')
    old=json.loads((prior/'lock.json').read_text());assert old['rows']==training['rows']
    lock=dict(old);inputs=dict(old['input_hashes']);reuse={};analysis={}
    for name in ['calibrated_low','calibrated_high']:
        reuse[name]=dict(root=str(prior/'examples'),model=name);analysis[name]=old['checkpoints'][name]
    for row in training['rows']:
        g=row['group_id'];path=prior/'examples'/g/'report.json';report=json.loads(path.read_text())
        assert report['role']=='train' and report['lock_sha256']==sha256(prior/'lock.json')
        inputs[str(path)]=sha256(path)
        for entry in report['entries']:
            if entry['model'] in reuse:
                file=path.parent/entry['name'];assert sha256(file)==entry['sha256'];inputs[str(file)]=entry['sha256']
    inputs[str(train/'training_audit.json')]=sha256(train/'training_audit.json')
    inputs[str(train/'lock.json')]=sha256(train/'lock.json')
    for checkpoint in [*audit['checkpoints'].values(),*analysis.values()]:assert sha256(Path(checkpoint['path']))==checkpoint['sha256']
    for f in ['differentiable_mini.py','diffusion_adapter.py','soft_sequence_chart.py']:
        assert sha256(root/'code/src/fastglycan/models'/f)==sha256(train/'code/src/fastglycan/models'/f)
    lock.pop('old_low',None)
    lock.update(train=str(train),checkpoints=audit['checkpoints'],analysis_checkpoints=analysis,reuse_models=reuse,
        models=['native_s1','native_s2','calibrated_low','calibrated_high','wide_matched'],
        contrasts=[['native_s2','native_s1'],['calibrated_low','native_s1'],['calibrated_high','native_s1'],
            ['wide_matched','native_s1'],['wide_matched','calibrated_high'],['wide_matched','calibrated_low']],
        input_hashes=inputs,hashes={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.md']},
        expected_outputs=1280,expected_new_predictions=256,expected_probe_nfe=32,
        primary='TRAIN-only width1 matched-strength minus archived width0.1 calibrated_high; no new acceptance gate')
    bands=root/'code/docs/connection_reference_bands.json';lock['hashes'][str(bands)]=sha256(bands)
    write_json(root/'lock.json',lock)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--mode',choices=['training','evaluation'],required=True);a=parser.parse_args()
    if a.mode=='training':prepare_temperature_training(a.root)
    else:prepare_temperature_evaluation(a.root)
