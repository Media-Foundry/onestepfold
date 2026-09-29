"""Fixed-correspondence experimental quality and protein-level continuation screen."""
import numpy as np
from fastglycan.scaling_metrics import lddt_observed


def experimental_quality(coordinates, mapping, sequence):
    from tmtools import tm_align
    x=np.asarray(coordinates,dtype=np.float64).reshape(-1,3);y=np.asarray(mapping['coordinates'],dtype=np.float64)
    mask=np.asarray(mapping['mask'],dtype=bool);res=np.asarray(mapping['residue_ids']);names=np.asarray(mapping['atom_names'])
    if x.shape!=y.shape or not np.isfinite(x).all():raise ValueError('coordinate shape or finite check failed')
    ca=(names=='CA') & mask
    if ca.sum()!=len(sequence):raise ValueError('locked complete backbone contract violated')
    aa=lddt_observed(x[mask],y[mask],res[mask]);cal=lddt_observed(x[ca],y[ca],res[ca])
    a=x[ca]-x[ca].mean(0);b=y[ca]-y[ca].mean(0);u,_,vt=np.linalg.svd(a.T@b);rotation=u@np.diag([1,1,np.linalg.det(u@vt)])@vt
    rms=float(np.sqrt(np.mean(np.sum((a@rotation-b)**2,-1))))
    tm=tm_align(np.ascontiguousarray(x[ca]),np.ascontiguousarray(y[ca]),sequence,sequence,alignment=[sequence,sequence])
    return dict(all_atom_lddt=aa['score'],ca_lddt=cal['score'],ca_rmsd=rms,tm_score_ca_observed=float(tm.tm_norm_chain2),observed_atoms=int(mask.sum()),lddt_details=aa)


def continuation_screen(rows, group_ids):
    """Missing triplets prevent positive quality conclusion; seeds aren't proteins."""
    if len(group_ids)!=32 or len(set(group_ids))!=32:raise ValueError('requires32 locked groups')
    lookup={(x['group_id'],x['seed']):x for x in rows}
    if len(lookup)!=len(rows):raise ValueError('duplicate group/seed')
    seeds=(300007,300017,300023);deltas=[];all3=0;passes=0;regressions=0;missing=[]
    for g in group_ids:
        triplet=[];valid=True;allpass=True
        for s in seeds:
            x=lookup.get((g,s),{});tail=x.get('tail_joint_pass',False);passes+=bool(tail);allpass=allpass and bool(tail)
            regressions+=bool(x.get('raw_joint_pass',False) and not tail)
            try:
                delta=x['quality']['tail']['all_atom_lddt']-x['quality']['raw']['all_atom_lddt']
                if not np.isfinite(delta):raise ValueError('nonfinite')
                triplet.append(delta)
            except (KeyError,TypeError,ValueError):valid=False;missing.append(dict(group_id=g,seed=s))
        all3+=allpass
        if valid:deltas.append(float(np.mean(triplet)))
    geometry=passes>=80 and all3>=24 and regressions==0
    out=dict(instances=96,proteins=32,tail_joint_pass=passes,all3_tail_joint_pass=all3,raw_pass_regressions=regressions,geometry_screen=geometry,missing_quality=missing,quality_screen=False,continuation_screen=False)
    if not missing:
        d=np.asarray(deltas);rng=np.random.default_rng(20260929);means=d[rng.integers(0,32,size=(10000,32))].mean(1);ci=np.quantile(means,[.025,.975]);bad=int((d<-.02).sum())
        quality=bool(d.mean()>=-.005 and ci[0]>=-.01 and bad<=3)
        out.update(mean_protein_lddt_delta=float(d.mean()),bootstrap95=ci.tolist(),proteins_delta_below_minus02=bad,quality_screen=quality,continuation_screen=geometry and quality)
    return out
