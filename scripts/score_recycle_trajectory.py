"""Coordinate-only comparison of C4, cold C2 and candidate-first WT transport."""
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


def score_trajectory(root,shard):
    begin=time.monotonic();torch.set_num_threads(1)
    lock=json.loads((root/'trajectory_lock.json').read_text())
    for name,digest in lock['code'].items(): assert sha256(root/'code'/name)==digest,name
    assert sha256(root/'protocol.md')==lock['protocol_sha256']
    lora_root=Path(lock['source']);lora=json.loads((lora_root/'lora_lock.json').read_text())
    source=Path(lora['source_root'])
    for name,digest in lora['source_files'].items(): assert sha256(source/name)==digest,name
    plan=json.loads((source/'plan.json').read_text());old_lock=json.loads((source/'lock.json').read_text())
    old_preflight=json.loads((source/'preflight.json').read_text())
    for r in old_preflight['baseline']: assert sha256(source/r['path'])==r['sha256']
    data=json.loads((root/f'shard_{shard}.json').read_text());assert data['complete']
    files={(r['arm'],r['label']):r for r in data['rows']}
    store=FactorTeacherStore(old_lock['teachers'])
    arms=['exact','cold_c2','wt_progress']
    records=[];outputs=[]
    for index,site in enumerate(plan['sites']):
        if site['parent_index']%2!=shard: continue
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
            record=files['exact',label];ep=root/record['path'];assert sha256(ep)==record['sha256']
            assert np.array_equal(np.load(ep)['coordinates'],exact)
            xyz={'exact':exact}
            for arm in arms[1:]:
                record=files[arm,label];path=root/record['path'];assert sha256(path)==record['sha256']
                xyz[arm]=np.load(path)['coordinates']
            # Historical reference-only is only a geometry-transition comparator.
            xyz['reference_only']=np.load(source/'baseline'/f'{label}.npz')['coordinates']
            centers=np.asarray(labels['centres']);volumes0=np.asarray(labels['volumes'])
            for ni,noise in enumerate(store.lock['seeds']):
                caches=prepare_fidelity_pairs(exact[ni],res),prepare_fidelity_pairs(exact[ni,ca],res[ca])
                good={a:response_geometry(xyz[a][ni],labels)['zero_severe_strict_checked_chirality']
                      for a in ['exact','reference_only','cold_c2']}
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
                    for name,ref in [('exact','exact'),('reference','reference_only'),('cold_c2','cold_c2')]:
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
        print('SCORE_TRAJECTORY_SITE',shard,site['site_key'],flush=True)
    assert len(records)==24*3 and len(outputs)==24*3*38
    result=dict(complete=True,shard=shard,sites=records,outputs=outputs,seconds=time.monotonic()-begin,
        scorer_sha256=sha256(Path(__file__)),trajectory_lock_sha256=sha256(root/'trajectory_lock.json'))
    with gzip.open(root/f'scores_{shard}.json.gz','wt') as f: json.dump(result,f,allow_nan=False)
    print('SCORE_TRAJECTORY_COMPLETE',shard,result['seconds'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--shard',type=int,choices=range(2),required=True)
    args=p.parse_args();score_trajectory(args.root,args.shard)
