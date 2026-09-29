"""Empirical connection windows; descriptive calibration, not chemical gates."""
import numpy as np

from fastglycan.connection_audit import TOLERANCES


def equal_protein_quantile(values, groups, quantile):
    """Inverse weighted empirical CDF, with each represented protein total weight1."""
    values = np.asarray(values, dtype=float); groups = np.asarray(groups)
    if len(values) == 0 or values.shape != groups.shape or not np.isfinite(values).all():
        raise ValueError('invalid weighted observations')
    if not 0 <= quantile <= 1:
        raise ValueError('invalid quantile')
    _, inverse, counts = np.unique(groups, return_inverse=True, return_counts=True)
    weights = 1. / counts[inverse]; order = np.argsort(values, kind='stable')
    cumulative = np.cumsum(weights[order]); target = quantile * cumulative[-1]
    index = min(int(np.searchsorted(cumulative, target, side='left')), len(values) - 1)
    return float(values[order[index]])


def fit_connection_windows(edges):
    """Fit only calibration trans connections; prevent held-out leakage by API."""
    if any(r['role'] != 'calibration' for r in edges):
        raise ValueError('window fitting may only read calibration observations')
    result = {}
    for category in ['Pro', 'other']:
        rows = [r for r in edges if r['branch'] == 'trans' and r['next_class'] == category]
        groups = [r['group_id'] for r in rows]; proteins = len(set(groups))
        result[category] = dict(edges=len(rows), proteins=proteins, supported=len(rows) >= 100 and proteins >= 8)
        if not result[category]['supported']:
            continue
        stats = {}
        for term in TOLERANCES:
            values = np.abs([r[term + '_residual'] for r in rows])
            stats[term] = {f'q{int(q * 100)}': dict(pooled=float(np.quantile(values, q, method='linear')),
                equal_protein=equal_protein_quantile(values, groups, q)) for q in [.95, .99]}
        result[category]['windows'] = stats
    return result


def coverage_by_protein(rows, term, bound, seed=9302026):
    """Intervals resample proteins, retaining all their connections per draw."""
    if not rows:
        return dict(edges=0, proteins=0)
    grouped = {}
    for r in rows:
        grouped.setdefault(r['group_id'], []).append(abs(r[term + '_residual']) <= bound)
    counts = np.array([[sum(v), len(v)] for _, v in sorted(grouped.items())], dtype=float)
    rng = np.random.default_rng(seed)
    samples = counts[rng.integers(len(counts), size=(2000, len(counts)))]
    pooled = samples[:, :, 0].sum(1) / samples[:, :, 1].sum(1)
    means = (samples[:, :, 0] / samples[:, :, 1]).mean(1)
    return dict(edges=int(counts[:, 1].sum()), proteins=len(counts), bound=float(bound),
        pooled=float(counts[:, 0].sum() / counts[:, 1].sum()),
        equal_protein=float((counts[:, 0] / counts[:, 1]).mean()),
        pooled_ci95=np.quantile(pooled, [.025, .975]).tolist(),
        equal_protein_ci95=np.quantile(means, [.025, .975]).tolist(),
        per_protein={g: dict(covered=sum(v), edges=len(v), coverage=sum(v) / len(v)) for g, v in sorted(grouped.items())})
