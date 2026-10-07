"""Independent score reconstruction and saved-checkpoint S1 replay for editor pilot."""
import argparse
import gzip
import json
import time
from pathlib import Path
import numpy as np
import torch
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.factor_student_data import FactorTeacherStore
from fastglycan.functional_response_rank import (ranking_fidelity,prepare_fidelity_pairs,response_structure_metrics,response_geometry,pack_conditioning)
from fastglycan.adapter_supervision import build_adapter_supervision
from fastglycan.backbone_sequence_task import backbone_target_pairs,backbone_target_loss


def score_reference_editor(root):
    started=time.monotonic();torch.set_num_threads(1)
    lock=rt.load_json(root/'lock.json');run=rt.load_json(root/'report.json')
    assert run['complete'] and rt.load_json(root/'execution.json')['complete']
    assert run['counts']==dict(c4=0,input_embedder=0,s1=3808,updates=1024),run['counts']
    assert len(run['preflight'])==95 and len(set(run['preflight']))==95
    for p,h in lock['code'].items():assert sha256(root/'code'/p)==h
    store=FactorTeacherStore(lock['teachers']);aa=store.lock['aa'];arms=['reference_only']
    for r in run['runs']:
        assert r['complete'] and len(r['history'])==512
        assert [e['step'] for e in r['evaluations']]==[0,128,512]
        for e in r['evaluations']:
            assert sha256(root/e['checkpoint'])==e['sha256']
            assert len(e['predictions'])==95
            for p in e['predictions']:assert sha256(root/p['path'])==p['sha256']
            arms.append(f"{r['seed']}_{e['step']}")
    records=[];all_outputs=[]
    for site in lock['sites']:
        pi,pos=site['parent'],site['position'];seq=store.rows[pi]['sequence'];choices=[a for a in aa if a!=seq[pos]]
        gtinfo=store.lock['gt'][str(pi)];assert sha256(Path(gtinfo['path']))==gtinfo['sha256']
        gt=dict(np.load(gtinfo['path']));gca=gt['atom_names']=='CA';y=gt['coordinates'][gca];obs=gt['mask'][gca]
        taskpairs,taskdist=backbone_target_pairs(y,obs)
        local=np.linalg.norm(y-y[pos],axis=-1)<=8;local[pos]=True
        tasks={arm:np.zeros((2,19)) for arm in ['exact',*arms]};site_outputs=[]
        for ai,a in enumerate(choices):
            source=store.load(pi,pos,a);inv=source['inventory'];exact=source['coordinates'][0];label=source['label']
            labels=build_adapter_supervision(dict(inv,coordinates=exact[0],mask=np.ones(len(inv['atom_names']),bool)),inv['bonds'],source['sequence'])
            ca=np.flatnonzero(inv['atom_names']=='CA');res=inv['residue_ids']
            xyz={'exact':exact,'reference_only':np.load(root/'coordinates'/f'baseline_{label}.npz')['coordinates']}
            for arm in arms[1:]:xyz[arm]=np.load(root/'coordinates'/f'{arm}_{label}.npz')['coordinates']
            for ni,noise in enumerate(store.lock['seeds']):
                caches=(prepare_fidelity_pairs(exact[ni],res),prepare_fidelity_pairs(exact[ni,ca],res[ca]))
                exact_geo=response_geometry(exact[ni],labels);base_geo=response_geometry(xyz['reference_only'][ni],labels)
                for arm,xs in xyz.items():
                    x=xs[ni];assert x.shape==exact[ni].shape and np.isfinite(x).all()
                    task=float(backbone_target_loss(torch.tensor(x,dtype=torch.float64),ca,taskpairs,taskdist));tasks[arm][ni,ai]=task
                    geom=response_geometry(x,labels);fidelity=response_structure_metrics(x,exact[ni],ca,local,caches)
                    b=np.asarray(inv['bonds'])[:,:2];lengths=np.linalg.norm(x[b[:,0]]-x[b[:,1]],axis=-1);peptide=res[b[:,0]]!=res[b[:,1]]
                    row=dict(parent=pi,position=pos,role=site['role'],aa=a,noise=int(noise),arm=arm,task=task,geometry=geom,fidelity=fidelity,
                             new_vs_exact=exact_geo['zero_severe_strict_checked_chirality'] and not geom['zero_severe_strict_checked_chirality'],
                             new_vs_reference_only=base_geo['zero_severe_strict_checked_chirality'] and not geom['zero_severe_strict_checked_chirality'],
                             bond_length_min=float(lengths.min()),bond_length_max=float(lengths.max()),
                             peptide_cn_rmse_from_1p33=float(np.sqrt(np.mean((lengths[peptide]-1.33)**2))))
                    site_outputs.append(row)
        for arm in ['exact',*arms]:
            ranks=[ranking_fidelity(tasks['exact'][ni],tasks[arm][ni]) for ni in range(2)]
            selected=int(np.argmin(tasks[arm][0]));best=float(tasks['exact'][1].min());regret=float(tasks['exact'][1,selected]-best)
            rows=[r for r in site_outputs if r['arm']==arm];local_values=np.array([r['fidelity']['local_ca_rmsd_global_frame'] for r in rows])
            records.append(dict(**site,pdb=store.rows[pi]['pdb_id'],arm=arm,ranking=ranks,
                aggregate_ranking=ranking_fidelity(tasks['exact'].mean(0),tasks[arm].mean(0)),
                old_selected=choices[selected],old_select_new_regret=regret,
                local_mean=float(local_values.mean()),local_p95=float(np.quantile(local_values,.95)),local_p99=float(np.quantile(local_values,.99)),local_max=float(local_values.max()),local_over1=int((local_values>1).sum()),
                aa_lddt=float(np.mean([r['fidelity']['all_atom_lddt'] for r in rows])),
                ca_lddt=float(np.mean([r['fidelity']['ca_lddt'] for r in rows])),
                geometry_pass=sum(r['geometry']['zero_severe_strict_checked_chirality'] for r in rows),
                new_vs_exact=sum(r['new_vs_exact'] for r in rows),new_vs_reference_only=sum(r['new_vs_reference_only'] for r in rows)))
        all_outputs+=site_outputs
    summary={}
    for role in ['train','same_protein','new_protein']:
        summary[role]={}
        for arm in ['exact',*arms]:
            rows=[r for r in records if r['role']==role and r['arm']==arm]
            summary[role][arm]=dict(sites=len(rows),proteins=len({r['parent'] for r in rows}),
                spearman=float(np.mean([r['aggregate_ranking']['spearman'] for r in rows if r['aggregate_ranking']['spearman'] is not None])),
                old_spearman=float(np.mean([r['ranking'][0]['spearman'] for r in rows if r['ranking'][0]['spearman'] is not None])),
                confirmation_spearman=float(np.mean([r['ranking'][1]['spearman'] for r in rows if r['ranking'][1]['spearman'] is not None])),
                top1=sum(r['aggregate_ranking']['top1_match'] for r in rows),regret=float(np.mean([r['old_select_new_regret'] for r in rows])),
                aa_lddt=float(np.mean([r['aa_lddt'] for r in rows])),local_mean=float(np.mean([r['local_mean'] for r in rows])),
                local_max=max(r['local_max'] for r in rows),local_over1=sum(r['local_over1'] for r in rows),
                geometry_pass=sum(r['geometry_pass'] for r in rows),new_vs_exact=sum(r['new_vs_exact'] for r in rows),new_vs_reference_only=sum(r['new_vs_reference_only'] for r in rows))
    result=dict(complete=True,summary=summary,sites=records,outputs=all_outputs,counts=run['counts'],report_sha256=sha256(root/'report.json'),
                audit_source_sha256=sha256(Path(__file__)),seconds=time.monotonic()-started,oracle_target_conditioning=False,independent_confirmation=False)
    with gzip.open(root/'scores.json.gz','wt') as f:json.dump(result,f,allow_nan=False)
    write_json(root/'summary.json',dict(complete=True,summary=summary,scores_sha256=sha256(root/'scores.json.gz')))
    print(json.dumps(dict(complete=True,outputs=len(all_outputs),summary=summary),indent=2))


def replay_reference_editor(root):
    from fastglycan.hip_device_policy import guarded_hip_runtime
    from fastglycan.reference_editor import ReferenceEditModel
    from fastglycan.models.soft_sequence_chart import native_sequence_features,device_tree
    from fastglycan.models.differentiable_mini import prepare_atom_pairs,diffusion_from_conditioning
    from fastglycan.hybrid_proposals import identity_noise
    runtime=guarded_hip_runtime();lock=rt.load_json(root/'lock.json');run=rt.load_json(root/'report.json');assert run['complete']
    store=FactorTeacherStore(lock['teachers']);aa=store.lock['aa'];pi=3;pos=36;seq=store.rows[pi]['sequence'];choices=[a for a in aa if a!=seq[pos]][:4]
    runner=rt.runner_setup(root/'replay_work');runner.configs.dtype='fp32';decoder=runner.model.eval().requires_grad_(False)
    reference=tuple(t.cuda() for t in store.load(pi)['conditioning']);records=[]
    source=store.load(pi,pos,choices[0]);native,atoms=native_sequence_features(source['sequence'])
    f=prepare_atom_pairs(decoder.relative_position_encoding.generate_relp(device_tree(native,'cuda')))
    noises=[identity_noise(atoms,n,device='cuda') for n in store.lock['seeds']]
    with torch.no_grad():
        for r in run['runs']:
            for e in r['evaluations']:
                path=root/e['checkpoint'];assert sha256(path)==e['sha256'];p=torch.load(path,map_location='cpu',weights_only=False)
                net=ReferenceEditModel(**p['architecture']).cuda().eval();net.load_state_dict(p['state_dict'])
                cache=net.prepare_reference(reference,[aa.index(a) for a in seq]);c=net(cache,[[(pos,aa.index(seq[pos]),aa.index(a))] for a in choices])
                old=np.load(root/'coordinates'/f"{r['seed']}_{e['step']}_{source['label']}.npz")['coordinates']
                for ni,n in enumerate(noises):
                    x=diffusion_from_conditioning(decoder,f,n,pack_conditioning(tuple(t[0] for t in c)),steps=1).squeeze(0).cpu().numpy()
                    assert np.array_equal(x,old[ni]),(r['seed'],e['step'],ni,float(np.max(np.abs(x-old[ni]))))
                records.append(dict(seed=r['seed'],step=e['step'],coordinate_bitwise=True,checkpoint_sha256=e['sha256']))
    write_json(root/'checkpoint_replay.json',dict(complete=True,runtime=runtime,records=records,s1_calls=12,c4_calls=0,esm_calls=0,audit_source_sha256=sha256(Path(__file__))))
    print('CHECKPOINT REPLAY COMPLETE',len(records),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--mode',choices=['score','replay'],required=True);a=p.parse_args()
    (score_reference_editor if a.mode=='score' else replay_reference_editor)(a.root)
