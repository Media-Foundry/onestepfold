"""Independent task-label, checkpoint and selection audit; CPU only."""
import argparse,gzip,json
from pathlib import Path
import numpy as np
import torch
from scipy.stats import spearmanr
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.task_readout import ContextTaskReadout,AATaskReadout


def audit_task_readout(root):
    torch.set_num_threads(1)
    load=lambda p:json.loads(p.read_text())
    assert load(root/'execution.json')['complete']
    lock=load(root/'lock.json');report=load(root/'report.json');labels=load(root/'evaluation_labels.json')['cases']
    for group in ('code_hashes','label_hashes'):
        for path,h in lock[group].items():assert sha256(Path(path))==h
    with gzip.open(Path(lock['prior'])/'report.json.gz','rt') as f:original=json.load(f)
    label_checks=0
    for c in labels:
        site=next(s for s in original['sites'] if (s['parent_index'],s['position'])==(c['parent_index'],c['position']))
        for n,seed in enumerate(lock['seeds']):
            wt=next(x['task'] for x in site['outputs'] if x['arm']=='exact' and x['noise']==seed and x['aa']==lock['aa'][c['wt']])
            for a,aa in enumerate(lock['aa']):
                raw=next(x['task'] for x in site['outputs'] if x['arm']=='exact' and x['noise']==seed and x['aa']==aa)
                assert abs((raw-wt)-c['target_delta'][n][a])<1e-14;label_checks+=1
    initial={};checkpoints=[]
    for job in lock['jobs']:
        run=root/'runs'/job['id'];r=load(run/'report.json');assert r['complete'] and r['context_exposures']==[3276]*10
        assert [h['step'] for h in r['history']]==[0,10920,21840,32760]
        train=load(root/f'train_{job["arm"]}.json')['cases'];assert [(x['parent_index'],x['position']) for x in train]==[tuple(x) for x in job['train_sites']]
        assert all(x['parent_index']!=6 and (x['parent_index'],x['position']) not in ((4,24),(5,33)) and lock['rows'][x['parent_index']]['role']=='train' for x in train)
        scale=float(np.sqrt(np.mean(np.concatenate([np.delete(np.array(x['target_delta'])[:2].mean(0),x['wt']) for x in train])**2)))
        assert scale==job['scale']
        packet=torch.load(run/'initial.pt',map_location='cpu',weights_only=False)
        assert sha256(run/'initial.pt')==r['initial_sha256']
        torch.manual_seed(job['seed']);net=ContextTaskReadout() if job['architecture']=='context' else AATaskReadout()
        assert all(torch.equal(p,packet['state_dict'][name]) for name,p in net.state_dict().items())
        initial[job['id']]=packet['state_dict']
        for h in r['history'][1:]:
            assert sha256(Path(h['checkpoint']))==h['sha256']
            cp=torch.load(h['checkpoint'],map_location='cpu',weights_only=False)
            assert cp['step']==h['step'] and cp['exposures']==[h['step']//10]*10
            steps={int(v['step']) for v in cp['optimizer']['state'].values()};assert steps=={h['step']}
            checkpoints.append(dict(job=job['id'],step=h['step'],sha256=h['sha256']))
    for architecture in ('context','aa_only'):
        for seed in (231301,231303):
            a,b=initial[f'restricted_{architecture}_s{seed}'],initial[f'expanded_{architecture}_s{seed}']
            assert all(torch.equal(a[k],b[k]) for k in a)
    selections=geometry=0
    for row in report['results']:
        c=next(c for c in labels if (c['parent_index'],c['position'])==(row['parent_index'],row['position']))
        ids=[a for a in range(20) if a!=c['wt']];names=[lock['aa'][i] for i in ids]
        pred=np.array(row['predicted_delta']);assert pred[c['wt']]==0 and np.isfinite(pred).all()
        target=np.array(c['target_delta'])[:,ids];x=pred[ids];chosen=int(np.argmin(x))
        for group,ns in [('old',[0,1]),('new',[2,3]),('all',[0,1,2,3])]:
            y=target[ns].mean(0);s=row['selection']['aggregate'][group]
            rho=float(spearmanr(y,x).statistic) if np.ptp(y) and np.ptp(x) else None
            assert (rho is None and s['spearman'] is None) or abs(rho-s['spearman'])<1e-12
            assert names[chosen]==s['student_choice'] and abs(y[chosen]-y.min()-s['top1_regret'])<1e-12
            assert abs(np.mean(abs(y-x))-s['task_mae'])<1e-12;selections+=1
        y=target[2:].mean(0);old=int(np.argmin(target[:2].mean(0)))
        cross=row['selection']['cross_noise']
        assert abs(y[chosen]-y.min()-cross['regret_to_new_best'])<1e-12
        assert abs(y[chosen]-y[old]-cross['extra_regret_vs_teacher_old_choice'])<1e-12
        assert row['selected_aa']==names[chosen]
        for n,g in enumerate(row['selected_teacher_geometry']):
            assert g==c['teacher_geometry'][n][ids[chosen]];geometry+=1
    write_json(root/'independent_audit.json',dict(complete=True,initializations=8,matched_initial_pairs=4,
                                               checkpoints=checkpoints,label_checks=label_checks,selection_checks=selections,
                                               selected_geometry_checks=geometry,s1_calls=0,c4_calls=0,
                                               audit_source_sha256=sha256(Path(__file__))))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    audit_task_readout(p.parse_args().root)
