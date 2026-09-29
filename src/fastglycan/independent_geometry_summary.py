"""Descriptive summaries of the locked experiment; no new acceptance thresholds."""
import math
import numpy as np
from scipy.spatial import cKDTree

SEEDS=(300007,300017,300023)
QUALITY=('all_atom_lddt','ca_lddt','tm_score_ca_observed','ca_rmsd')


def distribution(values):
    finite=[float(x) for x in values if x is not None and np.isfinite(x)]
    out=dict(total=len(values),available=len(finite),missing=len(values)-len(finite))
    if finite:
        a=np.sort(finite);k=max(1,math.ceil(.05*len(a)))
        out.update(mean=float(a.mean()),median=float(np.median(a)),min=float(a[0]),max=float(a[-1]),p01=float(np.quantile(a,.01)),p05=float(np.quantile(a,.05)),p95=float(np.quantile(a,.95)),p99=float(np.quantile(a,.99)),lower5_mean=float(a[:k].mean()),upper5_mean=float(a[-k:].mean()),tail_count=k)
    return out


def protein_quality(rows,group_ids):
    lookup={(r['group_id'],r['seed']):r for r in rows}
    if len(lookup)!=len(rows):raise ValueError('duplicate protein/noise records')
    proteins=[]
    for g in group_ids:
        row=dict(group_id=g,quality={},paired={})
        for method in ['raw','mean','tail']:
            for metric in QUALITY:
                vals=[lookup.get((g,s),{}).get('quality',{}).get(method,{}).get(metric) for s in SEEDS]
                value=float(np.mean(vals)) if all(v is not None and np.isfinite(v) for v in vals) else None
                row['quality'].setdefault(method,{})[metric]=value
        for method in ['mean','tail']:
            row['paired'][method]={metric:(row['quality'][method][metric]-row['quality']['raw'][metric] if row['quality'][method][metric] is not None and row['quality']['raw'][metric] is not None else None) for metric in QUALITY}
        proteins.append(row)
    summary=dict(proteins=len(group_ids),absolute={},paired={})
    for method in ['raw','mean','tail']:
        summary['absolute'][method]={metric:distribution([x['quality'][method][metric] for x in proteins]) for metric in QUALITY}
    for method in ['mean','tail']:
        summary['paired'][method]={}
        for metric in QUALITY:
            vals=[x['paired'][method][metric] for x in proteins];d=distribution(vals)
            if d['available']==len(group_ids) and group_ids:
                a=np.asarray(vals);rng=np.random.default_rng(20260929);means=a[rng.integers(0,len(a),size=(10000,len(a)))].mean(1)
                d['bootstrap95']=np.quantile(means,[.025,.975]).tolist()
            else:d['bootstrap95']=None
            d['below_minus005']=sum(v is not None and v<-.05 for v in vals)
            d['above_plus005']=sum(v is not None and v>.05 for v in vals)
            summary['paired'][method][metric]=d
    return proteins,summary


def geometry_transitions(rows):
    result={}
    for method in ['mean','tail']:
        counts=dict(instances=len(rows),raw_pass=0,raw_fail=0,raw_unknown=0,repaired_pass=0,repaired_fail=0,repaired_unknown=0,raw_pass_retained=0,raw_pass_regressed=0,raw_fail_repaired=0,raw_fail_still_failed=0,comparison_unknown=0)
        by_protein={}
        for row in rows:
            before=row.get('raw_joint_pass');after=row.get(method+'_joint_pass')
            counts['raw_unknown' if before is None else 'raw_pass' if before else 'raw_fail']+=1
            counts['repaired_unknown' if after is None else 'repaired_pass' if after else 'repaired_fail']+=1
            by_protein.setdefault(row['group_id'],[]).append(after)
            if before is None or after is None:counts['comparison_unknown']+=1
            elif before:counts['raw_pass_retained' if after else 'raw_pass_regressed']+=1
            else:counts['raw_fail_repaired' if after else 'raw_fail_still_failed']+=1
        counts['all3_proteins_pass']=sum(len(v)==3 and all(x is True for x in v) for v in by_protein.values())
        counts['raw_pass_retention_rate']=counts['raw_pass_retained']/counts['raw_pass'] if counts['raw_pass'] else None
        counts['raw_fail_repair_rate']=counts['raw_fail_repaired']/counts['raw_fail'] if counts['raw_fail'] else None
        result[method]=counts
    return result


def atom_lddt(predicted,target,residues):
    """Same inter-residue, per-observed-atom definition as frozen lddt_observed."""
    x=np.asarray(predicted,dtype=float);y=np.asarray(target,dtype=float);res=np.asarray(residues)
    pairs=cKDTree(y).query_pairs(15.,output_type='ndarray')
    reference=np.linalg.norm(y[pairs[:,0]]-y[pairs[:,1]],axis=-1)
    keep=(reference<15.)&(res[pairs[:,0]]!=res[pairs[:,1]])
    pairs=pairs[keep];reference=reference[keep]
    error=np.abs(np.linalg.norm(x[pairs[:,0]]-x[pairs[:,1]],axis=-1)-reference)
    scores=(error[:,None]<np.array([.5,1,2,4])).mean(1)
    counts=np.bincount(pairs.ravel(),minlength=len(x));totals=np.bincount(pairs.ravel(),weights=np.repeat(scores,2),minlength=len(x))
    result=np.full(len(x),np.nan);valid=counts>0;result[valid]=totals[valid]/counts[valid]
    return result


def penetration_distribution(coordinates,pairs,radii):
    """Streaming exact permitted-pair population, including count of zero depth."""
    x=np.asarray(coordinates,dtype=float);pairs=np.asarray(pairs);radii=np.asarray(radii,dtype=float);positive=[];zero=0;severe=0;minimum=float('inf')
    for start in range(0,len(pairs),65536):
        ij=pairs[start:start+65536];d=np.linalg.norm(x[ij[:,0]]-x[ij[:,1]],axis=-1);depth=radii[ij[:,0]]+radii[ij[:,1]]-d
        positive.append(depth[depth>0]);zero+=int((depth<=0).sum());severe+=int((d<1.).sum());minimum=min(minimum,float(d.min()))
    values=np.concatenate(positive) if positive else np.empty(0)
    edges=np.array([0,.25,.5,1,1.5,1.9,2,2.5,3,np.inf]);counts=np.histogram(values,bins=edges)[0]
    return dict(permitted_pairs=len(pairs),zero_depth_pairs=zero,positive_depth_pairs=len(values),severe_distance_below1=severe,minimum_distance=minimum if len(pairs) else None,positive_depth_distribution=distribution(values.tolist()),positive_histogram_edges=[float(e) if np.isfinite(e) else 'inf' for e in edges],positive_histogram_counts=counts.tolist())
