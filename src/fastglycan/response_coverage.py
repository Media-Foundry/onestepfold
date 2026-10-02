"""Matched archived-context selection and per-candidate error decomposition."""
import torch

RESTRICTED = ((3,36),(3,83),(4,1),(5,64),(7,43),(7,85),(12,10),(18,178),(19,89),(22,43))
EXPANDED = RESTRICTED[:6] + ((12,71),(18,12),(19,136),(22,24))
SETS = {'restricted': RESTRICTED, 'expanded': EXPANDED}
EXCLUDED = ((4,24),(5,33),(6,9),(6,16))
SNAPSHOTS = (10920,21840,32760)
SEEDS = (231301,231303)


def coverage_stratum(rows, arm, parent, position):
    train = SETS[arm]
    if (parent,position) in train:
        return 'train'
    parents = {p for p,_ in train}
    sources = {rows[p]['sequence'][i] for p,i in train}
    return ('seen_protein' if parent in parents else 'unseen_protein') + '_' + ('covered_source' if rows[parent]['sequence'][position] in sources else 'uncovered_source')


def coverage_exposures(step):
    if not 0 <= step <= SNAPSHOTS[-1]:
        raise ValueError('outside locked budget')
    return [step//10 + (i < step%10) for i in range(10)]


def response_polar_errors(prediction, target):
    """FP64 sufficient statistics; cosine is undefined for zero vectors.

    A teacher-optimal scalar is an offline diagnostic, never a calibrated model.
    Preserve the original mean-energy floor, including its effect on the identity.
    """
    p,t = prediction.detach().double().flatten(1), target.detach().double().flatten(1)
    if p.shape != t.shape or not torch.isfinite(p).all() or not torch.isfinite(t).all():
        raise ValueError('finite matching candidate matrices required')
    pp,tt,pt = p.square().mean(1),t.square().mean(1),(p*t).mean(1)
    err=(p-t).square().mean(1)
    records=[]
    for pe,te,dot,e in zip(pp.tolist(),tt.tolist(),pt.tolist(),err.tolist()):
        den=max(te,1e-6)
        r=(pe/te)**.5 if te>0 else None
        c=dot/(pe*te)**.5 if pe>0 and te>0 else None
        identity=(te+pe-2*dot)/den
        alpha=dot/pe if pe>0 else None
        optimal=max(0.,te-dot*dot/pe)/den if pe>0 else te/den
        records.append(dict(prediction_mean_energy=pe,teacher_mean_energy=te,dot_mean=dot,
                            amplitude_ratio=r,cosine=c,teacher_zero=te==0,prediction_zero=pe==0,
                            denominator_floor_active=te<1e-6,nmse=e/den,
                            expanded_identity_nmse=identity,
                            oracle_scalar=alpha,oracle_scaled_nmse=optimal))
    return records
