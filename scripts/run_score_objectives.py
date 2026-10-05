"""Frozen fixed-data A/B/C score objectives; no new folding or decoder work."""
import argparse,json,time
from pathlib import Path
import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.hip_device_policy import guarded_hip_runtime
from fastglycan.score_objectives import ARMS,training_site_weights,score_objective,clipping_counterfactual
from fastglycan.context_replication import AA
from fastglycan.multicontext_response import noise_selection
from run_context_replication import replication_inputs
from run_task_readout import make_task_model,task_prediction


def load(path):return json.loads(Path(path).read_text())


def prepare_score_objectives(root):
    assert not (root/'lock.json').exists();torch.set_num_threads(1)
    prior=root.parent/'context_replication_v1_20261005';old=load(prior/'lock.json')
    assert load(prior/'execution.json')['complete'] and load(prior/'independent_audit.json')['complete']
    train=load(prior/'train_n32.json');assert len(train['cases'])==128
    weights=training_site_weights(train['cases']);write_json(root/'weights.json',weights)
    # Only old TRAIN labels enter training and weight estimation.
    write_json(root/'train.json',train)
    jobs=[]
    for arm in ARMS:
        for oldjob in old['jobs']:
            if oldjob['size']!=32:continue
            job=dict(oldjob,id=f'{arm}_{oldjob["architecture"]}_s{oldjob["seed"]}',arm=arm,prior_job=oldjob['id'])
            jobs.append(job)
            torch.manual_seed(job['seed']);net=make_task_model(job['architecture'])
            oldcp=prior/'runs'/oldjob['id']/'initial.pt';rr=load(oldcp.parent/'report.json');assert sha256(oldcp)==rr['initial_sha256']
            pkt=torch.load(oldcp,map_location='cpu',weights_only=False)
            assert all(torch.equal(v,pkt['state_dict'][k]) for k,v in net.state_dict().items())
    for name in ['task_readout.py','deep_response_student.py']:
        assert sha256(root/'code/src/fastglycan'/name)==sha256(prior/'code/src/fastglycan'/name)
    sources={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ('.py','.md')}
    assets=[prior/p for p in ['lock.json','label_manifest.json','evaluation_labels.json','execution.json','independent_audit.json','train_n32.json']]+[root/'train.json',root/'weights.json']
    write_json(root/'lock.json',dict(schema='score_objectives_v1',prior=str(prior),prior_lock=old,jobs=jobs,
                                    weights=weights,code_hashes=sources,asset_hashes={str(p):sha256(p) for p in assets},
                                    expected=dict(runs=12,updates=12*131072,terminal_rows=1920,c4=0,s1=0),dev_previously_observed=True))


def verify_score_objectives(root):
    lock=load(root/'lock.json')
    for group in ['code_hashes','asset_hashes']:
        for p,h in lock[group].items():assert sha256(Path(p))==h,p
    return lock


def train_score_objectives(root,jobid):
    lock=verify_score_objectives(root);job=next(j for j in lock['jobs'] if j['id']==jobid)
    gpu=job['architecture']=='context';runtime=guarded_hip_runtime() if gpu else dict(device='cpu');device='cuda' if gpu else 'cpu';torch.set_num_threads(1)
    prior=Path(lock['prior']);cases=load(root/'train.json')['cases'];manifest=load(prior/'label_manifest.json')
    assert [[c['parent_index'],c['position']] for c in cases]==job['train_sites']
    assert all(c['role']=='train' and len(c['target_delta'])==2 for c in cases)
    data=replication_inputs(prior,lock['prior_lock'],manifest,cases,device,set(job['parents'])) if gpu else [None]*128
    ids=[torch.tensor([a for a in range(20) if a!=c['wt']],device=device) for c in cases]
    targets=[torch.tensor(np.mean(c['target_delta'],axis=0)/job['scale'],device=device,dtype=torch.float32) for c in cases]
    weights=[w['weight'] if job['arm']=='C' else 1. for w in lock['weights']['sites']]
    torch.manual_seed(job['seed']);model=make_task_model(job['architecture']).to(device)
    optimizer=torch.optim.AdamW(model.parameters(),lr=job['lr'],weight_decay=job['weight_decay'],eps=1e-8)
    out=root/'runs'/jobid;out.mkdir(parents=True,exist_ok=False)
    torch.save(dict(step=0,state_dict=model.state_dict(),job=job),out/'initial.pt')
    report=dict(complete=False,job=job,runtime=runtime,parameters=sum(p.numel() for p in model.parameters()),
                initial_sha256=sha256(out/'initial.pt'),history=[],trace=[],gradient_windows=[],source_lock_sha256=sha256(root/'lock.json'),
                train_sha256=sha256(root/'train.json'),weights_sha256=sha256(root/'weights.json'),c4_calls=0,s1_calls=0)
    counts=[0]*128;start=time.monotonic();keys=['unweighted_norm','weighted_norm','unweighted_post_norm','weighted_post_norm','post_vector_multiplier','both_clipped','weighted_clipped','unweighted_clipped']
    sums=np.zeros((128,len(keys)),dtype=np.float64);squared=np.zeros((128,4),dtype=np.float64);window_counts=np.zeros(128,dtype=int)
    def snapshot(step):
        sites=[]
        with torch.no_grad():
            for i,c in enumerate(cases):
                pred=task_prediction(model,job['architecture'],data[i],c['wt']);p=pred[ids[i]];y=targets[i][ids[i]]
                base,loss=score_objective(p,y,job['arm'],weights[i])
                assert torch.isfinite(pred).all() and pred[c['wt']]==0
                sites.append(dict(parent_index=c['parent_index'],position=c['position'],objective=float(loss),base_loss=float(base),
                                  normalized_mse=float((p-y).square().mean()),centered_mse=float(((p-p.mean())-(y-y.mean())).square().mean()),
                                  predicted_delta=(pred*job['scale']).cpu().tolist()))
        row=dict(step=step,sites=sites,exposures=list(counts),seconds=time.monotonic()-start)
        if step:
            cp=out/f'checkpoint_{step}.pt';torch.save(dict(step=step,state_dict=model.state_dict(),optimizer=optimizer.state_dict(),job=job,exposures=list(counts)),cp)
            row.update(checkpoint=str(cp),sha256=sha256(cp))
        report['history'].append(row);write_json(out/'report.json',report)
    snapshot(0)
    for step in range(1,job['steps']+1):
        i=(step-1)%128;optimizer.zero_grad(set_to_none=True)
        pred=task_prediction(model,job['architecture'],data[i],cases[i]['wt']);base,loss=score_objective(pred[ids[i]],targets[i][ids[i]],job['arm'],weights[i])
        loss.backward();gn=torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True)
        # clip_grad_norm_ returns the preclip norm; same-point unweighted is analytic.
        g=clipping_counterfactual(float(gn),weights[i]);optimizer.step();counts[i]+=1;window_counts[i]+=1
        sums[i]+=np.array([g[k] for k in keys]);squared[i]+=np.array([g[k] for k in keys[:4]])**2
        if step<=16 or step%640==0:
            report['trace'].append(dict(step=step,site=i,weight=weights[i],base_loss=float(base.detach()),loss=float(loss.detach()),
                                        prediction_range=float((pred.max()-pred.min()).detach()),**g))
            report.update(active_step=step,seconds=time.monotonic()-start);write_json(out/'report.json',report)
        if step%32768==0:
            report['gradient_windows'].append(dict(end_step=step,start_step=step-32768+1,keys=keys,counts=window_counts.tolist(),
                                                   sums=sums.tolist(),squared_norm_sums=squared.tolist()))
            sums.fill(0);squared.fill(0);window_counts.fill(0)
        if step in job['snapshots']:snapshot(step)
    assert counts==[1024]*128
    report.update(complete=True,context_exposures=counts,seconds=time.monotonic()-start,peak_allocated_bytes=torch.cuda.max_memory_allocated() if gpu else None)
    write_json(out/'report.json',report)


def evaluate_score_objectives(root,index):
    runtime=guarded_hip_runtime();lock=verify_score_objectives(root);prior=Path(lock['prior']);manifest=load(prior/'label_manifest.json')
    assert all(load(root/'runs'/j['id']/'report.json')['complete'] for j in lock['jobs'])
    cases=load(prior/'evaluation_labels.json')['cases'];results=[]
    for ji,job in enumerate(lock['jobs']):
        if ji%4!=index:continue
        run=load(root/'runs'/job['id']/'report.json');snap=run['history'][-1];assert snap['step']==131072
        cp=Path(snap['checkpoint']);assert sha256(cp)==snap['sha256'];pkt=torch.load(cp,map_location='cpu',weights_only=False)
        net=make_task_model(job['architecture']).cuda().eval().requires_grad_(False);net.load_state_dict(pkt['state_dict'])
        with torch.no_grad():
            for c in cases:
                data=replication_inputs(prior,lock['prior_lock'],manifest,[c],'cuda',set(range(40)))[0] if job['architecture']=='context' else None
                raw=(task_prediction(net,job['architecture'],data,c['wt'])*job['scale']).cpu().numpy().astype(float)
                assert np.isfinite(raw).all() and raw[c['wt']]==0
                ids=[a for a in range(20) if a!=c['wt']];target=np.array(c['target_delta'])[:,ids];p=raw[ids]
                selection=noise_selection(target,np.repeat(p[None],4,axis=0),[AA[a] for a in ids]);chosen=ids[int(np.argmin(p))]
                error=None
                if c['role']=='train':
                    saved=next(x for x in snap['sites'] if (x['parent_index'],x['position'])==(c['parent_index'],c['position']))
                    error=float(np.max(abs(raw-np.array(saved['predicted_delta']))));assert error<1e-5,error
                old=target[:2].mean(0)
                results.append(dict(job=job['id'],arm=job['arm'],architecture=job['architecture'],seed=job['seed'],step=job['steps'],
                                    category='train' if c['role']=='train' else 'development',parent_index=c['parent_index'],position=c['position'],pdb_id=c['pdb_id'],source_aa=c['source_aa'],
                                    predicted_delta=raw.tolist(),selection=selection,train_replay_error=error,selected_aa=AA[chosen],
                                    raw_old_mse=float(np.mean((p-old)**2)),centered_old_mse=float(np.mean(((p-p.mean())-(old-old.mean()))**2)),
                                    selected_teacher_geometry=[g[chosen] for g in c['teacher_geometry']]))
                del data
        del net
    write_json(root/f'evaluation_{index}.json',dict(complete=True,results=results,runtime=runtime,c4_calls=0,s1_calls=0))


def collect_score_objectives(root):
    lock=verify_score_objectives(root);results=[]
    for i in range(4):
        packet=load(root/f'evaluation_{i}.json');assert packet['complete'];results.extend(packet['results'])
    assert len(results)==1920 and len({(r['job'],r['parent_index'],r['position']) for r in results})==1920
    write_json(root/'report.json',dict(complete=True,results=results,model_promoted=False,student_coordinates=0,oracle_target_s=False,c4_calls=0,s1_calls=0))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--mode',required=True);p.add_argument('--job');p.add_argument('--index',type=int,default=0);a=p.parse_args()
    if a.mode=='prepare':prepare_score_objectives(a.root)
    elif a.mode=='train':train_score_objectives(a.root,a.job)
    elif a.mode=='eval':evaluate_score_objectives(a.root,a.index)
    elif a.mode=='collect':collect_score_objectives(a.root)
    else:raise ValueError(a.mode)
