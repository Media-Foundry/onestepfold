#!/usr/bin/env python3
"""Measure scope-dependent execution differences without changing weights or gates."""
import argparse
import json
import inspect
from pathlib import Path
import time
import torch
import numpy as np
from fastglycan.paired_teacher_protocol import sha256, write_json


def diagnose_diffusion_scope_replay(root):
    from fastglycan import stage0_confirm_runtime as rt
    from fastglycan.models.soft_sequence_chart import device_tree
    from fastglycan.models.differentiable_mini import diffusion_from_conditioning
    from fastglycan.models.diffusion_scope import select_diffusion_scope
    from fastglycan.hybrid_proposals import identity_noise
    from fastglycan.adapter_supervision import adapter_loss_parts
    parent=root.parent/'diffusion_scope_preflight_v1_20260930'
    lock=json.loads((parent/'lock.json').read_text());row=lock['rows'][0];g=row['group_id']
    assert row['role']=='train'
    write_json(root/'lock.json',dict(parent_lock_sha256=sha256(parent/'lock.json'),row=row,
        cases=['frozen_grad','full_no_grad','full_grad','full_grad_repeat'],optimizer_updates=0,
        hashes={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.md']}))
    torch.set_num_threads(1);runner=rt.runner_setup(root/'work');runner.configs.dtype='fp32'
    model=runner.model.eval();eligible={n for n,p in model.named_parameters() if p.requires_grad}
    original={n:p.detach().cpu().clone() for n,p in model.named_parameters()};model.requires_grad_(False)
    data=Path(lock['cache'])/'examples'/g
    for p,digest in lock['cache_files'].items():
        if Path(p).parent==data:assert sha256(Path(p))==digest
    saved=torch.load(data/'conditioning.pt',map_location='cpu',weights_only=False)
    flat=saved['conditioning_flat'].cuda();features=device_tree(saved['features'],'cuda')
    conditioning=tuple(x.reshape(s) for x,s in zip(flat.split(saved['sizes']),saved['shapes']))
    atoms=torch.load(Path(lock['source'])/'chemistry'/g/'native.pt',map_location='cpu',weights_only=False)['atoms']
    noise=identity_noise(atoms,lock['seed'],device='cuda')
    native=np.load(data/f's1_seed{lock["seed"]}.npy')
    labels=torch.load(data/'gt_supervision.pt',map_location='cpu',weights_only=False)
    teacher=torch.as_tensor(np.load(data/f's2_seed{lock["seed"]}.npy'),device='cuda')
    baseline={};traces={};counts={};active='';handles=[];order=[];capture_enabled=True
    def capture(name):
        def hook(module,inputs,output):
            if not capture_enabled:return
            count=counts.get(name,0);counts[name]=count+1
            values=output if isinstance(output,(tuple,list)) else [output]
            for i,value in enumerate(values):
                if not isinstance(value,torch.Tensor):continue
                key=f'{name}:{count}:{i}';v=value.detach().cpu()
                if active=='frozen_grad':baseline[key]=v.clone();order.append(key)
                else:
                    b=baseline[key];delta=v.double()-b.double()
                    traces[active][key]=dict(exact=torch.equal(v,b),max_abs=float(delta.abs().max()),
                        relative_l2=float(delta.norm()/b.double().norm().clamp_min(1e-30)))
        return hook
    for name,module in model.diffusion_module.named_modules():
        if name and ('.' not in name or name.startswith('diffusion_conditioning.') and name.count('.')==1):
            handles.append(module.register_forward_hook(capture(name)))
    results={};coordinates={};start=time.monotonic()
    cpu_rng=torch.get_rng_state();gpu_rng=torch.cuda.get_rng_state()
    for active in ['frozen_grad','full_no_grad','full_grad','full_grad_repeat']:
        if active=='full_no_grad':selected=select_diffusion_scope(model,'diffusion_dense',native_trainable_names=eligible)
        counts={};traces[active]={};capture_enabled=True
        with torch.set_grad_enabled(active!='full_no_grad'):
            x=diffusion_from_conditioning(model,features,noise,conditioning,steps=1).reshape(-1,3)
            a=x.detach().cpu().numpy();np.save(root/f'{active}.npy',a);coordinates[active]=a.copy()
            delta=a.astype(float)-native.astype(float)
            results[active]=dict(cache_exact=np.array_equal(a,native),max_abs=float(np.abs(delta).max()),
                atom_rms=float(np.sqrt(np.mean(np.sum(delta**2,axis=-1)))),requires_grad=x.requires_grad)
            write_json(root/'partial.json',dict(cases=results,traces=traces,trace_order=order))
            if active=='full_grad':
                parts=adapter_loss_parts(x,labels,teacher,smooth_temperature=.1)
                loss=sum(lock['weights'][k]*v for k,v in parts.items())
                capture_enabled=False  # backward checkpoint recomputation is not a new forward probe
                gradients=torch.autograd.grad(loss,list(selected.values()),allow_unused=True)
                stats={n:dict(present=v is not None,finite=bool(torch.isfinite(v).all()) if v is not None else None,
                    norm=float(v.double().norm()) if v is not None else None) for n,v in zip(selected,gradients)}
                write_json(root/'gradients.json',stats)
                results[active].update(loss=float(loss),parts={k:float(v) for k,v in parts.items()},
                    missing=[n for n,v in stats.items() if not v['present']],
                    nonfinite=[n for n,v in stats.items() if v['finite'] is False],
                    zeros=[n for n,v in stats.items() if v['norm']==0])
                del gradients,parts,loss
        del x
        assert torch.equal(cpu_rng,torch.get_rng_state()) and torch.equal(gpu_rng,torch.cuda.get_rng_state())
    for h in handles:h.remove()
    assert all(torch.equal(p.detach().cpu(),original[n]) for n,p in model.named_parameters())
    assert np.array_equal(coordinates['full_grad'],coordinates['full_grad_repeat'])
    imported={inspect.getfile(type(m)) for m in model.diffusion_module.modules()}
    write_json(root/'report.json',dict(complete=True,cases=results,traces=traces,trace_order=order,
        imported_sources={p:sha256(Path(p)) for p in sorted(imported)},
        weights_unchanged=True,repeat_exact=True,optimizer_updates=0,seconds=time.monotonic()-start))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args()
    diagnose_diffusion_scope_replay(a.root)
