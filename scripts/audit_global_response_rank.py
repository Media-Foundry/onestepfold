"""Independent chunked CPU Gram audit and archived global-rank metric checks."""
import argparse
import gzip
import json
from pathlib import Path
import numpy as np
import torch
from scipy.stats import spearmanr
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.scaling_metrics import lddt_observed


def audit_global_basis(root,index):
    torch.set_num_threads(1);lock=json.load(open(root/'lock.json'));worker=json.load(open(root/f'worker_{index}/report.json'));assert worker['complete'];states=Path(lock['states']);rows=[]
    for parent in worker['parents']:
        pi=parent['parent_index'];wt=torch.load(states/f'worker_{index}/p{pi}_wt_conditioning.pt',map_location='cpu',weights_only=False)['conditioning']
        for site in parent['sites']:
            pos=site['position'];packets=[torch.load(states/f'worker_{index}/{m["label"]}_conditioning.pt',map_location='cpu',weights_only=False)['conditioning'] for m in site['mutants']]
            grams={};energy={};errors={}
            for bi,key in [(1,'s'),(2,'z')]:
                source=[p[bi].reshape(-1).numpy() for p in packets];base=wt[bi].reshape(-1).numpy();g=np.zeros((19,19));e=0.
                for start in range(0,len(base),65536):
                    values=np.stack([v[start:start+65536] for v in source]).astype(np.float64)-base[start:start+65536].astype(np.float64)
                    e+=float(np.sum(values*values));values-=values.mean(0);g+=values@values.T
                grams[key]=g;energy[key]=e;reported=np.array(site['evidence']['centered_gram'][key]);expected=site['evidence']['energies_before_centering'][key]
                errors[key]=dict(gram_relative_l2=float(np.linalg.norm(g-reported)/max(np.linalg.norm(g),1e-30)),energy_relative=abs(e-expected)/max(e,1e-30))
                assert errors[key]['gram_relative_l2']<1e-10 and errors[key]['energy_relative']<1e-10
            spectra_errors={}
            metrics=dict(raw=grams['s']+grams['z'],balanced=sum(grams[k]/energy[k] if energy[k]>0 else np.zeros((19,19)) for k in ['s','z']),s=grams['s'],z=grams['z'])
            for metric,g in metrics.items():
                val,v=np.linalg.eigh((g+g.T)*.5);val=np.maximum(val[::-1],0);v=v[:,::-1];expected=site['evidence']['spectra'][metric]['cumulative_energy']
                if expected is not None:
                    error=float(np.max(np.abs(val.cumsum()/val.sum()-expected)));assert error<1e-9
                else:error=0.
                projection_error=0.
                for k in lock['ranks']:
                    q=v[:,:k]@v[:,:k].T;p=np.array(site['evidence']['coefficients'][metric][str(k)]);d=p-q
                    weighted=max(0.,float(np.trace(d@g@d.T)))/max(float(np.trace(g)),1e-30);projection_error=max(projection_error,weighted)
                assert projection_error<1e-9
                spectra_errors[metric]=dict(max_cumulative_error=error,max_projected_energy_difference=projection_error)
            rows.append(dict(parent_index=pi,position=pos,blocks=errors,spectra=spectra_errors))
    write_json(root/f'basis_audit_{index}.json',dict(complete=True,sites=rows,method='independent CPU FP64 chunked response Gram /numpy eigh vs GPU full Gram'))


def audit_global_outputs(root,prior):
    lock=json.load(open(root/'lock.json'))
    with gzip.open(root/'report.json.gz','rt') as f:report=json.load(f)
    with gzip.open(prior/'report.json.gz','rt') as f:old=json.load(f)
    owner={pi:i for i,rows in enumerate(lock['assignments']) for pi in rows};arms=lock['arms'];manifest=[];seen=set();exact_checks=0;lddt_checks=0;worst_lddt=0.;worst_rho=0.;rank_checks=0
    for site in report['sites']:
        pi,pos=site['parent_index'],site['position'];wi=lock['aa'].index(lock['rows'][pi]['sequence'][pos]);work=f'worker_{owner[pi]}'
        oldsite=next(s for s in old['sites'] if s['parent_index']==pi and s['position']==pos)
        tasks=np.array([[[next(r['task'] for r in site['outputs'] if r['arm']==arm and r['noise']==seed and r['aa']==aa) for aa in lock['aa']] for seed in lock['seeds']] for arm in arms])
        for ki,arm in enumerate(arms[1:],1):
            for ni,seed in enumerate(lock['seeds']):
                for ri,ref in [(0,'exact'),(1,'baseline')]:
                    for included in [False,True]:
                        ids=np.arange(20) if included else np.delete(np.arange(20),wi);rho=float(spearmanr(tasks[ri,ni,ids],tasks[ki,ni,ids]).statistic)
                        saved=next(r for r in site['ranking'] if r['arm']==arm and r['noise']==seed and r['reference']==ref and r['includes_wt']==included)
                        if saved['spearman'] is None:assert np.isnan(rho)
                        else:worst_rho=max(worst_rho,abs(rho-saved['spearman']))
                        pick=np.argsort(tasks[ki,ni,ids],kind='stable')[0];truth=tasks[ri,ni,ids];assert abs(float(truth[pick]-truth.min())-saved['top1_regret'])<1e-12;rank_checks+=1
        for ai,aa in enumerate(lock['aa']):
            label=f'p{pi}_wt' if ai==wi else f'p{pi}_s{pos+1}_{aa}';rel=f'{work}/{label}_coordinates.npz';co=np.load(root/rel)['coordinates'];oldco=np.load(prior/rel)['coordinates']
            if ai==wi:assert np.array_equal(co,oldco[0]) and np.array_equal(co,oldco[3])
            else:assert np.array_equal(co[0],oldco[0]) and np.array_equal(co[1],oldco[3])
            if rel not in seen:manifest.append(dict(path=rel,sha256=sha256(root/rel),bytes=(root/rel).stat().st_size));seen.add(rel)
            for arm,oldarm in [('exact','exact'),('baseline','target_trunk_only')]:
                for seed in lock['seeds']:
                    r=next(r for r in site['outputs'] if r['arm']==arm and r['noise']==seed and r['aa']==aa);o=next(r for r in oldsite['outputs'] if r['arm']==oldarm and r['noise']==seed and r['aa']==aa)
                    assert r['task']==o['task'] and r['geometry']==o['geometry'];exact_checks+=1
            if ai==next(j for j in range(20) if j!=wi):
                inv=dict(np.load(root/f'{work}/{label}_inventory.npz'))
                # All metrics and all requested K on one fixed non-WT endpoint/site.
                for ki,arm in enumerate(arms):
                    for ri,group in [(0,'fidelity'),(1,'compression_fidelity')]:
                        value=lddt_observed(co[ki,0],co[ri,0],inv['residue_ids'])['score'];saved=next(r[group]['all_atom_lddt'] for r in site['outputs'] if r['arm']==arm and r['noise']==lock['seeds'][0] and r['aa']==aa)
                        worst_lddt=max(worst_lddt,abs(value-saved));lddt_checks+=1
    assert len(manifest)==960 and exact_checks==4000 and lddt_checks==5200 and rank_checks==20400
    assert worst_lddt<1e-12 and worst_rho<1e-12
    write_json(root/'coordinate_manifest.json',manifest)
    write_json(root/'offline_output_audit.json',dict(complete=True,coordinate_packets=len(manifest),reference_task_geometry_checks=exact_checks,
        independent_lddt_checks=lddt_checks,max_lddt_difference=worst_lddt,rank_checks=rank_checks,max_spearman_difference=worst_rho))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--mode',choices=['basis','outputs'],required=True);p.add_argument('--index',type=int,default=0);p.add_argument('--prior',type=Path);a=p.parse_args()
    if a.mode=='basis':audit_global_basis(a.root,a.index)
    else:audit_global_outputs(a.root,a.prior)
