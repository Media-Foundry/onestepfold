"""Latent-only, bounded memorization ladder on existing TRAIN teachers."""
import argparse,time,json
from pathlib import Path
import numpy as np
import torch
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.factor_student_data import FactorTeacherStore
from fastglycan.factor_student import FactorStudent,expand_pair_factors
from fastglycan.factor_memorization import canonical_pair_factors,aligned_factor_loss,response_nmse


def run_memorization(root,index,stage):
    lock=rt.load_json(root/'lock.json');torch.set_num_threads(1)
    for p,h in lock['code_hashes'].items():assert sha256(Path(p))==h,p
    arm=['reconstruction','canonical','free_factors'][index//2];seed=lock['init_seeds'][index%2]
    assert stage in range(4) and (stage==0 or arm!='free_factors')
    if stage:
        gate=rt.load_json(root/f'ladder_gate_{stage-1}.json');assert gate['advance']
    out=root/f'stage_{stage}_{index}';out.mkdir(exist_ok=False);start=time.monotonic()
    store=FactorTeacherStore(Path(lock['teachers']),training_only=True);aa=store.lock['aa'];data=[]
    for pi,pos in lock['stages'][stage]:
        row=store.rows[pi];wt=store.load(pi);wts,wtz=[x.cuda() for x in wt['conditioning'][1:]]
        ids=[j for j,a in enumerate(aa) if a!=row['sequence'][pos]]
        target=torch.stack([store.load(pi,pos,aa[j])['conditioning'][2].cuda()-wtz for j in ids])
        tu,tv,groups,evidence=canonical_pair_factors(target,lock['rank'],lock['gap_tolerance'])
        oracle=expand_pair_factors(tu,tv);floor=response_nmse(oracle,target)
        data.append(dict(pi=pi,pos=pos,s=wts,z=wtz,wt=aa.index(row['sequence'][pos]),ids=ids,target=target,tu=tu,tv=tv,groups=groups,evidence=evidence,floor=floor))
    torch.manual_seed(seed);net=FactorStudent(rank=lock['rank']).cuda()
    if arm=='free_factors':
        d=data[0]
        with torch.no_grad():u,v=net(d['s'],d['z'],d['pos'],d['wt'],d['ids'])
        free=torch.nn.ParameterList([torch.nn.Parameter(u.clone()),torch.nn.Parameter(v.clone())]);parameters=list(free.parameters());lr=lock['free_lr'];wd=0.
    else:parameters=list(net.parameters());lr=lock['lr'];wd=lock['weight_decay']
    optimizer=torch.optim.AdamW(parameters,lr=lr,weight_decay=wd,eps=1e-8)
    report=dict(complete=False,arm=arm,seed=seed,stage=stage,lock_sha256=sha256(root/'lock.json'),history=[],
                sites=[dict(parent_index=d['pi'],position=d['pos'],oracle_floor=d['floor'].tolist(),svd=d['evidence']) for d in data],
                parameters=sum(p.numel() for p in parameters),s1_calls=0,c4_calls=0,lr=lr,weight_decay=wd)
    def predict(d):return tuple(free) if arm=='free_factors' else net(d['s'],d['z'],d['pos'],d['wt'],d['ids'])
    def snapshot(step):
        with torch.no_grad():
            metrics=[]
            for d in data:
                u,v=predict(d);nmse=response_nmse(expand_pair_factors(u,v),d['target'])
                metrics.append(dict(parent_index=d['pi'],position=d['pos'],nmse=nmse.tolist(),factor_loss=float(aligned_factor_loss(u,v,d['tu'],d['tv'],d['groups']))))
        report['history'].append(dict(step=step,sites=metrics,mean_nmse=float(np.mean([x for m in metrics for x in m['nmse']]))))
        write_json(out/'report.json',report)
    snapshot(0)
    for step in range(lock['updates']):
        d=data[step%len(data)];optimizer.zero_grad(set_to_none=True);u,v=predict(d)
        loss=aligned_factor_loss(u,v,d['tu'],d['tv'],d['groups']) if arm=='canonical' else response_nmse(expand_pair_factors(u,v),d['target']).mean()
        assert torch.isfinite(loss);loss.backward();gn=torch.nn.utils.clip_grad_norm_(parameters,lock['clip'],error_if_nonfinite=True);optimizer.step()
        if (step+1)%64==0:snapshot(step+1)
    torch.cuda.synchronize();path=out/'final.pt'
    torch.save(dict(state_dict=free.state_dict() if arm=='free_factors' else net.state_dict(),arm=arm,stage=stage,seed=seed,sites=lock['stages'][stage]),path)
    report.update(complete=True,seconds=time.monotonic()-start,peak_allocated_bytes=torch.cuda.max_memory_allocated(),checkpoint_sha256=sha256(path),final_gradient_norm=float(gn),exposures=lock['updates']*19)
    write_json(out/'report.json',report)


def gate_memorization(root,stage):
    lock=rt.load_json(root/'lock.json');reports=[rt.load_json(root/f'stage_{stage}_{i}/report.json') for i in range(4)]
    assert all(r['complete'] for r in reports)
    fits={arm:all(r['history'][-1]['mean_nmse']<=lock['advance_nmse'] for r in reports if r['arm']==arm) for arm in ['reconstruction','canonical']}
    write_json(root/f'ladder_gate_{stage}.json',dict(complete=True,stage=stage,criteria='same network arm mean full-response NMSE <= 0.1 in BOTH seeds',fits=fits,advance=any(fits.values()) and stage<3,values=[dict(arm=r['arm'],seed=r['seed'],nmse=r['history'][-1]['mean_nmse']) for r in reports]))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--index',type=int,default=0);p.add_argument('--stage',type=int,default=0);p.add_argument('--mode',choices=['run','gate'],default='run');a=p.parse_args()
    if a.mode=='run':run_memorization(a.root,a.index,a.stage)
    else:gate_memorization(a.root,a.stage)
