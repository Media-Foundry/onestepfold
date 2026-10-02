"""Post-hoc spectra of real hard-mutant C4 endpoints; no endpoint predictor."""
import numpy as np


def hard_response_spectrum(matrix, *, centered=False):
    """Rows are 19 non-WT responses; accumulate their small Gram matrix in FP64."""
    x=np.asarray(matrix,dtype=np.float64)
    if x.ndim!=2 or not np.isfinite(x).all():raise ValueError('finite response matrix required')
    if centered:x=x-x.mean(axis=0,keepdims=True)
    gram=x@x.T;values=np.linalg.eigvalsh(gram)[::-1];trace=float(np.trace(gram))
    if trace==0:
        return dict(energy=0.,zero_signal=True,cumulative_energy=None,rank95=None,rank99=None,
                    singular_values=[0.]*len(values),effective_rank=None,participation_rank=None)
    if values.min() < -1e-10*trace:raise ValueError('Gram matrix not positive semidefinite')
    values=np.maximum(values,0);weights=values/values.sum();cumulative=np.cumsum(weights)
    nonzero=weights>0
    return dict(energy=trace,zero_signal=False,cumulative_energy=cumulative.tolist(),
        rank95=int(np.searchsorted(cumulative,.95)+1),rank99=int(np.searchsorted(cumulative,.99)+1),
        singular_values=np.sqrt(values).tolist(),effective_rank=float(np.exp(-(weights[nonzero]*np.log(weights[nonzero])).sum())),
        participation_rank=float(1/(weights*weights).sum()))


def analyze_hard_response_site(endpoints, wt_index, position):
    """Subtract after promotion to FP64; never normalize individual AA responses."""
    order=np.arange(20)!=wt_index
    blocks={k:np.asarray(endpoints[k],np.float64)[order]-np.asarray(endpoints[k],np.float64)[wt_index]
            for k in ['s_site','z_row','z_col']}
    flat={k:v.reshape(19,-1) for k,v in blocks.items()}
    dimensions={k:v.shape[1] for k,v in flat.items()};energies={k:float((v*v).sum()) for k,v in flat.items()}
    matrices=dict(flat)
    matrices['raw_concat']=np.concatenate(list(flat.values()),axis=1)
    matrices['per_feature']=np.concatenate([v/np.sqrt(v.shape[1]) for v in flat.values()],axis=1)
    matrices['equal_block_energy']=np.concatenate([v/np.sqrt(energies[k]) if energies[k]>0 else v for k,v in flat.items()],axis=1)
    # Primary follows the user's concatenation, including z_ii twice; this is sensitivity only.
    matrices['deduplicated_diagonal']=np.concatenate([flat['s_site'],flat['z_row'],np.delete(blocks['z_col'],position,axis=1).reshape(19,-1)],axis=1)
    spectra={name:{kind:hard_response_spectrum(x,centered=kind=='mutant_centered')
              for kind in ['wt_anchored','mutant_centered']} for name,x in matrices.items()}
    raw=matrices['raw_concat'];mean=raw.mean(0)
    return dict(dimensions=dimensions,block_energy=energies,
        mutant_mean_energy_fraction=float(19*(mean*mean).sum()/(raw*raw).sum()) if (raw*raw).sum()>0 else None,
        per_mutation_response_norm=np.linalg.norm(raw,axis=1).tolist(),
        pair_row_col_relative_difference=float(np.linalg.norm(flat['z_row']-flat['z_col'])/max(np.linalg.norm(flat['z_row']),1e-30)),
        spectra=spectra)
