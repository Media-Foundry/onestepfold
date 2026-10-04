"""Read-only score-objective decomposition; no fitting or label rescaling."""
import numpy as np


def score_decomposition(target, prediction):
    y=np.asarray(target,dtype=np.float64);p=np.asarray(prediction,dtype=np.float64)
    if y.ndim!=1 or y.shape!=p.shape or not np.isfinite(y).all() or not np.isfinite(p).all():
        raise ValueError('finite matching candidate vectors required')
    yc=y-y.mean();pc=p-p.mean();e=p-y
    out=dict(label_energy=float(np.mean(y*y)),mean_energy=float(y.mean()**2),
             centered_energy=float(np.mean(yc*yc)),label_mean=float(y.mean()),
             prediction_mean=float(p.mean()),mse=float(np.mean(e*e)),
             mean_error=float((p.mean()-y.mean())**2),centered_error=float(np.mean((pc-yc)**2)),
             prediction_centered_energy=float(np.mean(pc*pc)))
    assert np.isclose(out['label_energy'],out['mean_energy']+out['centered_energy'],rtol=1e-12,atol=1e-14)
    assert np.isclose(out['mse'],out['mean_error']+out['centered_error'],rtol=1e-12,atol=1e-14)
    return out


def rank_correlation(x,y):
    from scipy.stats import rankdata
    x=rankdata(x);y=rankdata(y)
    if np.ptp(x)==0 or np.ptp(y)==0:return None
    return float(np.corrcoef(x,y)[0,1])


def noise_audit(scores):
    x=np.asarray(scores,dtype=np.float64)
    if x.shape[0]!=4:raise ValueError('two old and two new noises required')
    old=x[:2].mean(0);new=x[2:].mean(0);a=old-old.mean();b=new-new.mean()
    den=np.linalg.norm(a)*np.linalg.norm(b)
    return dict(old_new_rho=rank_correlation(old,new),centered_cosine=float(a@b/den) if den else None,
                centered_noise_mse=float(np.mean((a-b)**2)),
                old_centered_energy=float(np.mean(a*a)),new_centered_energy=float(np.mean(b*b)),
                within_old_disagreement=float(np.mean(((x[0]-x[0].mean())-(x[1]-x[1].mean()))**2)),
                within_new_disagreement=float(np.mean(((x[2]-x[2].mean())-(x[3]-x[3].mean()))**2)),
                old_select_new_regret=float(new[np.argmin(old)]-new.min()))
