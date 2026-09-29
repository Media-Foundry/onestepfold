"""Observed local backbone geometry and split-safe diagnostic reference fitting."""
import numpy as np

BACKBONE_METRICS = ('n_ca', 'ca_c', 'c_o', 'n_ca_c_degrees', 'ca_c_o_degrees')


def measure_backbone_local_geometry(coordinates):
    """N/CA/C/O ordered coordinates, shape (...,4,3); reject degeneracy."""
    x = np.asarray(coordinates, dtype=np.float64)
    if x.shape[-2:] != (4, 3) or not np.isfinite(x).all():
        raise ValueError('expected finite N/CA/C/O coordinates')
    n, ca, c, o = np.moveaxis(x, -2, 0)
    lengths = [np.linalg.norm(a-b, axis=-1) for a,b in [(n,ca),(ca,c),(c,o)]]
    if any(np.any(v <= 1e-8) for v in lengths):
        raise ValueError('degenerate backbone bond')
    values = dict(zip(BACKBONE_METRICS[:3], lengths))
    for name, a, b in [(BACKBONE_METRICS[3], n-ca, c-ca),
                       (BACKBONE_METRICS[4], ca-c, o-c)]:
        cosine = np.sum(a*b, axis=-1)/(np.linalg.norm(a,axis=-1)*np.linalg.norm(b,axis=-1))
        values[name] = np.degrees(np.arccos(np.clip(cosine, -1, 1)))
    return values


def fit_backbone_reference(rows, amino_acids='ACDEFGHIKLMNPQRSTVWY'):
    """Reject held-out records; estimate internal residues without fallback."""
    if any(r['role'] != 'calibration' for r in rows):
        raise ValueError('held-out rows supplied to calibration')
    result = {}
    for aa in amino_acids:
        selected = [r for r in rows if r['amino_acid'] == aa and not r['terminal']]
        count = len(selected); proteins = len({r['group_id'] for r in selected})
        supported = count >= 30 and proteins >= 8
        result[aa] = dict(residues=count, proteins=proteins, supported=supported, metrics={})
        for name in BACKBONE_METRICS:
            values = np.array([r[name] for r in selected])
            if not np.isfinite(values).all():
                raise ValueError('nonfinite calibration geometry')
            result[aa]['metrics'][name] = (dict(median=float(np.median(values)),
                q05=float(np.quantile(values,.05)), q95=float(np.quantile(values,.95)))
                if supported else None)
    return result
