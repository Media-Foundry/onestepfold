#!/usr/bin/env python3
"""Bounded first-failure replay diagnostic; no training, thresholds, or release changes."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.teacher_pairing import feature_digest,tensor_digest


def diagnose_rocm_replay(root):
    from fastglycan import stage0_confirm_runtime as rt
    from fastglycan.models.differentiable_mini import diffusion_from_conditioning
    from fastglycan.models.soft_sequence_chart import device_tree
    from fastglycan.folding_scale import load_folding_scale_terminal
    from fastglycan.hybrid_proposals import identity_noise
    from train_folding_scale import folding_training_input
    torch.set_num_threads(1)
    lock=json.loads((root/'lock.json').read_text());train=Path(lock['train'])/'weak'
    tl=json.loads((train/'lock.json').read_text())
    # First rejected original probe; not chosen by quality.
    g='b39dc28758a783962593c6afc6fbc268be4a05b05f3bbbea4cceb5b6440f940d';seed=600001
    folder=root/'replay_diagnostic';folder.mkdir(exist_ok=False)
    runner=rt.runner_setup(folder/'work');runner.configs.dtype='fp32';model=runner.model.eval().requires_grad_(False)
    before={n:hashlib.sha256(p.detach().cpu().numpy().tobytes()).hexdigest() for n,p in model.named_parameters()}
    state=torch.load(lock['checkpoints']['weak']['path'],map_location='cpu',weights_only=False)
    assert sha256(Path(lock['checkpoints']['weak']['path']))==lock['checkpoints']['weak']['sha256']
    load_folding_scale_terminal(model,state,arm='expanded',expected_names=lock['selected_names']['weak'],lock_sha256=lock['checkpoint_training_locks']['weak'])
    assert all(torch.equal(model.get_parameter(n).detach().cpu(),v) for n,v in state['trained'].items())
    assert all(hashlib.sha256(p.detach().cpu().numpy().tobytes()).hexdigest()==before[n] for n,p in model.named_parameters() if n not in state['trained'])
    archived=np.load(train/f'expanded/probe_2048/{g}_{seed}.npy')
    evaluated=np.load(root/f'examples/{g}/weak_seed{seed}.npy');records=[];inputs={};outputs={}
    for path in ['evaluation','training']:
        if path=='evaluation':
            data=Path(lock['cache'])/'examples'/g
            saved=torch.load(data/'conditioning.pt',map_location='cpu',weights_only=False)
            flat=saved['conditioning_flat'].cuda();features=device_tree(saved['features'],'cuda')
            cond=tuple(x.reshape(s) for x,s in zip(flat.split(saved['sizes']),saved['shapes']))
            atoms=torch.load(Path(lock['source'])/'chemistry'/g/'native.pt',map_location='cpu',weights_only=False)['atoms']
            noise=identity_noise(atoms,seed,device='cuda')
        else:
            features,cond,noise,labels,teacher,atoms=folding_training_input(tl,g,seed,set())
        inputs[path]=dict(conditioning=feature_digest(cond),features=feature_digest(features),noise=tensor_digest(noise))
        for flag in [False,True]:
            for n in lock['selected_names']['weak']:model.get_parameter(n).requires_grad_(flag)
            with torch.no_grad():
                x=diffusion_from_conditioning(model,features,noise.clone(),cond,steps=1).reshape(-1,3)
                y=diffusion_from_conditioning(model,features,noise.clone(),cond,steps=1).reshape(-1,3)
            array=x.cpu().numpy();name=f'{path}_requires_grad_{flag}.npy';np.save(folder/name,array)
            outputs[name]=array
            records.append(dict(path=path,selected_requires_grad=flag,repeat_exact=torch.equal(x,y),
                training_exact=bool(np.array_equal(array,archived)),evaluation_exact=bool(np.array_equal(array,evaluated)),
                training_max_abs=float(np.abs(array.astype(float)-archived).max()),
                evaluation_max_abs=float(np.abs(array.astype(float)-evaluated).max()),coordinate_sha256=sha256(folder/name)))
    assert inputs['training']==inputs['evaluation']
    write_json(folder/'report.json',dict(complete=True,group_id=g,arm='weak',seed=seed,parameter_updates=0,
        nfe=8,inputs=inputs,records=records,checkpoint_sha256=lock['checkpoints']['weak']['sha256'],
        script_sha256=sha256(Path(__file__)),scope='bounded diagnostic; original terminal exact gate unchanged'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    diagnose_rocm_replay(p.parse_args().root)
