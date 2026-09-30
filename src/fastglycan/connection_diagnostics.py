"""Descriptive connection reporting; empirical quantiles are NOT acceptance gates."""
import numpy as np

from .connection_audit import TOLERANCES


def describe_connection_distribution(measurement, sequence, calibration):
    """Summarize current nearest-branch residuals, including unsupported cis edges.

    Residue indices are one-based positions in the supplied single chain. The
    frozen equal-protein quantiles apply only to nearest-trans edges, separated
    by the following residue being Pro. No pooled pass/fail is constructed.
    """
    assert calibration['not_acceptance_thresholds'] is True
    branch = np.asarray(measurement['nearest_omega_sign'])
    if branch.shape != (len(sequence)-1,) or not np.isin(branch, [-1, 1]).all():
        raise ValueError('invalid nearest-branch labels')
    if not np.array_equal(branch, measurement['omega_sign']):
        raise ValueError('descriptive calibration requires nearest-branch residuals')
    residuals = {k: np.asarray(v, dtype=np.float64) for k, v in measurement['residuals'].items()}
    if set(residuals) != set(TOLERANCES) or any(v.shape != branch.shape or not np.isfinite(v).all() for v in residuals.values()):
        raise ValueError('invalid connection residuals')
    result = dict(not_acceptance_thresholds=True, legacy_role='historical diagnostic only',
                  edges=len(branch), calibration_proteins=calibration['calibration_proteins'], groups={})
    pro = np.array([aa == 'P' for aa in sequence[1:]])
    for kind, kind_mask in [('Pro', pro), ('other', ~pro)]:
        reference = calibration['windows'][kind]
        for state, sign in [('trans', -1), ('cis', 1)]:
            positions = np.flatnonzero(kind_mask & (branch == sign))
            group = dict(edges=len(positions), left_residue_positions=(positions+1).tolist(),
                         calibration_supported=state == 'trans' and reference['supported'],
                         calibration_edges=reference['edges'], terms={})
            for term, values in residuals.items():
                signed = values[positions]; magnitude = np.abs(signed)
                entry = dict(signed_values=signed.tolist(), legacy_window=TOLERANCES[term],
                             legacy_exceed_positions=(positions[magnitude > TOLERANCES[term]+1e-6]+1).tolist())
                if len(positions):
                    entry.update(signed_mean=float(signed.mean()), rms=float(np.sqrt(np.mean(signed**2))),
                                 absolute_p50=float(np.quantile(magnitude, .5)), absolute_p95=float(np.quantile(magnitude, .95)),
                                 absolute_max=float(magnitude.max()), worst_left_residue=int(positions[magnitude.argmax()]+1))
                if group['calibration_supported']:
                    entry['reference_bands'] = {}
                    for quantile in ['q95', 'q99']:
                        bound = reference['windows'][term][quantile]['equal_protein']
                        exceed = magnitude > bound
                        entry['reference_bands'][quantile] = dict(bound=bound, count=int(exceed.sum()),
                            fraction=float(exceed.mean()) if len(exceed) else None,
                            left_residue_positions=(positions[exceed]+1).tolist())
                group['terms'][term] = entry
            result['groups'][f'{kind}_{state}'] = group
    return result
