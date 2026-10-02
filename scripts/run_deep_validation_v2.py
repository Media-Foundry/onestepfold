"""One immutable Deep Validation v2 job; all GPU jobs use HIP devices 0--5 only."""
import argparse,json,os,time
from pathlib import Path
import numpy as np
import torch
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.factor_student_data import FactorTeacherStore
from fastglycan.factor_student import expand_pair_factors
from fastglycan.factor_memorization import response_nmse
from fastglycan.deep_response_student import DeepResponseStudent,response_diagnostics


def gpu_guard():
    visible=os.environ.get('HIP_VISIBLE_DEVICES','')
    if visible not in tuple(map(str,range(6))) or 'CUDA_VISIBLE_DEVICES' in os.environ:
        raise RuntimeError('require HIP_VISIBLE_DEVICES=one of 0..5; CUDA_VISIBLE_DEVICES must be absent')
    if torch.cuda.device_count()!=1:raise RuntimeError('expected exactly one visible accelerator')
    torch.set_num_threads(1)
    return dict(hip_visible=visible,cuda_visible=None,torch=torch.__version__,hip=torch.version.hip,device=torch.cuda.get_device_name())


def site_tensors(store,pi,pos,oracle_floor=True):
    row=store.rows[pi];wt=store.load(pi);si,s,z=[x.cuda() for x in wt['conditioning']];aa=store.lock['aa'];wtid=aa.index(row['sequence'][pos]);ids=[a for a in range(20) if a!=wtid]
    targets=[store.load(pi,pos,aa[a]) for a in ids]
    delta=torch.stack([x['conditioning'][2].cuda()-z for x in targets])
    inputs=torch.stack([x['conditioning'][0].cuda() for x in targets])
    floor=None
    if oracle_floor:
        sigma=torch.linalg.svdvals(delta.double().permute(0,3,1,2));floor=(sigma[:,:,32:].square().sum((1,2))/sigma.square().sum((1,2))).tolist()
    return dict(pi=pi,pos=pos,si=si,s=s,z=z,wt=wtid,ids=ids,target=delta,inputs=inputs,floor=floor)


def predict_site(model,data):
    oracle=data['inputs'] if model.input_mode in ('site','full') else None
    return model(data['s'],data['z'],data['pos'],data['wt'],data['ids'],data['si'] if model.input_mode!='none' else None,oracle)


def build_job_model(job,data):
    torch.manual_seed(job['seed']);model=DeepResponseStudent(**job['architecture']).cuda()
    if job['kind']=='free':
        d=data[0]
        with torch.no_grad():uv=model.factors(d['s'],d['z'],d['pos'],d['wt'],d['ids'])
        parameters=torch.nn.ParameterList([torch.nn.Parameter(x.clone()) for x in uv]);return model,parameters
    if job.get('initial_checkpoint'):
        p=Path(job['initial_checkpoint']);assert sha256(p)==job['initial_sha256'];model.load_state_dict(torch.load(p,map_location='cuda',weights_only=False)['state_dict'])
    return model,model


def train_deep_job(root,jobid):
    runtime=gpu_guard();lock=rt.load_json(root/'lock.json');job=rt.load_json(root/'jobs'/f'{jobid}.json')
    for p,h in lock['code_hashes'].items():assert sha256(Path(p))==h,p
    store=FactorTeacherStore(Path(lock['teachers']),training_only=True);out=root/'runs'/jobid;out.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    data=[site_tensors(store,pi,pos) for pi,pos in job['train_sites']];model,optimized=build_job_model(job,data);parameters=list(optimized.parameters())
    optimizer=torch.optim.AdamW(parameters,lr=job['lr'],weight_decay=job['weight_decay'],eps=1e-8)
    report=dict(complete=False,job=job,runtime=runtime,parameters=sum(p.numel() for p in parameters),history=[],trace=[],s1_calls=0,c4_calls=0,lock_sha256=sha256(root/'lock.json'),job_sha256=sha256(root/'jobs'/f'{jobid}.json'),oracle_floors=[dict(parent_index=d['pi'],position=d['pos'],nmse=d['floor']) for d in data])
    def predict(d):return expand_pair_factors(*optimized) if job['kind']=='free' else predict_site(model,d)
    def snapshot(step):
        with torch.no_grad():metrics=[dict(parent_index=d['pi'],position=d['pos'],**response_diagnostics(predict(d),d['target'])) for d in data]
        entry=dict(step=step,sites=metrics,mean_nmse=float(np.mean([m['mean_nmse'] for m in metrics])),centered_nmse=float(np.mean([m['centered_nmse'] for m in metrics])),seconds=time.monotonic()-start)
        if step:
            cp=out/f'checkpoint_{step}.pt';torch.save(dict(state_dict=optimized.state_dict(),optimizer=optimizer.state_dict(),rng=torch.get_rng_state(),cuda_rng=torch.cuda.get_rng_state(),job=job,step=step),cp);entry.update(checkpoint=str(cp),checkpoint_sha256=sha256(cp))
        report['history'].append(entry);write_json(out/'report.json',report)
    snapshot(0)
    for step in range(1,job['steps']+1):
        d=data[(step-1)%len(data)];optimizer.zero_grad(set_to_none=True)
        prediction=predict(d);loss=response_nmse(prediction,d['target']).mean()
        loss.backward();gn=torch.nn.utils.clip_grad_norm_(parameters,1.,error_if_nonfinite=True)
        monitor=step%64==0
        if monitor:before=[p.detach().clone() for p in parameters]
        optimizer.step()
        if monitor:
            with torch.no_grad():
                update=sum((p-b).double().square().sum() for p,b in zip(parameters,before));weight=sum(b.double().square().sum() for b in before)
            report['trace'].append(dict(step=step,loss=float(loss),gradient_norm=float(gn),update_weight_norm_ratio=float((update/weight.clamp_min(1e-30)).sqrt()),**response_diagnostics(prediction,d['target']),seconds=time.monotonic()-start))
            del before
            write_json(out/'report.json',report)
        if step in lock['checkpoints'] or step==job['steps']:snapshot(step)
    torch.cuda.synchronize();report.update(complete=True,seconds=time.monotonic()-start,peak_allocated_bytes=torch.cuda.max_memory_allocated(),candidate_exposures=job['steps']*19)
    write_json(out/'report.json',report)


def evaluate_latent_job(root,jobid):
    runtime=gpu_guard();lock=rt.load_json(root/'lock.json');job=rt.load_json(root/'jobs'/f'{jobid}.json');out=root/'evaluations'/jobid;out.mkdir(parents=True,exist_ok=False)
    store=FactorTeacherStore(Path(lock['teachers']));cp=Path(job['checkpoint']);assert sha256(cp)==job['checkpoint_sha256'];packet=torch.load(cp,map_location='cuda',weights_only=False)
    model=DeepResponseStudent(**packet['job']['architecture']).cuda().eval();model.load_state_dict(packet['state_dict']);metrics=[]
    with torch.no_grad():
        for pi,pos in job['sites']:
            d=site_tensors(store,pi,pos,oracle_floor=False);metrics.append(dict(parent_index=pi,position=pos,role=store.rows[pi]['role'],**response_diagnostics(predict_site(model,d),d['target'])))
    write_json(out/'report.json',dict(complete=True,runtime=runtime,job=job,sites=metrics,mean_nmse=float(np.mean([x['mean_nmse'] for x in metrics])),centered_nmse=float(np.mean([x['centered_nmse'] for x in metrics])),s1_calls=0,c4_calls=0))


def preflight_deep_models(root):
    runtime=gpu_guard();lock=rt.load_json(root/'lock.json');store=FactorTeacherStore(Path(lock['teachers']),training_only=True);d=site_tensors(store,3,36,oracle_floor=False);reports=[]
    variants=[dict(size=size,content=content) for size in ['small','large'] for content in [False,True]]+[dict(output='dense')]+[dict(size='large',content=True,input_mode=m) for m in ['wt','site','full']]
    for arch in variants:
        torch.manual_seed(231301);model=DeepResponseStudent(**arch).cuda();opt=torch.optim.AdamW(model.parameters(),lr=3e-4)
        start=time.monotonic()
        for step in range(24):
            opt.zero_grad(set_to_none=True);p=predict_site(model,d);loss=response_nmse(p,d['target']).mean();loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True);opt.step()
            if step==3:torch.cuda.synchronize();start=time.monotonic()
        torch.cuda.synchronize();seconds=(time.monotonic()-start)/20
        with torch.no_grad():
            wt=model(d['s'],d['z'],d['pos'],d['wt'],[d['wt']],d['si'] if model.input_mode!='none' else None,d['si'][None] if model.input_mode in ('site','full') else None);assert torch.count_nonzero(wt)==0
        reports.append(dict(architecture=arch,parameters=sum(p.numel() for p in model.parameters()),step_seconds=seconds,loss=float(loss),peak_allocated_bytes=torch.cuda.max_memory_allocated()))
        del opt,model;torch.cuda.empty_cache()
    write_json(root/'preflight.json',dict(complete=True,runtime=runtime,variants=reports,retained_checkpoints=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--job');p.add_argument('--mode',choices=['train','evaluate','preflight'],required=True);a=p.parse_args()
    if a.mode=='train':train_deep_job(a.root,a.job)
    elif a.mode=='evaluate':evaluate_latent_job(a.root,a.job)
    else:preflight_deep_models(a.root)
