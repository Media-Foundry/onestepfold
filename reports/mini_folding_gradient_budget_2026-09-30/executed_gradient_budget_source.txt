"""Coordinate-side loss-gradient accounting; not an optimizer-update attribution."""
import numpy as np


def coordinate_gradient_budget(gradients, weights, ca_mask):
    """Keep signed Gram products and cancellation; undefined cosines remain None."""
    keys=sorted(gradients)
    if not keys or set(keys)!=set(weights):
        raise ValueError('gradient/weight keys must match')
    arrays=[np.asarray(gradients[k],dtype=np.float64) for k in keys]
    shape=arrays[0].shape
    mask=np.asarray(ca_mask)
    if len(shape)!=2 or shape[1]!=3 or mask.shape!=(shape[0],) or mask.dtype!=bool:
        raise ValueError('expected N x 3 gradients and boolean CA mask')
    if any(a.shape!=shape or not np.isfinite(a).all() for a in arrays):
        raise ValueError('gradient shape or finite values invalid')
    w=np.array([weights[k] for k in keys],dtype=np.float64)
    if not np.isfinite(w).all() or (w<0).any():
        raise ValueError('weights must be finite and nonnegative')
    out={'keys':keys,'weights':dict(weights),'spaces':{}}
    for name,sel in [('all',slice(None)),('ca',mask)]:
        matrix=np.stack([a[sel].reshape(-1) for a in arrays]);gram=matrix@matrix.T
        weighted=matrix*w[:,None];total=weighted.sum(0);norm=float(np.linalg.norm(total))
        norms=np.linalg.norm(weighted,axis=1);rawnorms=np.linalg.norm(matrix,axis=1)
        terms={}
        for i,k in enumerate(keys):
            rest=total-weighted[i];rn=float(np.linalg.norm(rest));gn=float(norms[i])
            terms[k]={'raw_norm':float(rawnorms[i]),'weighted_norm':gn,
                      'ratio_to_total_norm':gn/norm if norm>0 else None,
                      'cosine_with_rest':float(weighted[i]@rest/(gn*rn)) if gn>0 and rn>0 else None,
                      'signed_projection_on_total':float(weighted[i]@total/norm) if norm>0 else None}
        out['spaces'][name]={'raw_gram':gram.tolist(),'total_norm':norm,'sum_term_norms':float(norms.sum()),
                            'cancellation_ratio':norm/float(norms.sum()) if norms.sum()>0 else None,'terms':terms}
    return out
