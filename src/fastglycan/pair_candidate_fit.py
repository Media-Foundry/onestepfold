"""Bounded single-context diagnostic contracts; no change to the recovery model."""
from collections import Counter
import math


FIT_SITE = 'p3_s37'
FIT_NODES = (0, 304, 1216, 4104, 8208)


def candidate_pair(choices, step, updates=8208):
    if len(choices) != 19 or len(set(choices)) != 19:
        raise ValueError('exactly nineteen distinct non-WT candidates required')
    if not 0 <= step < updates:
        raise ValueError('step outside the locked budget')
    return [choices[(2 * step + j) % 19] for j in range(2)]


def expected_exposures(choices, updates):
    if updates < 0 or updates > 8208:
        raise ValueError('invalid diagnostic budget')
    result = Counter({aa: 0 for aa in choices})
    for step in range(updates):
        result.update(candidate_pair(choices, step))
    return dict(result)


def validate_fit_site(site, original_train_sites, scale):
    if (site['site_key'] != FIT_SITE or FIT_SITE not in original_train_sites
            or site['role_n15'] != 'train' or site['parent_index'] != 3
            or site['position_zero_based'] != 36 or site['original_aa'] != 'T'
            or site['pdb_id'].upper() != '1W53'):
        raise ValueError('only preselected historical TRAIN 1W53 T37 is allowed')
    if set(site['candidates']) != set('ACDEFGHIKLMNPQRSTVWY') - {'T'}:
        raise ValueError('candidate inventory changed')
    candidate_pair(site['candidates'], 0)
    if not math.isfinite(scale) or scale != 31.323820267027703:
        raise ValueError('must retain the original training scale')


def gradient_groups(model):
    """Pre-clip Euclidean norms, including missing/zero gradients explicitly."""
    sums, missing = {}, []
    for name, param in model.named_parameters():
        group = '.'.join(name.split('.')[:2]) if name.startswith('blocks.') else name.split('.')[0]
        sums.setdefault(group, 0.)
        if param.grad is None:
            missing.append(name)
        else:
            sums[group] += float(param.grad.detach().double().square().sum())
    return dict(norms={name: math.sqrt(value) for name, value in sums.items()}, missing=missing)
