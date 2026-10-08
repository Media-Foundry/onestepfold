"""Independent coordinate-only assessment and native checkpoint replay/timing."""
import argparse
import gzip
import json
import time
from pathlib import Path

import numpy as np
import torch

from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.factor_student_data import FactorTeacherStore
from fastglycan.adapter_supervision import build_adapter_supervision
from fastglycan.backbone_sequence_task import backbone_target_pairs, backbone_target_loss
from fastglycan.functional_response_rank import (
    ranking_fidelity, prepare_fidelity_pairs, response_structure_metrics, response_geometry,
)
from fastglycan.reference_editor_metrics import distance_response_summary, summarize_editor_sites, paired_parent_interval


def score_lora(root, seed):
    begin=time.monotonic();torch.set_num_threads(1)
    lock=json.loads((root/'lora_lock.json').read_text());source=Path(lock['source_root'])
    plan=json.loads((source/'plan.json').read_text())
    old_lock=json.loads((source/'lock.json').read_text())
    for name,digest in lock['source_files'].items(): assert sha256(source/name)==digest,name
    old_preflight=json.loads((source/'preflight.json').read_text())
    for p in old_preflight['baseline']: assert sha256(source/p['path'])==p['sha256']
    preflight=json.loads((Path(lock['native_root'])/'compensation_preflight.json').read_text());assert preflight['complete']
    output=root/'runs'/str(seed);report=json.loads((output/'report.json').read_text())
    assert report['complete'] and report['counts']['updates']==8208
    assert report['counts']['input_embedder']==report['counts']['c4']==0
    assert sha256(output/'history.jsonl')==report['history_sha256']
    assert {e['step'] for e in report['evaluations']}=={0,4104,8208}
    for e in report['evaluations']:
        assert sha256(output/e['checkpoint'])==e['sha256']
        rows=json.loads((output/f"evaluation_{e['step']}.json").read_text())['predictions']
        assert len(rows)==912
        for p in rows: assert sha256(output/p['path'])==p['sha256']
    for p in preflight['baseline'].values(): assert sha256(Path(lock['native_root'])/p['path'])==p['sha256']
    store=FactorTeacherStore(old_lock['teachers'])
    arms=['exact','reference_only','disabled']+[f'{s}_adapted' for s in (0,4104,8208)]
    records=[];outputs=[]
    for site in plan['sites']:
        pi,pos=site['parent_index'],site['position_zero_based'];choices=site['candidates']
        sequence=store.rows[pi]['sequence'];gi=store.lock['gt'][str(pi)]
        assert sha256(Path(gi['path']))==gi['sha256']
        gt=dict(np.load(gi['path']));gca=gt['atom_names']=='CA';y=gt['coordinates'][gca]
        pairs,dist=backbone_target_pairs(y,gt['mask'][gca])
        local=np.linalg.norm(y-y[pos],axis=-1)<=8;local[pos]=True
        ii,jj=np.triu_indices(len(sequence),3)
        wt=store.load(pi);wca=np.flatnonzero(wt['inventory']['atom_names']=='CA')
        rd=np.linalg.norm(wt['coordinates'][:,wca[ii]]-wt['coordinates'][:,wca[jj]],axis=-1)
        tasks={a:np.zeros((2,19)) for a in arms}
        distances={a:np.zeros((2,19,len(ii))) for a in arms}
        site_outputs=[]
        for ai,aa in enumerate(choices):
            label=f'p{pi}_s{pos+1}_{aa}'
            inv=dict(np.load(store.path(pi,label,'inventory.npz')))
            exact=np.load(store.path(pi,label,'coordinates.npz'))['coordinates'][0]
            labels=build_adapter_supervision(dict(inv,coordinates=exact[0],mask=np.ones(len(inv['atom_names']),bool)),
                                             inv['bonds'],sequence[:pos]+aa+sequence[pos+1:])
            ca=np.flatnonzero(inv['atom_names']=='CA');res=inv['residue_ids']
            assert np.array_equal(res[ca],wt['inventory']['residue_ids'][wca])
            xyz=dict(exact=exact,reference_only=np.load(source/'baseline'/f'{label}.npz')['coordinates'],
                     disabled=np.load(Path(lock['native_root'])/preflight['baseline'][label]['path'])['coordinates'])
            for a in arms[3:]: xyz[a]=np.load(output/'coordinates'/f'{a}_{label}.npz')['coordinates']
            for a in ('0_adapted',): assert np.array_equal(xyz[a],xyz['disabled'])
            centers=np.asarray(labels['centres']);volumes0=np.asarray(labels['volumes'])
            for ni,noise in enumerate(store.lock['seeds']):
                caches=prepare_fidelity_pairs(exact[ni],res),prepare_fidelity_pairs(exact[ni,ca],res[ca])
                good={a:response_geometry(xyz[a][ni],labels)['zero_severe_strict_checked_chirality']
                      for a in ['exact','reference_only','disabled']}
                for arm in arms:
                    x=xyz[arm][ni];assert x.shape==exact[ni].shape and np.isfinite(x).all()
                    task=float(backbone_target_loss(torch.tensor(x,dtype=torch.float64),ca,pairs,dist))
                    tasks[arm][ni,ai]=task
                    distances[arm][ni,ai]=np.linalg.norm(x[ca[ii]]-x[ca[jj]],axis=-1)
                    geo=response_geometry(x,labels);ok=geo['zero_severe_strict_checked_chirality']
                    a,b,c,d=centers.T;volumes=(np.cross(x[b]-x[a],x[c]-x[a])*(x[d]-x[a])).sum(1)
                    row=dict(site_key=site['site_key'],parent=pi,position=pos,label=label,role=site['role_n15'],aa=aa,
                             noise=int(noise),arm=arm,task=task,geometry=geo,
                             fidelity=response_structure_metrics(x,exact[ni],ca,local,caches),
                             signed_volumes=volumes.tolist(),center_residues=res[centers].tolist(),
                             center_atom_names=inv['atom_names'][centers].tolist(),
                             reference_oriented_volume_ratio=(volumes*np.sign(volumes0)/np.maximum(abs(volumes0),1e-12)).tolist())
                    for name,ref in [('exact','exact'),('reference','reference_only'),('disabled','disabled')]:
                        row[f'{name}_pass_to_fail']=bool(good[ref] and not ok)
                        row[f'{name}_fail_to_pass']=bool(not good[ref] and ok)
                    site_outputs.append(row)
        for arm in arms:
            rows=[r for r in site_outputs if r['arm']==arm]
            lr=np.array([r['fidelity']['local_ca_rmsd_global_frame'] for r in rows])
            selected=int(np.argmin(tasks[arm][0]))
            records.append(dict(site_key=site['site_key'],parent=pi,position=pos,pdb=site['pdb_id'],role=site['role_n15'],
                                original_aa=site['original_aa'],arm=arm,tasks=tasks[arm].tolist(),
                                ranking=[ranking_fidelity(tasks['exact'][ni],tasks[arm][ni]) for ni in range(2)],
                                aggregate_ranking=ranking_fidelity(tasks['exact'].mean(0),tasks[arm].mean(0)),
                                old_selected=choices[selected],old_select_new_regret=float(tasks['exact'][1,selected]-tasks['exact'][1].min()),
                                local_mean=float(lr.mean()),local_max=float(lr.max()),
                                aa_lddt=float(np.mean([r['fidelity']['all_atom_lddt'] for r in rows])),
                                ca_lddt=float(np.mean([r['fidelity']['ca_lddt'] for r in rows])),
                                response=[distance_response_summary(distances['exact'][ni],distances[arm][ni],rd[ni]) for ni in range(2)]))
        outputs.extend(site_outputs)
        print('SCORE_SITE',seed,site['site_key'],flush=True)
    summary={}
    contrasts={}
    for role in sorted({s['role_n15'] for s in plan['sites']}):
        summary[role]={}
        for a in arms:
            rows=[r for r in records if r['role']==role and r['arm']==a]
            o=[r for r in outputs if r['role']==role and r['arm']==a]
            summary[role][a]=summarize_editor_sites(rows,o)
            summary[role][a]['disabled_pass_to_fail']=sum(r['disabled_pass_to_fail'] for r in o)
            summary[role][a]['disabled_fail_to_pass']=sum(r['disabled_fail_to_pass'] for r in o)
        contrasts[role]={}
        for ref in ('disabled',):
            contrasts[role][f'adapted-{ref}']={f:paired_parent_interval(summary[role]['8208_adapted']['parent_summaries'],
                                                summary[role][ref]['parent_summaries'],f)
                                             for f in ('spearman','regret','centered_response_rmse')}
    result=dict(complete=True,seed=seed,summary=summary,contrasts=contrasts,sites=records,outputs=outputs,
                seconds=time.monotonic()-begin,report_sha256=sha256(output/'report.json'),
                scorer_sha256=sha256(Path(__file__)),independent_confirmation=False,promoted=False)
    with gzip.open(output/'scores.json.gz','wt') as f: json.dump(result,f,allow_nan=False)
    write_json(output/'summary.json',{k:v for k,v in result.items() if k not in ['sites','outputs']})
    print('SCORE_COMPLETE',seed,result['seconds'],flush=True)


def replay_lora(root,seed):
    from run_recycle_lora import LoRARuntime
    from fastglycan.models.recycle_lora import RecycleLoRA
    from fastglycan.models.compensated_recycle import initialize_cached_recycle,capture_cached_prefix,native_recycle_step
    from contextlib import nullcontext
    rt=LoRARuntime(root,f'lora_replay_{seed}');out=root/'runs'/str(seed)
    site=rt.base.sites['p3_s37'];choices=site['candidates'];replays=[]
    with torch.no_grad():
        for step in rt.lock['checkpoints']:
            cp=torch.load(out/'checkpoints'/f'{step}.pt',map_location='cpu',weights_only=False)
            assert cp['lock_sha256']==sha256(root/'lora_lock.json')
            bank=RecycleLoRA(rt.model.pairformer_stack,**cp['config']).cuda().eval();bank.load_state_dict(cp['state_dict'])
            item,c=rt.conditioning(bank,site,choices[0])
            old=np.load(out/'coordinates'/f'{step}_adapted_{item["label"]}.npz')['coordinates']
            for ni in range(2): assert np.array_equal(rt.base.decode(item,c,ni).cpu().numpy(),old[ni])
            replays.append(dict(step=step,bitwise=True))
        _,a=rt.conditioning(bank,site,choices[0]);rt.conditioning(bank,site,choices[-1]);_,b=rt.conditioning(bank,site,choices[0])
        assert all(torch.equal(x,y) for x,y in zip(a,b))
        # Disabled after nonzero adaptation must restore exact old baseline.
        for site_check in rt.base.plan['sites']:
            aa=site_check['candidates'][0];item,c=rt.conditioning(None,site_check,aa)
            rec=rt.preflight['baseline'][item['label']]
            expected=np.load(Path(rt.lock['native_root'])/rec['path'])['coordinates']
            for ni in range(2): assert np.array_equal(rt.base.decode(item,c,ni).cpu().numpy(),expected[ni])
        items=[rt.base.item(3,36,aa) for aa in choices]
        inputs=[rt.candidate_input(item) for item in items];wt=rt.base.item(3);times=[]
        for repeat in range(6):
            for arm in np.roll(['cold_C4','disabled','adapted'],repeat%3):
                torch.cuda.synchronize();begin=time.perf_counter();source_time=0.
                if arm!='cold_C4':
                    ini=initialize_cached_recycle(rt.model,wt['features'],rt.base.references[3][0])
                    prefix,rng=capture_cached_prefix(rt.model,wt['features'],ini)
                    final=native_recycle_step(rt.model,wt['features'],ini,prefix,rng=rng)
                    assert all(torch.equal(x,y) for x,y in zip(final,rt.base.references[3][1:]))
                    torch.cuda.synchronize();source_time=time.perf_counter()-begin
                for i,item in enumerate(items):
                    init=initialize_cached_recycle(rt.model,item['features'],inputs[i])
                    if arm=='cold_C4':
                        final=(torch.zeros_like(init.single),torch.zeros_like(init.pair))
                        for _ in range(4): final=native_recycle_step(rt.model,item['features'],init,final)
                    else:
                        with bank.candidate(rt.model.pairformer_stack) if arm=='adapted' else nullcontext():
                            final=native_recycle_step(rt.model,item['features'],init,prefix,rng=rng)
                    rt.base.decode(item,(init.inputs,*final),0)
                torch.cuda.synchronize();times.append(dict(repeat=repeat,arm=str(arm),seconds=time.perf_counter()-begin,
                                                           reference_c4_seconds=source_time))
    rt.finish()
    write_json(out/'replay_timing.json',dict(complete=True,replays=replays,timing=times,counts=rt.base.counts,runtime=rt.base.runtime,
         peak_allocated_bytes=torch.cuda.max_memory_allocated(),noedit_bypass_bitwise=True,serial_order_bitwise=True,
         disabled_restored_sites=48,excludes=['ESM/MSA preparation','cold model load','disk','scoring']))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--seed',type=int,required=True)
    p.add_argument('--mode',choices=['score','replay'],required=True);a=p.parse_args()
    (score_lora if a.mode=='score' else replay_lora)(a.root,a.seed)
