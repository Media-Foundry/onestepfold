"""Immutable bounded readout jobs; raw and R32 matrix-label errors kept separate."""
import argparse,json,time
from pathlib import Path
import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.factor_student_data import FactorTeacherStore
from fastglycan.deep_response_student import DeepResponseStudent,response_diagnostics
from fastglycan.response_readouts import FreeNodeReadout,NonlinearResponseReadout,oracle_matrix_target
from fastglycan.factor_memorization import response_nmse
from run_deep_validation_v2 import site_tensors
from fastglycan.hip_device_policy import guarded_hip_runtime as gpu_guard


def readout_data(store,pi,pos):
    d=site_tensors(store,pi,pos,oracle_floor=False);d['r32']=oracle_matrix_target(d['target'])
    return d


def make_readout(job,data):
    torch.manual_seed(job['seed'])
    if job['architecture']=='free_hidden':
        if len(data)!=1:raise ValueError('free hidden is single-site only')
        d=data[0];base=DeepResponseStudent(size='large',content=False).cuda();model=FreeNodeReadout(base,d['s'],d['z'],d['pos'],d['wt']);del base
        return model.cuda()
    return NonlinearResponseReadout(job['architecture']).cuda()


def readout_predict(model,d,ids=None):
    return model(d['s'],d['z'],d['pos'],d['wt'],d['ids'] if ids is None else ids)


def matrix_metrics(pred,d,label):
    return dict(raw=response_diagnostics(pred,d['target']),label=response_diagnostics(pred,d['target'] if label=='raw' else d['r32']))


def train_readout(root,jobid):
    runtime=gpu_guard();lock=json.loads((root/'lock.json').read_text());job=json.loads((root/'jobs'/f'{jobid}.json').read_text())
    for p,h in lock['code_hashes'].items():assert sha256(Path(p))==h
    out=root/'runs'/jobid;out.mkdir(parents=True,exist_ok=False);store=FactorTeacherStore(Path(lock['teachers']),training_only=True);data=[readout_data(store,*x) for x in job['sites']];model=make_readout(job,data);opt=torch.optim.AdamW(model.parameters(),lr=1e-3,weight_decay=1e-4,eps=1e-8);parameters=list(model.parameters());start=time.monotonic()
    report=dict(complete=False,job=job,runtime=runtime,parameters=sum(p.numel() for p in parameters),history=[],trace=[],s1_calls=0,c4_calls=0,lock_sha256=sha256(root/'lock.json'),job_sha256=sha256(root/'jobs'/f'{jobid}.json'),oracle_raw_floor=[response_diagnostics(d['r32'],d['target']) for d in data])
    def snapshot(step):
        with torch.no_grad():metrics=[dict(parent_index=d['pi'],position=d['pos'],**matrix_metrics(readout_predict(model,d),d,job['label'])) for d in data]
        row=dict(step=step,sites=metrics,raw_nmse=float(np.mean([m['raw']['mean_nmse'] for m in metrics])),label_nmse=float(np.mean([m['label']['mean_nmse'] for m in metrics])),seconds=time.monotonic()-start)
        if step:
            path=out/f'checkpoint_{step}.pt';torch.save(dict(state_dict=model.state_dict(),optimizer=opt.state_dict(),rng=torch.get_rng_state(),cuda_rng=torch.cuda.get_rng_state(),job=job,step=step),path);row.update(checkpoint=str(path),sha256=sha256(path))
        report['history'].append(row);write_json(out/'report.json',report)
    snapshot(0)
    for step in range(1,8193):
        d=data[(step-1)%len(data)];target=d['target'] if job['label']=='raw' else d['r32'];opt.zero_grad(set_to_none=True);pred=readout_predict(model,d);loss=response_nmse(pred,target).mean();loss.backward();gn=torch.nn.utils.clip_grad_norm_(parameters,1.,error_if_nonfinite=True);monitor=step%64==0
        if monitor:before=[p.detach().clone() for p in parameters]
        opt.step()
        if monitor:
            with torch.no_grad():ratio=(sum((p-b).double().square().sum() for p,b in zip(parameters,before))/sum(b.double().square().sum() for b in before).clamp_min(1e-30)).sqrt()
            report['trace'].append(dict(step=step,loss=float(loss),gradient_norm=float(gn),update_weight_norm_ratio=float(ratio),parent_index=d['pi'],position=d['pos'],**matrix_metrics(pred,d,job['label'])));del before;write_json(out/'report.json',report)
        if step in lock['checkpoints']:snapshot(step)
    torch.cuda.synchronize();train_seconds=time.monotonic()-start;latencies=[]
    with torch.no_grad():
        for rep in range(13):
            torch.cuda.synchronize();begin=time.monotonic();readout_predict(model,data[0],list(range(20)));torch.cuda.synchronize()
            if rep>=3:latencies.append(time.monotonic()-begin)
    report.update(complete=True,seconds=train_seconds,peak_allocated_bytes=torch.cuda.max_memory_allocated(),candidate_exposures=8192*19,head20_forward_seconds=latencies)
    write_json(out/'report.json',report)


def evaluate_readout(root,jobid):
    runtime=gpu_guard();lock=json.loads((root/'lock.json').read_text());job=json.loads((root/'jobs'/f'{jobid}.json').read_text());store=FactorTeacherStore(Path(lock['teachers']),training_only=True);cp=Path(job['checkpoint']);assert sha256(cp)==job['sha256'];state=torch.load(cp,map_location='cpu',weights_only=False);initial=readout_data(store,*state['job']['sites'][0]);model=make_readout(state['job'],[initial]);model.load_state_dict(state['state_dict']);model.eval();rows=[]
    with torch.no_grad():
        for pi,pos in job['sites']:
            d=readout_data(store,pi,pos);rows.append(dict(parent_index=pi,position=pos,**matrix_metrics(readout_predict(model,d),d,state['job']['label'])))
    write_json(root/'evaluations'/jobid/'report.json',dict(complete=True,job=job,runtime=runtime,sites=rows,raw_nmse=float(np.mean([x['raw']['mean_nmse'] for x in rows])),label_nmse=float(np.mean([x['label']['mean_nmse'] for x in rows])),s1_calls=0,c4_calls=0))


def preflight_readouts(root):
    runtime=gpu_guard();lock=json.loads((root/'lock.json').read_text());store=FactorTeacherStore(Path(lock['teachers']),training_only=True);d=readout_data(store,3,36);rows=[]
    for kind in ['free_hidden','pair','channel']:
        model=make_readout(dict(seed=231301,architecture=kind),[d]);opt=torch.optim.AdamW(model.parameters(),lr=1e-3);torch.cuda.reset_peak_memory_stats();start=time.monotonic()
        for step in range(24):
            opt.zero_grad(set_to_none=True);p=readout_predict(model,d);loss=response_nmse(p,d['target']).mean();loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True);opt.step()
            if step==3:torch.cuda.synchronize();start=time.monotonic()
        torch.cuda.synchronize();seconds=(time.monotonic()-start)/20
        with torch.no_grad():assert readout_predict(model,d,[d['wt']]).count_nonzero()==0
        rows.append(dict(kind=kind,parameters=sum(p.numel() for p in model.parameters()),step_seconds=seconds,loss=float(loss),peak_allocated_bytes=torch.cuda.max_memory_allocated()));del model,opt;torch.cuda.empty_cache()
    write_json(root/'preflight.json',dict(complete=True,runtime=runtime,models=rows,retained_checkpoints=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--mode',choices=['preflight','train','evaluate'],required=True);p.add_argument('--job');a=p.parse_args()
    if a.mode=='preflight':preflight_readouts(a.root)
    elif a.mode=='train':train_readout(a.root,a.job)
    else:evaluate_readout(a.root,a.job)
