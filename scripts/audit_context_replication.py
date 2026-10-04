"""Independent endpoint and data-split audit; no new predictions or updates."""
import argparse,json
from pathlib import Path
import numpy as np
import torch
from scipy.stats import spearmanr
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.context_replication import AA
from run_task_readout import make_task_model


def audit_context_replication(root):
    torch.set_num_threads(1);load=lambda p:json.loads(p.read_text())
    lock=load(root/'lock.json');manifest=load(root/'label_manifest.json');report=load(root/'report.json');assert report['complete']
    for p,h in lock['code_hashes'].items():assert sha256(Path(p))==h
    for p,h in manifest['files'].items():assert sha256(Path(p))==h
    native={x['label']:x for x in load(root/'native_manifest.json')['records']};tasks={};task_checks=0
    for worker in range(4):
        teacher=load(root/f'teacher_{worker}/report.json');scored=load(root/f'score_{worker}/report.json')['endpoints'];assert teacher['complete']
        for r in teacher['records']:
            assert sha256(Path(r['coordinates']['path']))==r['coordinates']['sha256']
            item=native[r['label']];assert sha256(Path(item['path']))==item['sha256']
            inv=dict(np.load(item['path']));co=np.load(r['coordinates']['path'])['coordinates'];ca=inv['atom_names']=='CA'
            g=lock['gt'][str(r['parent_index'])];assert sha256(Path(g['path']))==g['sha256'];gt=dict(np.load(g['path']))
            mask=gt['mask'][gt['atom_names']=='CA'];ref=gt['coordinates'][gt['atom_names']=='CA'].astype(float)
            i,j=np.triu_indices(len(ref),3);valid=mask[i]&mask[j];i,j=i[valid],j[valid]
            distance=np.linalg.norm(ref[i]-ref[j],axis=-1);scores=[]
            for xyz in co:
                x=xyz[ca].astype(float);e=abs(np.linalg.norm(x[i]-x[j],axis=-1)-distance)
                scores.append(float(np.where(e<=1,.5*e**2,e-.5).mean()))
            assert np.allclose(scores,scored[r['label']]['task'],rtol=0,atol=1e-12)
            tasks[r['label']]=np.array(scores);task_checks+=4
    cases=load(root/'evaluation_labels.json')['cases'];labels=0
    for c in cases:
        pi,pos=c['parent_index'],c['position'];expected=[]
        for a,aa in enumerate(AA):
            key=f'p{pi}_wt' if a==c['wt'] else f'p{pi}_s{pos+1}_{aa}'
            expected.append(tasks[key]-tasks[f'p{pi}_wt']);labels+=4
        assert np.allclose(np.array(expected).T,c['target_delta'],rtol=0,atol=1e-12)
    states={};checkpoints=0
    for job in lock['jobs']:
        run=root/'runs'/job['id'];rr=load(run/'report.json');assert rr['complete']
        cases_train=load(root/f'train_n{job["size"]}.json')['cases']
        assert [[c['parent_index'],c['position']] for c in cases_train]==job['train_sites']
        assert all(c['role']=='train' and len(c['target_delta'])==2 for c in cases_train)
        initial=torch.load(run/'initial.pt',map_location='cpu',weights_only=False)
        assert sha256(run/'initial.pt')==rr['initial_sha256']
        torch.manual_seed(job['seed']);net=make_task_model(job['architecture'])
        assert all(torch.equal(v,initial['state_dict'][k]) for k,v in net.state_dict().items())
        key=(job['architecture'],job['seed']);state=initial['state_dict']
        if key in states:assert all(torch.equal(v,states[key][k]) for k,v in state.items())
        else:states[key]=state
        assert [h['step'] for h in rr['history']]==[0,*job['snapshots']]
        for h in rr['history'][1:]:
            assert sha256(Path(h['checkpoint']))==h['sha256'];cp=torch.load(h['checkpoint'],map_location='cpu',weights_only=False)
            assert cp['step']==h['step'] and cp['exposures']==[h['step']//len(cases_train)]*len(cases_train)
            assert {int(x['step']) for x in cp['optimizer']['state'].values()}=={h['step']};checkpoints+=1
        assert rr['context_exposures']==[1024]*len(cases_train)
    selections=geometry=0
    for row in report['results']:
        c=next(c for c in cases if (c['parent_index'],c['position'])==(row['parent_index'],row['position']))
        ids=[a for a in range(20) if a!=c['wt']];names=[AA[a] for a in ids];x=np.array(row['predicted_delta'])[ids];target=np.array(c['target_delta'])[:,ids];chosen=int(np.argmin(x))
        for group,ns in [('old',[0,1]),('new',[2,3]),('all',[0,1,2,3])]:
            y=target[ns].mean(0);s=row['selection']['aggregate'][group]
            rho=float(spearmanr(y,x).statistic) if np.ptp(y) and np.ptp(x) else None
            assert (rho is None and s['spearman'] is None) or abs(rho-s['spearman'])<1e-12
            assert names[chosen]==s['student_choice'] and abs(y[chosen]-y.min()-s['top1_regret'])<1e-12;selections+=1
        new=target[2:].mean(0);cross=row['selection']['cross_noise']
        assert abs(new[chosen]-new.min()-cross['regret_to_new_best'])<1e-12
        assert row['selected_aa']==names[chosen]
        assert row['selected_teacher_geometry']==[g[ids[chosen]] for g in c['teacher_geometry']];geometry+=4
    write_json(root/'independent_audit.json',dict(complete=True,task_checks=task_checks,label_checks=labels,
                                               initializations=len(lock['jobs']),paired_initial_groups=len(states),checkpoints=checkpoints,
                                               selection_checks=selections,selected_geometry_checks=geometry,
                                               c4_calls=0,s1_calls=0,optimizer_updates=0))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True,type=Path);audit_context_replication(p.parse_args().root)
