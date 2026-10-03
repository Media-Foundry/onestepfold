"""Probe saved coverage checkpoints without an optimizer step or decoder call."""
import argparse,json,time
from pathlib import Path
import torch
from fastglycan.hip_device_policy import guarded_hip_runtime
from fastglycan.response_readouts import NonlinearResponseReadout
from fastglycan.student_probe import tensor_diversity,parameter_branch
from fastglycan.factor_student_data import FactorTeacherStore
from fastglycan.factor_memorization import response_nmse
from fastglycan.paired_teacher_protocol import sha256,write_json
from run_deep_validation_v2 import site_tensors


def audit_student_collapse(root,index):
    runtime=guarded_hip_runtime();lock=json.loads((root/'lock.json').read_text())
    for p,h in lock['code_hashes'].items():assert sha256(Path(p))==h
    prior=Path(lock['prior']);panel=json.loads((prior/'evaluation_lock.json').read_text());job=panel['jobs'][index]
    store=FactorTeacherStore(Path(panel['teachers']),training_only=True)
    out=root/f'probe_{index}';out.mkdir(exist_ok=False)
    data=[site_tensors(store,*site,oracle_floor=False) for site in job['train_sites']]
    run=prior/'runs'/job['id'];old=json.loads((run/'report.json').read_text())
    init=torch.load(run/'initial.pt',map_location='cpu',weights_only=False)['state_dict']
    paths=[run/'initial.pt']+[Path(h['checkpoint']) for h in old['history'][1:]]
    expected=[old['initial_sha256']]+[h['sha256'] for h in old['history'][1:]]
    start=time.monotonic();records=[];previous=init
    for path,expected_hash in zip(paths,expected):
        assert sha256(path)==expected_hash
        packet=torch.load(path,map_location='cpu',weights_only=False)
        net=NonlinearResponseReadout('pair').cuda().eval();net.load_state_dict(packet['state_dict'])
        changes={}
        for name,p in net.named_parameters():
            key=parameter_branch(name);z=changes.setdefault(key,dict(initial_delta_sq=0.,previous_delta_sq=0.,weight_sq=0.))
            cpu=p.detach().cpu().double();z['initial_delta_sq']+=float((cpu-init[name].double()).square().sum())
            z['previous_delta_sq']+=float((cpu-previous[name].double()).square().sum());z['weight_sq']+=float(cpu.square().sum())
        for d in data:
            captured={};hooks=[];calls={}
            def save(name):
                def hook(module,args,output):
                    n=calls.get(name,0);calls[name]=n+1;key=f'{name}:{n}'
                    captured[key]=output
                    if output.requires_grad:output.retain_grad()
                    if name in ('mix','readout.0','readout.2'):
                        captured[key+':input']=args[0]
                        if args[0].requires_grad:args[0].retain_grad()
                return hook
            modules=dict(net.named_modules())
            names=['query','mix',*[f'blocks.{i}' for i in range(4)],'left','right','aa_readout','readout.0','readout.1','readout.2','readout.3']
            for name in names:hooks.append(modules[name].register_forward_hook(save(name)))
            net.zero_grad(set_to_none=True)
            prediction=net(d['s'],d['z'],d['pos'],d['wt'],d['ids'])
            loss=response_nmse(prediction,d['target']).mean();loss.backward()
            layers={}
            for name,value in captured.items():
                st=tensor_diversity(value)
                st['gradient_norm']=float(value.grad.double().norm()) if value.grad is not None else None
                st['gradient_nonzero']=int(value.grad.count_nonzero()) if value.grad is not None else None
                layers[name]=st
            gradients={}
            for name,p in net.named_parameters():
                key=parameter_branch(name);v=gradients.setdefault(key,dict(gradient_sq=0.,nonzero=0,missing=0))
                if p.grad is None:v['missing']+=1
                else:v['gradient_sq']+=float(p.grad.double().square().sum());v['nonzero']+=int(p.grad.count_nonzero())
            records.append(dict(job=job['id'],step=packet['step'],parent_index=d['pi'],position=d['pos'],loss=float(loss),
                                checkpoint_sha256=expected_hash,layers=layers,gradients=gradients,parameter_changes=changes))
            for hook in hooks:hook.remove()
            captured.clear();del prediction,loss
            write_json(out/'status.json',dict(complete=False,records=len(records),seconds=time.monotonic()-start))
        previous=packet['state_dict'];del net
    write_json(out/'report.json',dict(complete=True,runtime=runtime,job=job['id'],records=records,
               seconds=time.monotonic()-start,optimizer_steps=0,s1_calls=0,c4_calls=0,
               peak_allocated_bytes=torch.cuda.max_memory_allocated(),source_hashes=lock['code_hashes']))
    write_json(out/'status.json',dict(complete=True,records=len(records)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--index',type=int,required=True)
    a=p.parse_args();audit_student_collapse(a.root,a.index)
