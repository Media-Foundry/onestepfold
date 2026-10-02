"""Offline archive, exact-reference and ranking audit for six conditioning swaps."""
import argparse
import gzip
import json
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
from scipy.spatial.distance import pdist
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.scaling_metrics import lddt_observed
from fastglycan.adapter_supervision import build_adapter_supervision


def audit_conditioning_swaps(root,prior):
    lock=json.load(open(root/'lock.json'))
    with gzip.open(root/'report.json.gz','rt') as f:report=json.load(f)
    with gzip.open(prior/'report.json.gz','rt') as f:old=json.load(f)
    assert report['complete'];workers={pi:wi for wi,pis in enumerate(lock['assignments']) for pi in pis};arms=lock['arms'];manifest=[];worst_lddt=0.;worst_rho=0.;exact_metrics=0;lddt_checks=0;geometry_checks=0;seen=set()
    for site in report['sites']:
        pi,pos=site['parent_index'],site['position'];wi=lock['aa'].index(lock['rows'][pi]['sequence'][pos]);worker=workers[pi]
        oldsite=next(s for s in old['sites'] if s['parent_index']==pi and s['position']==pos)
        tasks=np.array([[[next(r['task'] for r in site['outputs'] if r['arm']==arm and r['noise']==seed and r['aa']==aa) for aa in lock['aa']] for seed in lock['seeds']] for arm in arms])
        for ki,arm in enumerate(arms[1:],1):
            for ni,seed in enumerate(lock['seeds']):
                for included in [False,True]:
                    ids=np.arange(20) if included else np.delete(np.arange(20),wi);rho=float(spearmanr(tasks[0,ni,ids],tasks[ki,ni,ids]).statistic)
                    r=next(r for r in site['ranking'] if r['arm']==arm and r['noise']==seed and r['includes_wt']==included)
                    if r['spearman'] is None:assert np.isnan(rho)
                    else:worst_rho=max(worst_rho,abs(rho-r['spearman']))
                    order=np.argsort(tasks[ki,ni,ids],kind='stable');truth=tasks[0,ni,ids];assert abs(float(truth[order[0]]-truth.min())-r['top1_regret'])<1e-12
        for ai,aa in enumerate(lock['aa']):
            label=f'p{pi}_wt' if ai==wi else f'p{pi}_s{pos+1}_{aa}';rel=f'worker_{worker}/{label}_coordinates.npz'
            co=np.load(root/rel)['coordinates'];oc=np.load(prior/rel)['coordinates'];reference=oc if ai==wi else oc[0]
            assert np.array_equal(co[0],reference)
            if rel not in seen:manifest.append(dict(path=rel,sha256=sha256(root/rel),bytes=(root/rel).stat().st_size));seen.add(rel)
            for seed in lock['seeds']:
                r=next(r for r in site['outputs'] if r['arm']=='exact' and r['noise']==seed and r['aa']==aa)
                o=next(r for r in oldsite['outputs'] if r['rank']==-1 and r['noise']==seed and r['aa']==aa)
                assert r['task']==o['task'] and r['geometry']==o['geometry'];exact_metrics+=1
            first=next(j for j in range(20) if j!=wi)
            if ai==first:
                inv=dict(np.load(root/f'worker_{worker}/{label}_inventory.npz'))
                for ki,arm in enumerate(arms):
                    for ni,seed in enumerate(lock['seeds']):
                        score=lddt_observed(co[ki,ni],co[0,ni],inv['residue_ids'])['score'];r=next(r for r in site['outputs'] if r['arm']==arm and r['noise']==seed and r['aa']==aa)
                        worst_lddt=max(worst_lddt,abs(score-r['fidelity']['all_atom_lddt']));lddt_checks+=1
                if pos==lock['rows'][pi]['positions'][0]:
                    n=co.shape[-2];labels=build_adapter_supervision(dict(inv,coordinates=co[0,0],mask=np.ones(n,bool)),inv['bonds'],str(inv['sequence']))
                    i,j=np.triu_indices(n,1);allowed=~np.isin(i*n+j,labels['excluded']);a,b,c,d=labels['centres'].numpy().T
                    for ki,arm in enumerate(arms):
                        x=co[ki,0].astype(float);severe=int(((pdist(x)<1)&allowed).sum());v=np.linalg.det(np.stack([x[b]-x[a],x[c]-x[a],x[d]-x[a]],1));wrong=int((v*labels['volumes'].numpy()<=0).sum())
                        saved=next(r['geometry'] for r in site['outputs'] if r['arm']==arm and r['noise']==lock['seeds'][0] and r['aa']==aa)
                        assert severe==saved['severe_pairs'] and wrong==saved['checked_chirality_wrong'];geometry_checks+=1
    assert len(manifest)==960 and exact_metrics==2000 and lddt_checks==600 and geometry_checks==60
    assert worst_lddt<1e-12 and worst_rho<1e-12
    write_json(root/'coordinate_manifest.json',manifest)
    write_json(root/'offline_audit.json',dict(complete=True,coordinate_packets_exact_replayed_and_hashed=len(manifest),exact_task_geometry_comparisons=exact_metrics,
        independent_lddt_comparisons=lddt_checks,max_lddt_difference=worst_lddt,max_spearman_difference=worst_rho,independent_allpair_determinant_geometry_comparisons=geometry_checks))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--prior',type=Path,required=True);a=p.parse_args();audit_conditioning_swaps(a.root,a.prior)
