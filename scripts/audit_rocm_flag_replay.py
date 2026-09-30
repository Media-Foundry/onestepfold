#!/usr/bin/env python3
"""Match parameter gradient flags without changing weights or weakening replay tolerances."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256,write_json


def audit_rocm_gradient_flag_replay(root,arm):
    from fastglycan import stage0_confirm_runtime as rt
    from fastglycan.models.differentiable_mini import diffusion_from_conditioning
    from fastglycan.folding_scale import load_folding_scale_terminal
    from train_folding_scale import folding_training_input
    torch.set_num_threads(1)
    lock=json.loads((root/'lock.json').read_text());train=Path(lock['train'])/arm
    tl=json.loads((train/'lock.json').read_text())
    folder=root/f'flag_replay_{arm}';folder.mkdir(exist_ok=False)
    runner=rt.runner_setup(folder/'work');runner.configs.dtype='fp32';model=runner.model.eval().requires_grad_(False)
    before={n:hashlib.sha256(p.detach().cpu().numpy().tobytes()).hexdigest() for n,p in model.named_parameters()}
    checkpoint=lock['checkpoints'][arm];assert sha256(Path(checkpoint['path']))==checkpoint['sha256']
    state=torch.load(checkpoint['path'],map_location='cpu',weights_only=False)
    load_folding_scale_terminal(model,state,arm='expanded',expected_names=lock['selected_names'][arm],lock_sha256=lock['checkpoint_training_locks'][arm])
    assert all(torch.equal(model.get_parameter(n).detach().cpu(),v) for n,v in state['trained'].items())
    assert all(hashlib.sha256(p.detach().cpu().numpy().tobytes()).hexdigest()==before[n] for n,p in model.named_parameters() if n not in state['trained'])
    probe=train/'expanded/probe_2048/report.json';records=json.loads(probe.read_text())['records']
    assert len(records)==64;out=[];verified=set()
    for r in records:
        g,seed=r['group_id'],r['seed']
        features,cond,noise,labels,teacher,atoms=folding_training_input(tl,g,seed,verified)
        row=dict(group_id=g,seed=seed,states={})
        for flag in [False,True]:
            for n in lock['selected_names'][arm]:model.get_parameter(n).requires_grad_(flag)
            cpu=torch.get_rng_state().clone();gpu=torch.cuda.get_rng_state().clone()
            with torch.no_grad():x=diffusion_from_conditioning(model,features,noise.clone(),cond,steps=1).reshape(-1,3)
            assert torch.equal(cpu,torch.get_rng_state()) and torch.equal(gpu,torch.cuda.get_rng_state())
            file=folder/f'{g}_{seed}_{flag}.npy';np.save(file,x.cpu().numpy())
            reference=probe.parent/f'{g}_{seed}.npy' if flag else root/'examples'/g/f'{arm}_seed{seed}.npy'
            exact=sha256(file)==sha256(reference)
            row['states'][str(flag)]=dict(exact=exact,sha256=sha256(file),reference_sha256=sha256(reference),
                max_abs=float(np.abs(np.load(file).astype(float)-np.load(reference)).max()))
        out.append(row)
        write_json(folder/'progress.json',dict(records=out,complete=False))
        del features,cond,noise,labels,teacher,atoms,x;torch.cuda.empty_cache()
    assert all(torch.equal(model.get_parameter(n).detach().cpu(),v) for n,v in state['trained'].items())
    assert all(hashlib.sha256(p.detach().cpu().numpy().tobytes()).hexdigest()==before[n] for n,p in model.named_parameters() if n not in state['trained'])
    assert all(p.grad is None for p in model.parameters())
    passed=all(v['exact'] for r in out for v in r['states'].values())
    write_json(folder/'report.json',dict(complete=True,matched_state_exact=passed,records=out,arm=arm,nfe=128,
        parameter_updates=0,parameters_unchanged=True,checkpoint_sha256=checkpoint['sha256'],
        script_sha256=sha256(Path(__file__)),protocol_sha256=sha256(root/'replay_tools/mini_folding_rocm_replay_addendum_v1.md'),
        original_cross_state_gate_passed=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--arm',choices=['weak','strong'],required=True)
    a=p.parse_args();audit_rocm_gradient_flag_replay(a.root,a.arm)
