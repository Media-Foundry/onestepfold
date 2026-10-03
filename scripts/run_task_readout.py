"""Bounded direct task readout versus AA-only; archived labels, no decoder calls."""
import argparse,gzip,json,time
from pathlib import Path
import numpy as np
import torch
from fastglycan.task_readout import ContextTaskReadout,AATaskReadout,reference_node_features
from fastglycan.factor_student_data import FactorTeacherStore
from fastglycan.response_coverage import SETS,SEEDS,SNAPSHOTS,coverage_exposures
from fastglycan.hip_device_policy import guarded_hip_runtime
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.multicontext_response import noise_selection


def prepare_task_readout(root):
    assert not (root/'lock.json').exists()
    prior=root.parent/'pair_coverage_v1_20261003'
    panel=json.loads((prior/'evaluation_lock.json').read_text())
    assert json.loads((prior/'independent_audit.json').read_text())['complete']
    with gzip.open(prior/'report.json.gz','rt') as f:report=json.load(f)
    labels=[]
    for site in report['sites']:
        pi,pos=site['parent_index'],site['position'];wt=panel['aa'].index(panel['rows'][pi]['sequence'][pos])
        records={(x['arm'],x['noise'],x['aa']):x for x in site['outputs']}
        matrices={arm:np.array([[records[arm,seed,aa]['task'] for aa in panel['aa']] for seed in panel['seeds']]) for arm in panel['arms']}
        native=matrices['exact'];wt_task=native[:,wt]
        labels.append(dict(parent_index=pi,position=pos,wt=wt,pdb_id=site['pdb_id'],
                           target_delta=(native-wt_task[:,None]).tolist(),wt_task=wt_task.tolist(),
                           comparators={arm:(value-wt_task[:,None]).tolist() for arm,value in matrices.items()},
                           teacher_geometry=[[records['exact',seed,aa]['geometry'] for aa in panel['aa']] for seed in panel['seeds']]))
    write_json(root/'evaluation_labels.json',dict(cases=labels))
    jobs=[];scales={}
    for arm,contexts in SETS.items():
        rows=[next(x for x in labels if (x['parent_index'],x['position'])==site) for site in contexts]
        targets=np.concatenate([np.delete(np.array(x['target_delta'])[:2].mean(0),x['wt']) for x in rows])
        scale=float(np.sqrt(np.mean(targets**2)));assert scale>1e-8
        scales[arm]=scale
        write_json(root/f'train_{arm}.json',dict(cases=rows))
        for architecture in ('context','aa_only'):
            for seed in SEEDS:
                jobs.append(dict(id=f'{arm}_{architecture}_s{seed}',arm=arm,architecture=architecture,seed=seed,
                                 train_sites=[list(x) for x in contexts],steps=32760,lr=.001,weight_decay=.0001,
                                 scale=scale,initial_checkpoint=None))
    lock=dict(schema='task_readout_v1',prior=str(prior),teachers=panel['teachers'],rows=panel['rows'],
              gt=panel['gt'],contexts=panel['contexts'],aa=panel['aa'],seeds=panel['seeds'],jobs=jobs,
              snapshots=list(SNAPSHOTS),primary_step=32760,scales=scales,
              prior_report_sha256=sha256(prior/'report.json.gz'),
              teacher_lock_sha256=sha256(Path(panel['teachers'])/'teacher_lock.json'),
              teacher_manifest_sha256=sha256(Path(panel['teachers'])/'teacher_manifest.json'),
              label_hashes={str(root/name):sha256(root/name) for name in ('evaluation_labels.json','train_restricted.json','train_expanded.json')},
              code_hashes={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ('.py','.md')})
    write_json(root/'lock.json',lock)
    for job in jobs:write_json(root/'jobs'/f'{job["id"]}.json',job)


def verify_task_lock(root):
    lock=json.loads((root/'lock.json').read_text())
    for group in ('code_hashes','label_hashes'):
        for p,h in lock[group].items():assert sha256(Path(p))==h,p
    for file,field in [('teacher_lock.json','teacher_lock_sha256'),('teacher_manifest.json','teacher_manifest_sha256')]:
        assert sha256(Path(lock['teachers'])/file)==lock[field]
    assert sha256(Path(lock['prior'])/'report.json.gz')==lock['prior_report_sha256']
    return lock


def context_task_input(store,lock,case,device):
    pi,pos=case['parent_index'],case['position']
    # WT ONLY. No native mutant, target s, z or s_inputs is accessed.
    item=store.load(pi);_,s,z=item['conditioning']
    info=lock['gt'][str(pi)];assert sha256(Path(info['path']))==info['sha256']
    gt=dict(np.load(info['path']));ca=gt['atom_names']=='CA'
    ref=reference_node_features(gt['coordinates'][ca],gt['mask'][ca],pos)
    return dict(s=s.to(device),z=z.to(device),reference=torch.from_numpy(ref).to(device),position=pos,wt=case['wt'])


def task_prediction(model,architecture,data,wt):
    if architecture=='aa_only':return model(wt)
    return model(data['s'],data['z'],data['position'],data['wt'],data['reference'])


def make_task_model(architecture):
    return ContextTaskReadout() if architecture=='context' else AATaskReadout()


def train_task_readout(root,jobid):
    lock=verify_task_lock(root);job=next(x for x in lock['jobs'] if x['id']==jobid)
    gpu=job['architecture']=='context';runtime=guarded_hip_runtime() if gpu else dict(device='cpu')
    torch.set_num_threads(1);device='cuda' if gpu else 'cpu'
    cases=json.loads((root/f'train_{job["arm"]}.json').read_text())['cases']
    assert [(x['parent_index'],x['position']) for x in cases]==[tuple(x) for x in job['train_sites']]
    assert all(lock['rows'][x['parent_index']]['role']=='train' for x in cases)
    store=FactorTeacherStore(Path(lock['teachers']),training_only=True) if gpu else None
    data=[context_task_input(store,lock,c,device) for c in cases] if gpu else [None]*10
    targets=[torch.tensor(np.array(c['target_delta'])[:2].mean(0)/job['scale'],device=device,dtype=torch.float32) for c in cases]
    ids=[torch.tensor([i for i in range(20) if i!=c['wt']],device=device) for c in cases]
    torch.manual_seed(job['seed']);model=make_task_model(job['architecture']).to(device)
    optimizer=torch.optim.AdamW(model.parameters(),lr=job['lr'],weight_decay=job['weight_decay'],eps=1e-8)
    out=root/'runs'/jobid;out.mkdir(parents=True,exist_ok=False)
    torch.save(dict(state_dict=model.state_dict(),job=job,step=0),out/'initial.pt')
    report=dict(complete=False,job=job,runtime=runtime,parameters=sum(p.numel() for p in model.parameters()),
                initial_sha256=sha256(out/'initial.pt'),history=[],trace=[],c4_calls=0,s1_calls=0,oracle_target_s=False)
    start=time.monotonic();counts=[0]*10
    def snapshot(step):
        metrics=[]
        with torch.no_grad():
            for i,c in enumerate(cases):
                pred=task_prediction(model,job['architecture'],data[i],c['wt']);assert pred[c['wt']]==0
                loss=float((pred[ids[i]]-targets[i][ids[i]]).square().mean())
                metrics.append(dict(parent_index=c['parent_index'],position=c['position'],normalized_mse=loss,
                                    predicted_delta=(pred*job['scale']).cpu().tolist()))
        row=dict(step=step,exposures=list(counts),sites=metrics,seconds=time.monotonic()-start)
        if step:
            path=out/f'checkpoint_{step}.pt'
            torch.save(dict(state_dict=model.state_dict(),optimizer=optimizer.state_dict(),step=step,job=job,exposures=list(counts)),path)
            row.update(checkpoint=str(path),sha256=sha256(path))
        report['history'].append(row);write_json(out/'report.json',report)
    snapshot(0)
    for step in range(1,job['steps']+1):
        i=(step-1)%10;optimizer.zero_grad(set_to_none=True)
        pred=task_prediction(model,job['architecture'],data[i],cases[i]['wt'])
        loss=(pred[ids[i]]-targets[i][ids[i]]).square().mean();loss.backward()
        grad=torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True);optimizer.step();counts[i]+=1
        if step%640==0:
            report['trace'].append(dict(step=step,loss=float(loss.detach()),gradient_norm=float(grad)))
            write_json(out/'report.json',report)
        if step in SNAPSHOTS:snapshot(step)
    assert counts==[3276]*10
    if gpu:torch.cuda.synchronize()
    report.update(complete=True,context_exposures=counts,seconds=time.monotonic()-start,
                  peak_allocated_bytes=torch.cuda.max_memory_allocated() if gpu else None)
    write_json(out/'report.json',report)


def evaluate_task_readout(root,index):
    runtime=guarded_hip_runtime();lock=verify_task_lock(root)
    cases=json.loads((root/'evaluation_labels.json').read_text())['cases'];store=FactorTeacherStore(Path(lock['teachers']))
    # One matched arm/seed per worker, evaluate both architectures.
    arm=('restricted','expanded')[index//2];seed=SEEDS[index%2]
    jobs=[j for j in lock['jobs'] if j['arm']==arm and j['seed']==seed]
    models=[]
    for job in jobs:
        run=root/'runs'/job['id'];r=json.loads((run/'report.json').read_text());assert r['complete']
        end=r['history'][-1];assert end['step']==32760 and sha256(Path(end['checkpoint']))==end['sha256']
        packet=torch.load(end['checkpoint'],map_location='cpu',weights_only=False)
        model=make_task_model(job['architecture']).cuda().eval().requires_grad_(False);model.load_state_dict(packet['state_dict'])
        models.append((job,model,end))
    results=[];start=time.monotonic()
    with torch.no_grad():
        for c in cases:
            data=context_task_input(store,lock,c,'cuda');ids=[i for i in range(20) if i!=c['wt']]
            names=[lock['aa'][i] for i in ids];target=np.array(c['target_delta'])[:,ids]
            for job,model,end in models:
                pred=task_prediction(model,job['architecture'],data,c['wt'])*job['scale']
                assert pred[c['wt']]==0 and torch.isfinite(pred).all()
                raw=pred.cpu().numpy().astype(float);replay_error=None
                if [c['parent_index'],c['position']] in job['train_sites']:
                    old=next(x for x in end['sites'] if (x['parent_index'],x['position'])==(c['parent_index'],c['position']))
                    replay_error=float(np.max(np.abs(raw-old['predicted_delta'])));assert replay_error<1e-5
                elapsed=[]
                if c is cases[0]:
                    for n in range(24):
                        torch.cuda.synchronize();t=time.perf_counter();task_prediction(model,job['architecture'],data,c['wt']);torch.cuda.synchronize()
                        if n>=4:elapsed.append(time.perf_counter()-t)
                selection=noise_selection(target,np.repeat(raw[None,ids],4,axis=0),names)
                chosen=int(ids[np.argmin(raw[ids])])
                results.append(dict(job=job['id'],parent_index=c['parent_index'],position=c['position'],pdb_id=c['pdb_id'],
                                    predicted_delta=raw.tolist(),selection=selection,train_replay_error=replay_error,
                                    selected_aa=lock['aa'][chosen],selected_teacher_geometry=[g[chosen] for g in c['teacher_geometry']],
                                    head_only_warm_latency_samples=elapsed))
            del data;store.cache.clear()
    write_json(root/f'evaluation_{index}.json',dict(complete=True,runtime=runtime,results=results,seconds=time.monotonic()-start,
                                                  s1_calls=0,c4_calls=0,oracle_target_s=False))


def collect_task_readout(root):
    lock=verify_task_lock(root);results=[]
    for i in range(4):
        r=json.loads((root/f'evaluation_{i}.json').read_text());assert r['complete'];results+=r['results']
    assert len(results)==8*48
    write_json(root/'report.json',dict(complete=True,results=results,structures_generated=0,
                                      deployment_accepted=False,oracle_target_s=False,s1_calls=0,c4_calls=0))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--mode',choices=['prepare','train','eval','collect'],required=True);p.add_argument('--job');p.add_argument('--index',type=int)
    a=p.parse_args()
    if a.mode=='prepare':prepare_task_readout(a.root)
    elif a.mode=='train':train_task_readout(a.root,a.job)
    elif a.mode=='eval':evaluate_task_readout(a.root,a.index)
    else:collect_task_readout(a.root)
