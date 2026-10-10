"""Score the fixed normalized arm and retain immutable archived controls."""
import gzip
import json
from pathlib import Path
import time

import numpy as np
import torch

from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.factor_student_data import FactorTeacherStore
from fastglycan.adapter_supervision import build_adapter_supervision
from fastglycan.backbone_sequence_task import backbone_target_pairs, backbone_target_loss
from fastglycan.functional_response_rank import ranking_fidelity, prepare_fidelity_pairs, response_structure_metrics, response_geometry
from fastglycan.reference_editor_metrics import distance_response_summary, summarize_editor_sites, paired_parent_interval
from fastglycan.transport_normalization_audit import read_transport_normalization_lock


def score_transport_normalization(root, shard):
    root=Path(root);lock=read_transport_normalization_lock(root);start=time.monotonic();torch.set_num_threads(1)
    source=Path(lock['trajectory_root']);old=json.loads((source/'trajectory_lock.json').read_text())
    lora=json.loads((Path(old['source'])/'lora_lock.json').read_text());native=Path(lora['source_root'])
    plan=json.loads((native/'plan.json').read_text());old_lock=json.loads((native/'lock.json').read_text())
    assert sha256(native/'plan.json')==old['plan_sha256']
    store=FactorTeacherStore(old_lock['teachers'])
    saved=[]
    for i in range(2):
        p=source/f'scores_{i}.json.gz';assert sha256(p)==lock['score_hashes'][p.name]
        with gzip.open(p,'rt') as f:saved.append(json.load(f))
    old_outputs={(r['site_key'],r['arm'],r['noise'],r['aa']):r for d in saved for r in d['outputs']}
    old_sites={(r['site_key'],r['arm']):r for d in saved for r in d['sites']}
    audit=json.loads((root/f'shard_{shard}.json').read_text());assert audit['complete']
    files={r['label']:r for r in audit['rows']};records=[];outputs=[]
    for site in plan['sites']:
        pi,pos=site['parent_index'],site['position_zero_based']
        if pi%6!=shard:continue
        choices=site['candidates'];sequence=store.rows[pi]['sequence'];gi=store.lock['gt'][str(pi)]
        assert sha256(Path(gi['path']))==gi['sha256'];gt=dict(np.load(gi['path']))
        mask=gt['atom_names']=='CA';y=gt['coordinates'][mask]
        pairs,dist=backbone_target_pairs(y,gt['mask'][mask])
        local=np.linalg.norm(y-y[pos],axis=-1)<=8;local[pos]=True
        ii,jj=np.triu_indices(len(sequence),3)
        wt=store.load(pi);wca=np.flatnonzero(wt['inventory']['atom_names']=='CA')
        reference_dist=np.linalg.norm(wt['coordinates'][:,wca[ii]]-wt['coordinates'][:,wca[jj]],axis=-1)
        tasks=np.zeros((2,19));distances=np.zeros((2,19,len(ii)));exact_dist=np.zeros_like(distances);rows=[]
        exact_tasks=np.asarray(old_sites[site['site_key'],'exact']['tasks'])
        for ai,aa in enumerate(choices):
            label=f'p{pi}_s{pos+1}_{aa}';record=files[label];path=root/record['path']
            assert sha256(path)==record['sha256'];xyz=np.load(path)['coordinates']
            inv=dict(np.load(store.path(pi,label,'inventory.npz')))
            exact=np.load(store.path(pi,label,'coordinates.npz'))['coordinates'][0]
            labels=build_adapter_supervision(dict(inv,coordinates=exact[0],mask=np.ones(len(inv['atom_names']),bool)),
                inv['bonds'],sequence[:pos]+aa+sequence[pos+1:])
            ca=np.flatnonzero(inv['atom_names']=='CA');res=inv['residue_ids']
            assert np.array_equal(res[ca],wt['inventory']['residue_ids'][wca])
            reference_only=np.load(native/'baseline'/f'{label}.npz')['coordinates']
            centers=np.asarray(labels['centres']);volumes0=np.asarray(labels['volumes'])
            for ni,noise in enumerate(store.lock['seeds']):
                x=xyz[ni];assert x.shape==exact[ni].shape and np.isfinite(x).all()
                tasks[ni,ai]=float(backbone_target_loss(torch.tensor(x,dtype=torch.float64),ca,pairs,dist))
                distances[ni,ai]=np.linalg.norm(x[ca[ii]]-x[ca[jj]],axis=-1)
                exact_dist[ni,ai]=np.linalg.norm(exact[ni,ca[ii]]-exact[ni,ca[jj]],axis=-1)
                caches=prepare_fidelity_pairs(exact[ni],res),prepare_fidelity_pairs(exact[ni,ca],res[ca])
                geo=response_geometry(x,labels);ok=geo['zero_severe_strict_checked_chirality']
                a,b,c,d=centers.T;volumes=(np.cross(x[b]-x[a],x[c]-x[a])*(x[d]-x[a])).sum(1)
                row=dict(site_key=site['site_key'],parent=pi,position=pos,label=label,role=site['role_n15'],aa=aa,
                    noise=int(noise),arm='normalized',task=tasks[ni,ai],geometry=geo,
                    fidelity=response_structure_metrics(x,exact[ni],ca,local,caches),signed_volumes=volumes.tolist(),
                    center_residues=res[centers].tolist(),center_atom_names=inv['atom_names'][centers].tolist(),
                    reference_oriented_volume_ratio=(volumes*np.sign(volumes0)/np.maximum(abs(volumes0),1e-12)).tolist())
                for arm in ('exact','cold_c2','wt_progress'):
                    good=old_outputs[site['site_key'],arm,noise,aa]['geometry']['zero_severe_strict_checked_chirality']
                    row[arm+'_pass_to_fail']=bool(good and not ok);row[arm+'_fail_to_pass']=bool(not good and ok)
                good=response_geometry(reference_only[ni],labels)['zero_severe_strict_checked_chirality']
                row['reference_pass_to_fail']=bool(good and not ok);row['reference_fail_to_pass']=bool(not good and ok)
                rows.append(row)
        lr=np.asarray([r['fidelity']['local_ca_rmsd_global_frame'] for r in rows]);selected=int(tasks[0].argmin())
        records.append(dict(site_key=site['site_key'],parent=pi,position=pos,pdb=site['pdb_id'],role=site['role_n15'],
            original_aa=site['original_aa'],arm='normalized',tasks=tasks.tolist(),
            ranking=[ranking_fidelity(exact_tasks[ni],tasks[ni]) for ni in range(2)],
            aggregate_ranking=ranking_fidelity(exact_tasks.mean(0),tasks.mean(0)),old_selected=choices[selected],
            old_select_new_regret=float(exact_tasks[1,selected]-exact_tasks[1].min()),local_mean=float(lr.mean()),local_max=float(lr.max()),
            aa_lddt=float(np.mean([r['fidelity']['all_atom_lddt'] for r in rows])),
            ca_lddt=float(np.mean([r['fidelity']['ca_lddt'] for r in rows])),
            response=[distance_response_summary(exact_dist[ni],distances[ni],reference_dist[ni]) for ni in range(2)]))
        outputs.extend(rows);print('NORMALIZATION_SCORE_SITE',shard,site['site_key'],flush=True)
    assert len(records)==8 and len(outputs)==304
    with gzip.open(root/f'scores_{shard}.json.gz','wt') as f:json.dump(dict(complete=True,shard=shard,sites=records,outputs=outputs,
        seconds=time.monotonic()-start,lock_sha256=sha256(root/'normalization_lock.json')),f,allow_nan=False)


def summarize_transport_normalization(root):
    root=Path(root);lock=read_transport_normalization_lock(root);source=Path(lock['trajectory_root'])
    sites=[];outputs=[];audits=[];hashes={}
    for base,n in [(source,2),(root,6)]:
        for i in range(n):
            p=base/f'scores_{i}.json.gz';hashes[str(p)]=sha256(p)
            if base==source:assert hashes[str(p)]==lock['score_hashes'][p.name]
            with gzip.open(p,'rt') as f:d=json.load(f)
            assert d['complete'];sites.extend(d['sites']);outputs.extend(d['outputs'])
    for i in range(6):
        d=json.loads((root/f'shard_{i}.json').read_text());assert d['complete'];audits.append(d)
    assert len(sites)==192 and len(outputs)==7296
    assert len({(r['site_key'],r['arm']) for r in sites})==192
    assert len({(r['site_key'],r['arm'],r['noise'],r['aa']) for r in outputs})==7296
    lookup={(r['site_key'],r['arm']):r for r in sites};summary={};contrasts={};selections=[];diagnostics={}
    for r in sites:
        e=np.asarray(lookup[r['site_key'],'exact']['tasks']);p=np.asarray(r['tasks']);chosen=int(p[0].argmin())
        assert np.isclose(e[1,chosen]-e[1].min(),r['old_select_new_regret'],rtol=1e-12,atol=1e-12)
        if r['arm']=='normalized':
            b=lookup[r['site_key'],'wt_progress'];selections.append(dict(role=r['role'],pdb=r['pdb'],site=r['original_aa']+str(r['position']+1),
                raw_choice=b['old_selected'],normalized_choice=r['old_selected'],raw_regret=b['old_select_new_regret'],
                normalized_regret=r['old_select_new_regret'],delta=r['old_select_new_regret']-b['old_select_new_regret']))
    latent=[r for d in audits for r in d['latent']];errors=[r for d in audits for r in d['candidate_errors']]
    for role in sorted({r['role'] for r in sites}):
        summary[role]={};contrasts[role]={}
        for arm in lock['arms']:
            ss=[r for r in sites if r['role']==role and r['arm']==arm];oo=[r for r in outputs if r['role']==role and r['arm']==arm]
            value=summarize_editor_sites(ss,oo)
            value['severe_pairs']=sum(r['geometry']['severe_pairs'] for r in oo)
            value['wrong_centres']=sum(r['geometry']['checked_chirality_wrong'] for r in oo)
            for ref in ('cold_c2','wt_progress'):
                for transition in ('pass_to_fail','fail_to_pass'):
                    field=ref+'_'+transition
                    if all(field in r for r in oo):value[field]=sum(r[field] for r in oo)
            summary[role][arm]=value
        for ref in ('wt_progress','cold_c2','exact'):
            contrasts[role]['normalized-'+ref]={m:paired_parent_interval(summary[role]['normalized']['parent_summaries'],
                summary[role][ref]['parent_summaries'],m) for m in ('spearman','regret','centered_response_rmse')}
        group=[r for r in latent if r['role']==role];parents=sorted({r['parent'] for r in group})
        metrics={}
        for space in ('state','bridge'):
            metrics[space]={}
            for arm in ('wt_progress','normalized'):
                metrics[space][arm]={}
                for field in ('s','z'):
                    values={}
                    for part in ('raw','common','centered'):
                        values[part]={}
                        for key in ('nmse','cosine','energy_ratio'):
                            pv=[]
                            for pi in parents:
                                vals=[r['spaces'][space][arm][field][part][key] for r in group if r['parent']==pi]
                                vals=[v for v in vals if v is not None]
                                if vals:pv.append(float(np.mean(vals)))
                            values[part][key]=float(np.mean(pv)) if pv else None
                    metrics[space][arm][field]=values
        ee=[r for r in errors if r['role']==role];boundary={}
        for field in ('s','z'):
            vals=[r['states'][field] for r in ee]
            boundary[field]=dict(candidates=len(vals),after_error_amplified=sum(v['after_mse']>v['normalized']['mse'] for v in vals),
                raw_channel_mean_fraction_pooled=sum(v['elements']*v['raw']['channel_mean_mse'] for v in vals)/sum(v['elements']*v['raw']['mse'] for v in vals),
                normalized_channel_mean_fraction_pooled=sum(v['elements']*v['normalized']['channel_mean_mse'] for v in vals)/sum(v['elements']*v['normalized']['mse'] for v in vals))
            for name,func in [('raw_before',lambda v:v['raw']['mse']**.5),('normalized_before',lambda v:v['normalized']['mse']**.5),('normalized_after',lambda v:v['after_mse']**.5)]:
                boundary[field][name+'_rmse_parent_mean']=float(np.mean([np.mean([func(r['states'][field]) for r in ee if r['parent']==pi]) for pi in parents]))
        diagnostics[role]=dict(latent=metrics,boundary=boundary)
    counts={k:sum(d['counts'][k] for d in audits) for k in audits[0]['counts']}
    assert counts['recycle']==984 and counts['s1']==1968 and counts['input_embedder']==counts['updates']==0
    write_json(root/'summary.json',dict(complete=True,summary=summary,contrasts=contrasts,diagnostics=diagnostics,selection_changes=selections,
        native_counts=counts,score_hashes=hashes,reference_scales=[r for d in audits for r in d['reference_scales']],
        noedit=sum(len(d['noedit']) for d in audits),raw_replay=sum(len(d['raw_replay']) for d in audits),isolation=sum(len(d['isolation']) for d in audits),
        independent_confirmation=False,promoted=False,training_updates=0,speed_claim=False))
    print('NORMALIZATION_SUMMARY_COMPLETE',counts,flush=True)
