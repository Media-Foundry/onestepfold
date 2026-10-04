"""Fixed saved-state gradient probes; never calls optimizer.step."""
import argparse,json,time
from pathlib import Path
import numpy as np
import torch
from fastglycan.hip_device_policy import guarded_hip_runtime
from fastglycan.paired_teacher_protocol import sha256,write_json
from run_context_replication import replication_inputs
from run_task_readout import make_task_model,task_prediction


def probe_objective_gradients(root,out,jobid):
    runtime=guarded_hip_runtime();torch.set_num_threads(1)
    load=lambda p:json.loads(p.read_text())
    assert load(root/'execution.json')['complete'] and load(root/'independent_audit.json')['complete']
    lock=load(root/'lock.json');manifest=load(root/'label_manifest.json');job=next(j for j in lock['jobs'] if j['id']==jobid)
    assert job['size']==32
    path=root/'train_n32.json';assert sha256(path)==manifest['files'][str(path)]
    cases=load(path)['cases'];run=load(root/'runs'/jobid/'report.json')
    data=replication_inputs(root,lock,manifest,cases,'cuda',set(job['parents'])) if job['architecture']=='context' else [None]*len(cases)
    rows=[];hashes={};start=time.monotonic()
    for step in [0,32768,job['steps']]:
        snap=next(h for h in run['history'] if h['step']==step)
        cp=root/'runs'/jobid/('initial.pt' if step==0 else f'checkpoint_{step}.pt')
        expected=run['initial_sha256'] if step==0 else snap['sha256'];assert sha256(cp)==expected;hashes[str(cp)]=expected
        pkt=torch.load(cp,map_location='cpu',weights_only=False);net=make_task_model(job['architecture']).cuda().eval();net.load_state_dict(pkt['state_dict'])
        named=list(net.named_parameters());params=[p for _,p in named]
        for i,c in enumerate(cases):
            ids=[a for a in range(20) if a!=c['wt']]
            y=torch.tensor(np.mean(c['target_delta'],axis=0)[ids]/job['scale'],dtype=torch.float32,device='cuda')
            raw=task_prediction(net,job['architecture'],data[i],c['wt']);p=raw[ids]
            reference=next(v for v in snap['sites'] if (v['parent_index'],v['position'])==(c['parent_index'],c['position']))
            replay=float(np.max(abs((raw*job['scale']).detach().cpu().numpy()-np.array(reference['predicted_delta']))));assert replay<1e-5,replay
            lm=(p.mean()-y.mean()).square();lc=((p-p.mean())-(y-y.mean())).square().mean()
            gm=torch.autograd.grad(lm,params,retain_graph=True,allow_unused=True)
            gc=torch.autograd.grad(lc,params,allow_unused=True)
            acc=torch.zeros(5,dtype=torch.float64,device='cuda')
            for (name,param),m,cg in zip(named,gm,gc):
                if m is None:m=torch.zeros_like(param)
                if cg is None:cg=torch.zeros_like(param)
                md=m.double();cd=cg.double();g=md+cd
                acc[0]+=(g*g).sum();acc[1]+=(md*md).sum();acc[2]+=(cd*cd).sum();acc[3]+=(md*cd).sum()
                if name.startswith('score.'):acc[4]+=(g*g).sum()
            total,mean,center,dot,score=acc.cpu().tolist();norm=total**.5
            rows.append(dict(job=jobid,step=step,parent_index=cases[i]['parent_index'],position=cases[i]['position'],
                             source_aa=cases[i]['source_aa'],gradient_norm=norm,mean_gradient_norm=mean**.5,
                             centered_gradient_norm=center**.5,mean_center_dot=dot,score_gradient_norm=score**.5,
                             clipped_norm=min(norm,1.),clip_scale=min(1.,1./max(norm,1e-30)),replay_error=replay))
            assert abs(total-(mean+center+2*dot))<1e-8*max(1,total)
        assert all(torch.equal(v.detach().cpu(),pkt['state_dict'][k]) for k,v in net.state_dict().items())
        assert sha256(cp)==expected
        write_json(out/f'{jobid}.json',dict(complete=False,rows=rows,runtime=runtime))
        del net
    write_json(out/f'{jobid}.json',dict(complete=True,rows=rows,runtime=runtime,checkpoint_hashes=hashes,parameters_unchanged=True,
                                      optimizer_updates=0,c4_calls=0,s1_calls=0,seconds=time.monotonic()-start))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--job',required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True);probe_objective_gradients(a.root,a.out,a.job)
