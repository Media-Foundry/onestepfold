"""Offline audit and descriptive response-scale supplement; no model inference.

The normalized distance-response diagnostic supplements (does not replace) the
locked fidelity/ranking endpoints. All variants use the same full hard outputs.
"""
import argparse
import gzip
import json
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.functional_response_rank import reconstruct_local_responses
from fastglycan.scaling_metrics import lddt_observed


def audit_functional_response_rank(root, prior=None):
    lock=json.load(open(root/'lock.json'))
    with gzip.open(root/'report.json.gz','rt') as f:report=json.load(f)
    assert report['complete'] and report['lock_sha256']==sha256(root/'lock.json')
    ranks=lock['ranks'];aa=lock['aa'];seeds=lock['seeds'];by_parent={pi:wi for wi,pis in enumerate(lock['assignments']) for pi in pis}
    records=[];hashes=[];worst_svd=0.;worst_svd_ulp=0.;worst_lddt=0.;worst_rank=0.;n=0
    for site in report['sites']:
        pi,pos=site['parent_index'],site['position'];wi=aa.index(lock['rows'][pi]['sequence'][pos]);out=root/f'worker_{by_parent[pi]}'
        wt=np.load(out/f'p{pi}_wt_coordinates.npz')['coordinates']
        inventory=dict(np.load(out/f'p{pi}_wt_inventory.npz'));ca=inventory['atom_names']=='CA'
        assert np.array_equal(inventory['residue_ids'][ca],np.arange(1,ca.sum()+1))
        i,j=np.triu_indices(ca.sum(),3)
        wd=np.linalg.norm(wt[:,ca][:,i]-wt[:,ca][:,j],axis=-1)
        distances=[];tasks=[]
        for ai,letter in enumerate(aa):
            if ai==wi:
                tasks.append(np.array([[next(r['task'] for r in site['outputs'] if r['aa']==letter and r['rank']==k and r['noise']==seed) for seed in seeds] for k in [-1]+ranks]))
                continue
            label=f'p{pi}_s{pos+1}_{letter}';file=out/f'{label}_coordinates.npz';values=np.load(file)['coordinates'];inv=dict(np.load(out/f'{label}_inventory.npz'));a=inv['atom_names']=='CA'
            assert np.array_equal(inv['residue_ids'][a],np.arange(1,a.sum()+1))
            expected=next(x for w in report['workers'] for p in w['parents'] if p['parent_index']==pi for s in p['sites'] if s['position']==pos for x in s['mutants'] if x['aa']==letter)
            digest=sha256(file);assert digest==expected['coordinate_sha256'];hashes.append(dict(path=str(file.relative_to(root)),sha256=digest,bytes=file.stat().st_size))
            xyz=values[:,:,a];distances.append(np.linalg.norm(xyz[:,:,i]-xyz[:,:,j],axis=-1))
            tasks.append(np.array([[next(r['task'] for r in site['outputs'] if r['aa']==letter and r['rank']==k and r['noise']==seed) for seed in seeds] for k in [-1]+ranks]))
            if ai==next(aidx for aidx in range(20) if aidx!=wi):
                for ki,k in enumerate([-1]+ranks):
                    for ni,seed in enumerate(seeds):
                        check=lddt_observed(values[ki,ni],values[0,ni],inv['residue_ids'])['score']
                        saved=next(r['fidelity']['all_atom_lddt'] for r in site['outputs'] if r['aa']==letter and r['rank']==k and r['noise']==seed)
                        worst_lddt=max(worst_lddt,abs(check-saved));n+=1
        tasks=np.array(tasks).transpose(1,2,0)
        for ki,k in enumerate(ranks,1):
            for ni,seed in enumerate(seeds):
                for included in [False,True]:
                    ids=np.arange(20) if included else np.delete(np.arange(20),wi)
                    calc=float(spearmanr(tasks[0,ni,ids],tasks[ki,ni,ids]).statistic)
                    saved=next(r for r in site['ranking'] if r['rank']==k and r['noise']==seed and r['includes_wt']==included)
                    if saved['spearman'] is not None:worst_rank=max(worst_rank,abs(calc-saved['spearman']))
                    top=np.argsort(tasks[ki,ni,ids],kind='stable');truth=tasks[0,ni,ids]
                    assert abs(float(truth[top[0]]-truth.min())-saved['top1_regret'])<1e-12
        # [19, rank, noise, nonlocal CA pairs], always on common backbone identities.
        d=np.array(distances);reference=d[:,0]-wd[None]
        for ki,k in enumerate(ranks,1):
            pred=d[:,ki]-wd[None]
            for ni,seed in enumerate(seeds):
                true=reference[:,ni];approx=pred[:,ni];error=approx-true
                centered_true=true-true.mean(0);centered_approx=approx-approx.mean(0)
                den=float(np.linalg.norm(true));cden=float(np.linalg.norm(centered_true))
                records.append(dict(parent_index=pi,position=pos,rank=k,noise=seed,
                    exact_response_rms=float(np.sqrt(np.mean(true**2))),
                    approximation_error_rms=float(np.sqrt(np.mean(error**2))),
                    relative_response_l2_error=float(np.linalg.norm(error)/den) if den>1e-12 else None,
                    centered_AA_response_l2_error=float(np.linalg.norm(centered_approx-centered_true)/cden) if cden>1e-12 else None))
        if prior is not None:
            endpoint=lock['endpoints'][f'{pi}:{pos}'];old=prior/Path(endpoint['path']).parent.name/Path(endpoint['path']).name
            assert sha256(old)==endpoint['sha256'];e=dict(np.load(old));reconstructed,_=reconstruct_local_responses(e,wi,ranks)
            x=np.concatenate([e[key].reshape(20,-1).astype(float) for key in ['s_site','z_row','z_col']],1);ids=np.delete(np.arange(20),wi)
            mean=x[ids].mean(0);u,s,v=np.linalg.svd(x[ids]-mean,full_matrices=False)
            for k in ranks:
                actual=np.concatenate([reconstructed[k][key].reshape(20,-1) for key in ['s_site','z_row','z_col']],1)
                expected=mean+(u[:,:k]*s[:k])@v[:k]
                error=np.abs(actual[ids]-expected)
                worst_svd=max(worst_svd,float(error.max()))
                worst_svd_ulp=max(worst_svd_ulp,float(np.max(error/np.maximum(1e-8,np.abs(np.spacing(expected.astype(np.float32)))))))
    assert len(hashes)==950 and n==1100 and worst_lddt<1e-12 and worst_rank<1e-12
    if prior is not None:assert worst_svd_ulp<=1.01
    summary={}
    for k in ranks:
        part=[r for r in records if r['rank']==k]
        summary[str(k)]={key:float(np.mean([r[key] for r in part if r[key] is not None])) for key in ['exact_response_rms','approximation_error_rms','relative_response_l2_error','centered_AA_response_l2_error']}
    write_json(root/'offline_audit.json',dict(complete=True,coordinates_hashed=950,independent_lddt_comparisons=n,
        max_lddt_difference=worst_lddt,max_spearman_difference=worst_rank,direct_svd_float32_max_error=worst_svd if prior is not None else None,
        direct_svd_max_error_ulps_or_1e8_floor=worst_svd_ulp if prior is not None else None,
        response_scale_supplement=dict(role='descriptive supplemental analysis; not a new success threshold',summary=summary,records=records)))
    write_json(root/'coordinate_manifest.json',hashes)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--prior',type=Path);a=p.parse_args();audit_functional_response_rank(a.root,a.prior)
