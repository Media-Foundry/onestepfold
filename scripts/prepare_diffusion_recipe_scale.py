#!/usr/bin/env python3
"""Freeze three new runs and the already-completed low-LR control."""
import argparse
import json
from pathlib import Path

from fastglycan.diffusion_recipe import resolve_diffusion_recipe
from fastglycan.paired_teacher_protocol import sha256, write_json


def prepare_diffusion_recipe_scale(root):
    assert not (root/'lock.json').exists()
    old=root.parent/'diffusion_learning_pilot_v1_20260930'
    calibration=root.parent/'diffusion_gradient_budget_v1_20260930/objective_calibration.json'
    audit=json.loads((old/'training_audit.json').read_text())
    assert audit['complete'] and audit['lock_sha256']==sha256(old/'lock.json')
    lock=json.loads((old/'lock.json').read_text())
    reference=audit['checkpoints']['gt_s2']
    assert sha256(Path(reference['path']))==reference['sha256']
    calibrated=json.loads(calibration.read_text())
    assert calibrated['calibration_state']=='initial'
    expected=dict(coordinate=.01,smooth_lddt=1.,bond=1.505408125612628,
        chirality=1.,clash=.0006600251156855778,teacher=.025476389066842815)
    assert calibrated['calibrated_weights']==expected
    # Identical native model/supervision; only trainer configuration is extended.
    for file in ['models/differentiable_mini.py','models/diffusion_adapter.py',
                 'models/soft_sequence_chart.py','adapter_supervision.py']:
        assert sha256(root/'code/src/fastglycan'/file)==sha256(old/'code/src/fastglycan'/file)
    lock.update(arms=['old_high','calibrated_low','calibrated_high'],
        arm_recipes=dict(old_high=dict(weights=lock['loss_weights'],teacher=True,lr_multiplier=10.),
            calibrated_low=dict(weights=expected,teacher=True,lr_multiplier=1.),
            calibrated_high=dict(weights=expected,teacher=True,lr_multiplier=10.)),
        old_low=reference,original_lock_sha256=sha256(old/'lock.json'),
        original_audit_sha256=sha256(old/'training_audit.json'),
        calibration_path=str(calibration),calibration_sha256=sha256(calibration),
        evaluation_role='train_only',validation_reevaluation=False,
        hashes={str(p):sha256(p) for p in (root/'code').rglob('*')
            if p.is_file() and p.suffix in ['.py','.md']})
    assert len(lock['order'])==2048 and len(lock['rows'])==128
    assert all(r['role']=='train' for r in lock['rows'])
    for arm in lock['arms']:resolve_diffusion_recipe(lock,arm)
    write_json(root/'lock.json',lock)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True)
    prepare_diffusion_recipe_scale(parser.parse_args().root)
