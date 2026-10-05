"""Frozen A/raw, B/centered, C/site-weighted objectives for nineteen mutants."""
import numpy as np

ARMS=('A','B','C')


def training_site_weights(cases):
    energies=[]
    for c in cases:
        if c['role']!='train' or len(c['target_delta'])!=2:
            raise ValueError('weights require TRAIN old two-noise labels only')
        y=np.delete(np.asarray(c['target_delta'],dtype=np.float64).mean(0),c['wt'])
        if y.shape!=(19,) or not np.isfinite(y).all():raise ValueError('19 finite non-WT scores required')
        energies.append(float(np.mean((y-y.mean())**2)))
    if not energies:raise ValueError('empty TRAIN')
    floor=max(float(np.quantile(energies,.25,method='linear')),1e-12)
    raw=1/np.maximum(energies,floor);weights=raw/raw.mean()
    return dict(quantile=.25,quantile_method='linear',numerical_floor=1e-12,floor=floor,
                mean_weight=float(weights.mean()),sites=[dict(parent_index=c['parent_index'],position=c['position'],
                source_aa=c['source_aa'],centered_energy=v,weight=float(w)) for c,v,w in zip(cases,energies,weights)])


def score_objective(prediction,target,arm,weight=1.):
    if arm not in ARMS or prediction.shape!=target.shape or prediction.numel()!=19:
        raise ValueError('fixed19AA objective required')
    if arm=='A':base=(prediction-target).square().mean()
    else:base=((prediction-prediction.mean())-(target-target.mean())).square().mean()
    return base,base*weight if arm=='C' else base


def clipping_counterfactual(weighted_norm,weight,clip=1.,epsilon=1e-6):
    """Positive scalar reweighting at one fixed parameter state, not an Adam step."""
    if not np.isfinite(weighted_norm) or weighted_norm<0 or not np.isfinite(weight) or weight<=0:raise ValueError('finite nonnegative norm, positive weight')
    unweighted=weighted_norm/weight
    weighted_coef=min(1.,clip/(weighted_norm+epsilon))
    unweighted_coef=min(1.,clip/(unweighted+epsilon))
    return dict(unweighted_norm=unweighted,weighted_norm=weighted_norm,
                unweighted_post_norm=unweighted*unweighted_coef,weighted_post_norm=weighted_norm*weighted_coef,
                post_vector_multiplier=weight*weighted_coef/unweighted_coef,
                both_clipped=weighted_norm>clip and unweighted>clip,
                weighted_clipped=weighted_norm>clip,unweighted_clipped=unweighted>clip)
