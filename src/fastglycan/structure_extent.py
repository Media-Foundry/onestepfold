"""Describe local/global CA errors without changing folding quality gates."""
import numpy as np


def structure_extent_diagnostics(prediction, target, residue_ids):
    """Use observed CA coordinates; all pair bands are defined by experimental GT.

    Fragment fits are descriptive independent 32-residue fits, not a repaired
    structure. Top-5% exclusion keeps the original whole-chain alignment.
    """
    x=np.asarray(prediction,dtype=np.float64);y=np.asarray(target,dtype=np.float64)
    ids=np.asarray(residue_ids)
    if x.shape!=y.shape or x.ndim!=2 or x.shape[1]!=3 or len(x)<3:
        raise ValueError('need matching N x 3 CA arrays with N >= 3')
    if ids.shape!=(len(x),) or not np.issubdtype(ids.dtype,np.integer) or np.any(np.diff(ids)<=0):
        raise ValueError('residue ids must be unique increasing integers')
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError('coordinates must be finite')
    a=x-x.mean(0);b=y-y.mean(0)
    u,_,vt=np.linalg.svd(a.T@b)
    rotation=u@np.diag([1.,1.,np.linalg.det(u@vt)])@vt
    squared=np.sum((a@rotation-b)**2,axis=1)
    residual=np.sqrt(squared);n=len(x);k=max(1,int(np.ceil(.05*n)))
    order=np.argsort(squared,kind='stable');total=float(squared.sum())
    # This is a descriptive zero-signal convention, not a derivative gate.
    tail_fraction=float(squared[order[-k:]].sum()/total) if total>1e-20 else None
    fragment_sse=0.;fragment_n=0;fragments=[]
    for start in range(0,n,32):
        stop=min(start+32,n)
        if stop-start<3:continue
        if not np.all(np.diff(ids[start:stop])==1):continue
        aa=x[start:stop]-x[start:stop].mean(0);bb=y[start:stop]-y[start:stop].mean(0)
        uu,_,vv=np.linalg.svd(aa.T@bb);rr=uu@np.diag([1.,1.,np.linalg.det(uu@vv)])@vv
        ss=float(np.sum((aa@rr-bb)**2));fragment_sse+=ss;fragment_n+=stop-start
        fragments.append(dict(first=int(ids[start]),last=int(ids[stop-1]),rmsd=float(np.sqrt(ss/(stop-start)))))
    i,j=np.triu_indices(n,1);reference=np.linalg.norm(y[i]-y[j],axis=1)
    measured=np.linalg.norm(x[i]-x[j],axis=1);difference=measured-reference
    nonlocal_pair=np.abs(ids[i]-ids[j])>=24
    bands={}
    for name,keep in [('all',np.ones(len(i),dtype=bool)),('seq24_gt_lt15',nonlocal_pair&(reference<15)),
                      ('seq24_gt_15_30',nonlocal_pair&(reference>=15)&(reference<30)),
                      ('seq24_gt_ge30',nonlocal_pair&(reference>=30))]:
        z=difference[keep]
        bands[name]=dict(pairs=int(keep.sum()),mae=float(np.abs(z).mean()) if len(z) else None,
                         rmse=float(np.sqrt(np.mean(z*z))) if len(z) else None,
                         signed_mean=float(z.mean()) if len(z) else None)
    rgx=float(np.sqrt(np.mean(np.sum(a*a,axis=1))));rgy=float(np.sqrt(np.mean(np.sum(b*b,axis=1))))
    return dict(ca_count=n,ca_rmsd=float(np.sqrt(squared.mean())),residual_median=float(np.median(residual)),
                residual_p90=float(np.quantile(residual,.9)),residual_max=float(residual.max()),
                fraction_gt2=float(np.mean(residual>2)),fraction_gt5=float(np.mean(residual>5)),
                top5_count=k,top5_sse_fraction=tail_fraction,
                remainder95_rmsd_fixed_alignment=float(np.sqrt(squared[order[:-k]].mean())),
                fragment32_rmsd=float(np.sqrt(fragment_sse/fragment_n)) if fragment_n else None,
                fragment32_residues=fragment_n,fragments=fragments,
                prediction_rg=rgx,gt_rg=rgy,rg_ratio=rgx/rgy if rgy>0 else None,
                distance_bands=bands,residue_ids=ids.tolist(),aligned_residual=residual.tolist())
