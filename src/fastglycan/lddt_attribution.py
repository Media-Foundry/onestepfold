"""Additive attribution of the existing atom-averaged, inter-residue lDDT."""
import numpy as np
from scipy.spatial.distance import cdist


def lddt_attribution(predicted, target, residues):
    """Expose atom and unordered-pair contributions without changing denominators.

    Pair weights are (1/n_i + 1/n_j)/N_valid, NOT uniform over pairs. A partition
    of atoms or pairs therefore sums exactly to the original atom-mean metric.
    """
    x=np.asarray(predicted,dtype=np.float64);y=np.asarray(target,dtype=np.float64)
    residues=np.asarray(residues)
    if x.shape!=y.shape or x.shape!=(len(residues),3) or not np.isfinite([x,y]).all():
        raise ValueError('invalid coordinates or residue inventory')
    reference=cdist(y,y)
    keep=(reference<15)&(residues[:,None]!=residues[None,:])
    counts=keep.sum(1);valid=counts>0
    if not valid.any():raise ValueError('no evaluable atom pairs')
    pairs=np.column_stack(np.nonzero(np.triu(keep,1)))
    i,j=pairs.T
    error=np.abs(np.linalg.norm(x[i]-x[j],axis=1)-reference[i,j])
    thresholds=(error[:,None]<np.array([.5,1.,2.,4.])).astype(np.float64)/4
    pair_scores=thresholds.sum(1)
    weights=(1/counts[i]+1/counts[j])/valid.sum()
    sums=np.bincount(pairs.ravel(),weights=np.repeat(pair_scores,2),minlength=len(x))
    per_atom=np.divide(sums,counts,out=np.zeros(len(x)),where=valid)
    contribution=per_atom/valid.sum()
    return dict(score=float(contribution.sum()),per_atom=per_atom,valid=valid,counts=counts,
                atom_contribution=contribution,pairs=pairs,pair_weights=weights,
                pair_contribution=weights*pair_scores,threshold_contribution=weights[:,None]*thresholds,
                error=error,reference_distance=reference[i,j])
