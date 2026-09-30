"""Guard the two scientifically different arms and fail-closed explicit configs."""
import copy
import pytest
from fastglycan.diffusion_recipe import resolve_diffusion_recipe

WEIGHTS=dict(coordinate=.01,smooth_lddt=1.,bond=10.,chirality=1.,clash=.1,teacher=.0025)


def test_historical_and_explicit_teacher_semantics():
    lock=dict(arms=['gt','gt_s2'],loss_weights=WEIGHTS)
    for arm in lock['arms']:
        recipe=resolve_diffusion_recipe(lock,arm)
        assert recipe==dict(weights=WEIGHTS,teacher=arm=='gt_s2',lr_multiplier=1.)
    lock['arms']=['old_high','calibrated_low','calibrated_high']
    lock['arm_recipes']={a:dict(weights=copy.copy(WEIGHTS),teacher=True,
        lr_multiplier=10. if a.endswith('high') else 1.) for a in lock['arms']}
    for arm in lock['arms']:assert resolve_diffusion_recipe(lock,arm)['teacher']
    del lock['arm_recipes']['old_high']
    with pytest.raises(ValueError):resolve_diffusion_recipe(lock,'calibrated_low')


@pytest.mark.parametrize('bad', [float('nan'),float('inf'),-1.])
def test_invalid_weight_rejected(bad):
    lock=dict(arms=['gt'],loss_weights=dict(WEIGHTS,teacher=bad))
    with pytest.raises(ValueError):resolve_diffusion_recipe(lock,'gt')
