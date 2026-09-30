"""Explicit per-arm configuration; historical two-arm locks retain their semantics."""
import math


def resolve_diffusion_recipe(lock, arm):
    if arm not in lock['arms']:
        raise ValueError('arm absent from execution lock')
    overrides = lock.get('arm_recipes', {})
    if overrides and set(overrides) != set(lock['arms']):
        raise ValueError('explicit recipes must cover every arm')
    recipe = overrides.get(arm, dict(weights=lock['loss_weights'], teacher=arm == 'gt_s2', lr_multiplier=1.))
    if set(recipe) != {'weights', 'teacher', 'lr_multiplier'} or type(recipe['teacher']) is not bool:
        raise ValueError('invalid recipe schema')
    weights = dict(recipe['weights'])
    if set(weights) != {'coordinate', 'smooth_lddt', 'bond', 'chirality', 'clash', 'teacher'}:
        raise ValueError('incomplete objective')
    if not all(math.isfinite(v) and v >= 0 for v in weights.values()):
        raise ValueError('invalid loss weight')
    multiplier = recipe['lr_multiplier']
    if not math.isfinite(multiplier) or multiplier <= 0:
        raise ValueError('invalid LR multiplier')
    return dict(weights=weights, teacher=recipe['teacher'], lr_multiplier=multiplier)
