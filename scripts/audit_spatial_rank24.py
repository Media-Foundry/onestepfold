"""Independent CPU spatial factorization and saved-coordinate audits."""
import argparse,gzip,json,time
from pathlib import Path
import numpy as np
import torch
from scipy.stats import spearmanr
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.scaling_metrics import lddt_observed


def audit_rank24_basis(root,index):
    torch.set_num_threads(1);start=time.monotonic();lock=json.load(open(root/'lock.json'));worker=json.load(open(root/f'worker_{index}/report.json'));assert worker['complete'];states=Path(lock['states']);results=[]
    hashes={f['path']:f['sha256'] for f in lock['conditioning_manifest']}
    def load(label):
        p=states/f'worker_{index}/{label}_conditioning.pt';assert sha256(p)==hashes[str(p.relative_to(states))]
        return torch.load(p,map_location='cpu',weights_only=False)['conditioning'][2].numpy()
    for parent in worker['parents']:
        pi=parent['parent_index'];wt=load(f'p{pi}_wt')
        for site in parent['sites']:
            m=next(m for m in site['mutants'] if 'audit_file' in m);target=load(m['label']);d=target.astype(np.float64)-wt.astype(np.float64);L,_,C=d.shape
            path=root/f'worker_{index}'/m['audit_file'];assert sha256(path)==m['audit_sha256'];saved=torch.load(path,map_location='cpu',weights_only=False)
            dc=d.transpose(2,0,1);u,s,v=np.linalg.svd(dc,full_matrices=False)
            # Matricizations independently build left/right covariance matrices.
            dl=d.reshape(L,-1);dr=d.transpose(1,0,2).reshape(L,-1)
            left=np.linalg.eigh(dl@dl.T)[1][:,::-1];right=np.linalg.eigh(dr@dr.T)[1][:,::-1];energy=float(np.sum(d*d));errors=[]
            for row in m['evidence']['rows']:
                rank=row['rank'];r=L if rank=='full' else min(rank,L)
                if row['variant']=='channel':
                    kept=float(np.sum(s[:,:r]**2));x=((u[:,:,:r]*s[:,None,:r])@v[:,:r]).transpose(1,2,0)
                else:
                    core=np.einsum('ir,ijc,js->rsc',left[:,:r],d,right[:,:r],optimize=True)
                    kept=float(np.sum(core*core));x=np.einsum('ir,rsc,js->ijc',left[:,:r],core,right[:,:r],optimize=True)
                ee=abs(kept/energy-row['energy_retained']);assert ee<1e-9
                rec_error=0.
                if rank in (24,'full'):
                    ref=saved[f'{row["variant"]}_{rank}'].numpy();rec_error=float(np.max(np.abs((wt.astype(np.float64)+x).astype(wt.dtype)-ref)));assert rec_error<2e-5,(m['label'],row['variant'],rank,rec_error)
                errors.append(dict(variant=row['variant'],rank=rank,energy_error=ee,projection_max_error=rec_error))
            results.append(dict(parent_index=pi,position=site['position'],aa=m['aa'],errors=errors))
    write_json(root/f'basis_audit_{index}.json',dict(complete=True,sites=results,seconds=time.monotonic()-start,method='NumPy CPU FP64 channel SVD / matricization HOSVD, R24/full, first nonWT AA at each site'))


def audit_rank24_outputs(root,prior):
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
            if ai==wi:assert co.ndim==3 and np.array_equal(co,oldco)
            else:assert np.array_equal(co[0],oldco[0]) and np.array_equal(co[1],oldco[1])
            if rel not in seen:manifest.append(dict(path=rel,sha256=sha256(root/rel),bytes=(root/rel).stat().st_size));seen.add(rel)
            for arm,oldarm in [('exact','exact'),('baseline','baseline')]:
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
    assert len(manifest)==960 and exact_checks==4000 and lddt_checks==100*len(arms) and rank_checks==400*(len(arms)-1)
    assert worst_lddt<1e-12 and worst_rho<1e-12
    write_json(root/'coordinate_manifest.json',manifest)
    write_json(root/'offline_output_audit.json',dict(complete=True,coordinate_packets=len(manifest),reference_task_geometry_checks=exact_checks,
        independent_lddt_checks=lddt_checks,max_lddt_difference=worst_lddt,rank_checks=rank_checks,max_spearman_difference=worst_rho))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--mode',choices=['basis','outputs'],required=True);p.add_argument('--index',type=int,default=0);p.add_argument('--prior',type=Path);a=p.parse_args()
    if a.mode=='basis':audit_rank24_basis(a.root,a.index)
    else:audit_rank24_outputs(a.root,a.prior)
