"""Source-anchored, masked experimental backbone evaluation for editing probes."""
import numpy as np
from .scaling_metrics import lddt_observed


def fit_ca_frame(coordinates, reference, support):
    x=np.asarray(coordinates,dtype=float);y=np.asarray(reference,dtype=float);m=np.asarray(support,dtype=bool)
    if x.shape!=y.shape or x.ndim!=2 or x.shape[-1]!=3 or m.sum()<3:
        raise ValueError('invalid common frame support')
    a=x[m].mean(0);b=y[m].mean(0)
    u,_,vt=np.linalg.svd((x[m]-a).T@(y[m]-b));r=u@np.diag([1.,1.,np.linalg.det(u@vt)])@vt
    return (x-a)@r+b


def edit_backbone_metrics(prediction, source, target, local):
    """All comparisons use identical nonlocal support, never local target alignment."""
    source=np.asarray(source,dtype=float);target=np.asarray(target,dtype=float);local=np.asarray(local,dtype=bool)
    pred=np.asarray(prediction,dtype=float);assert source.shape==target.shape==pred.shape
    if not np.isfinite(pred).all():raise ValueError('nonfinite backbone')
    t=fit_ca_frame(target,source,~local);p=fit_ca_frame(pred,source,~local)
    def rms(v):return float(np.sqrt(np.mean(np.sum(v*v,axis=-1))))
    needed=t-source;response=p-source;den=np.linalg.norm(needed[local])*np.linalg.norm(response[local])
    indices=np.arange(len(source));eligible=np.abs(indices[:,None]-indices[None,:])>2
    eligible=np.triu(eligible,1)
    def contacts(x):return np.linalg.norm(x[:,None]-x[None,:],axis=-1)<8.
    sc,tc,pc=map(contacts,[source,target,pred]);expected=(tc!=sc)&eligible;actual=(pc!=sc)&eligible
    # Signed gain/loss identity must match, not just whether the pair changed.
    correct=expected&actual&(pc==tc)
    return dict(ca_lddt=lddt_observed(pred,target,indices)['score'],
        ca_aligned_rmsd=rms(fit_ca_frame(pred,target,np.ones(len(source),dtype=bool))-target),
        local_target_rmsd=rms(p[local]-t[local]),nonlocal_target_rmsd=rms(p[~local]-t[~local]),
        nonlocal_motion=rms(response[~local]),local_motion=rms(response[local]),
        experimental_local_change=rms(needed[local]),experimental_nonlocal_change=rms(needed[~local]),
        local_response_cosine=float((needed[local]*response[local]).sum()/den) if den>1e-10 else None,
        local_residues=int(local.sum()),nonlocal_residues=int((~local).sum()),
        needed_contact_changes=int(expected.sum()),predicted_contact_changes=int(actual.sum()),
        correctly_reconstructed_contact_changes=int(correct.sum()),
        target_contact_errors=int(((pc!=tc)&eligible).sum()))
