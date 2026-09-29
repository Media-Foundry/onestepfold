"""Necessary Cα-spacing bounds for the frozen local chemical representation.

This is a geometric audit, not a projection, solver, or new acceptance policy.
Bounds concern an individual peptide connection and omit carbonyl/global/clash
constraints; being inside them does not establish whole-chain feasibility.
"""
import numpy as np


def peptide_span_squared(a, b, c, cosine_c, cosine_n, cosine_omega):
    """Squared |CA(i+1)-CA(i)| from the three bond lengths and two angles."""
    a, b, c, u, v, q = np.broadcast_arrays(*[np.asarray(x, dtype=np.float64)
        for x in [a, b, c, cosine_c, cosine_n, cosine_omega]])
    if not all(np.isfinite(x).all() for x in [a, b, c, u, v, q]):
        raise ValueError('nonfinite geometry')
    if np.any(a <= 0) or np.any(b <= 0) or np.any(c <= 0):
        raise ValueError('nonpositive bond length')
    if any(np.any(np.abs(x) > 1) for x in [u, v, q]):
        raise ValueError('invalid angle cosine')
    return a*a+b*b+c*c-2*a*b*u-2*b*c*v+2*a*c*(u*v-np.sqrt(1-u*u)*np.sqrt(1-v*v)*q)


def _product_bounds(*intervals):
    low, high = intervals[0]
    for lo, hi in intervals[1:]:
        corners = np.stack([low*lo, low*hi, high*lo, high*hi])
        low, high = corners.min(axis=0), corners.max(axis=0)
    return low, high


def ca_span_bounds(a, c, cn_target, widths, omega_sign):
    """Analytic min/max in a monotonic residual box, with derivative checks.

    a=CA-C and c=N-CA remain fixed by the local chemical constructor. Widths
    specify allowed absolute CN, angle-cosine and omega-phase-chord residuals.
    omega_sign is +1 for cis, -1 for trans. Unsupported/nonmonotonic boxes fail
    explicitly. Floating-point results are not outward-rounded formal intervals;
    consumers must retain a numerical margin when classifying near boundaries.
    """
    keys = ['cn', 'angle_c', 'angle_n', 'omega']
    args = [a, c, cn_target, omega_sign] + [widths[k] for k in keys]
    a, c, b0, sign, wb, wu, wv, wq = np.broadcast_arrays(
        *[np.asarray(x, dtype=np.float64) for x in args])
    if not all(np.isfinite(x).all() for x in [a, c, b0, sign, wb, wu, wv, wq]):
        raise ValueError('nonfinite box')
    if np.any(a <= 0) or np.any(c <= 0) or np.any(b0 <= wb):
        raise ValueError('nonpositive bond length interval')
    if not np.isin(sign, [-1, 1]).all() or any(np.any(x < 0) for x in [wb, wu, wv, wq]):
        raise ValueError('invalid branch or width')
    if np.any(wq >= np.sqrt(2)):
        raise ValueError('omega box must stay in its branch hemisphere')
    blo, bhi = b0-wb, b0+wb
    ulo, uhi = -.4473-wu, -.4473+wu
    vlo, vhi = -.5203-wv, -.5203+wv
    if np.any(ulo <= -1) or np.any(uhi >= 1) or np.any(vlo <= -1) or np.any(vhi >= 1):
        raise ValueError('degenerate angle interval')
    qlo = np.where(sign > 0, 1-wq*wq/2, -1.)
    qhi = np.where(sign > 0, 1., -1+wq*wq/2)
    # sin(angle) ranges; max=1 when its cosine interval crosses zero.
    su = (np.sqrt(1-np.maximum(ulo*ulo, uhi*uhi)),
          np.sqrt(1-np.where((ulo <= 0)&(uhi >= 0), 0, np.minimum(ulo*ulo, uhi*uhi))))
    sv = (np.sqrt(1-np.maximum(vlo*vlo, vhi*vhi)),
          np.sqrt(1-np.where((vlo <= 0)&(vhi >= 0), 0, np.minimum(vlo*vlo, vhi*vhi))))
    ru = (ulo/np.sqrt(1-ulo*ulo), uhi/np.sqrt(1-uhi*uhi))
    rv = (vlo/np.sqrt(1-vlo*vlo), vhi/np.sqrt(1-vhi*vhi))
    db_lower = 2*blo-2*a*uhi-2*c*vhi
    du_upper = -2*a*blo+2*a*c*(vhi+_product_bounds(ru, sv, (qlo, qhi))[1])
    dv_upper = -2*c*blo+2*a*c*(uhi+_product_bounds(rv, su, (qlo, qhi))[1])
    if np.any(db_lower <= 0) or np.any(du_upper >= 0) or np.any(dv_upper >= 0):
        raise ValueError('monotonicity not certified for this box')
    # d(span²)/dq=-2ac sin(alpha)sin(beta)<0 throughout this box.
    low2 = peptide_span_squared(a, blo, c, uhi, vhi, qhi)
    high2 = peptide_span_squared(a, bhi, c, ulo, vlo, qlo)
    if np.any(low2 < 0) or np.any(high2 < low2):
        raise ValueError('invalid span interval')
    return dict(lower=np.sqrt(low2), upper=np.sqrt(high2),
        db_lower=db_lower, du_upper=du_upper, dv_upper=dv_upper)


def ca_motion_lower_bound(gaps):
    """A necessary RMS Cα motion from maximum-weight disjoint violated edges.

    An edge gap g requires ||delta_i||+||delta_j||>=g, hence squared endpoint
    movement >=g²/2. Only disjoint edges can be added without double counting.
    This lower bound is not a constructed motion or a global feasibility proof.
    """
    gaps = np.asarray(gaps, dtype=np.float64)
    if gaps.ndim != 1 or not len(gaps) or not np.isfinite(gaps).all() or np.any(gaps < 0):
        raise ValueError('expected finite nonnegative edge gaps')
    before_previous = previous = 0.
    for value in gaps:
        best = max(previous, before_previous+value*value/2)
        before_previous, previous = previous, best
    return float(np.sqrt(previous/(len(gaps)+1)))
