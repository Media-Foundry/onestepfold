#!/usr/bin/env python3
"""Two fixed-budget native S1 adapters; held-out targets are never read here."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import time
import traceback

import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.diffusion_recipe import resolve_diffusion_recipe


def prepare_diffusion_pilot(root):
    assert not (root/'lock.json').exists()
    cache=root.parent/'diffusion_learning_cache_v1_20260930'
    audit=json.loads((cache/'audit.json').read_text());cache_lock=json.loads((cache/'lock.json').read_text())
    assert audit['complete'] and audit['lock_sha256']==sha256(cache/'lock.json')
    assert audit['validation_outputs']==0 and audit['conditioning']==160
    rows=[r for r in cache_lock['rows'] if r['role']=='train'];assert len(rows)==128
    order=[]
    for epoch in range(1,17):
        ordered=sorted(rows,key=lambda r:hashlib.sha256(f'diffusion-pilot-v1:epoch:{epoch}:{r["group_id"]}'.encode()).hexdigest())
        order.extend(dict(epoch=epoch,group_id=r['group_id'],seed=cache_lock['train_seeds'][(epoch-1)%2]) for r in ordered)
    assert len(order)==2048
    cache_files={str(cache/'examples'/r['group_id']/name):digest for r in rows
        for name,digest in json.loads((cache/'examples'/r['group_id']/'report.json').read_text())['files'].items()}
    for path,digest in cache_files.items():assert sha256(Path(path))==digest
    hashes={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.md']}
    for file in ['differentiable_mini.py','diffusion_adapter.py','soft_sequence_chart.py']:
        assert sha256(root/'code/src/fastglycan/models'/file)==sha256(cache/'code/src/fastglycan/models'/file)
    assert sha256(root/'code/src/fastglycan/adapter_supervision.py')==sha256(cache/'code/src/fastglycan/adapter_supervision.py')
    write_json(root/'lock.json',dict(cache=str(cache),cache_lock_sha256=sha256(cache/'lock.json'),
        cache_audit_sha256=sha256(cache/'audit.json'),source=cache_lock['source'],rows=rows,order=order,
        cache_files=cache_files,hashes=hashes,weights_sha256=cache_lock['weights_sha256'],weight_stats=cache_lock['weight_stats'],
        arms=['gt','gt_s2'],epochs=16,exposures=2048,accumulation=4,updates=512,rank=8,adapter_seed=20260930,
        learning_rate=dict(peak=1e-5,warmup_updates=32,terminal=1e-6),
        loss_weights=dict(coordinate=.01,smooth_lddt=1.,bond=10.,chirality=1.,clash=.1,teacher=.0025),
        terminal_only=True,validation_during_training=False,checkpoints_every=32))


def train_diffusion_pilot(root,arm):
    from fastglycan import stage0_confirm_runtime as rt
    from fastglycan.models.soft_sequence_chart import device_tree
    from fastglycan.models.differentiable_mini import diffusion_from_conditioning
    from fastglycan.models.diffusion_adapter import attach_diffusion_adapter
    from fastglycan.hybrid_proposals import identity_noise
    from fastglycan.adapter_supervision import adapter_loss_parts
    lock=json.loads((root/'lock.json').read_text());assert arm in lock['arms']
    recipe=resolve_diffusion_recipe(lock,arm)
    temperature=lock.get('smooth_temperature_by_arm',{}).get(arm,0.1)
    assert math.isfinite(temperature) and temperature>0
    folder=root/arm;folder.mkdir(exist_ok=False);start=time.monotonic()
    report=dict(complete=False,arm=arm,recipe=recipe,smooth_temperature=temperature,updates=0,exposures=0,lock_sha256=sha256(root/'lock.json'))
    try:
        for path,digest in lock['hashes'].items():assert sha256(Path(path))==digest
        for path,stat in lock['weight_stats'].items():assert [Path(path).stat().st_size,Path(path).stat().st_mtime_ns]==stat
        cache=Path(lock['cache']);source=Path(lock['source'])
        assert sha256(cache/'audit.json')==lock['cache_audit_sha256'] and sha256(cache/'lock.json')==lock['cache_lock_sha256']
        torch.set_num_threads(1);runner=rt.runner_setup(folder/'work');runner.configs.dtype='fp32'
        model=runner.model.eval().requires_grad_(False)
        assert Path(runner.configs.load_checkpoint_dir).resolve()==(root.parent/'protenix_stage0_pkg/v1_1/runtime/checkpoint').resolve()
        assert all(p.dtype==torch.float32 for p in model.parameters() if p.is_floating_point())
        original={n:p.detach().cpu().clone() for n,p in model.named_parameters()}
        adapters=attach_diffusion_adapter(model,rank=lock['rank'],seed=lock['adapter_seed'])
        params=[p for a in adapters.values() for p in a.parameters()]
        assert sum(p.numel() for p in params)==835584
        assert {id(p) for p in params}=={id(p) for p in model.parameters() if p.requires_grad}
        counts=dict(pairformer=0,diffusion=0)
        ph=model.pairformer_stack.register_forward_hook(lambda *unused:counts.__setitem__('pairformer',counts['pairformer']+1))
        dh=model.diffusion_module.register_forward_hook(lambda *unused:counts.__setitem__('diffusion',counts['diffusion']+1))
        optimizer=torch.optim.AdamW(params,lr=1e-5,betas=(.9,.999),eps=1e-8,weight_decay=0)
        optimizer.zero_grad(set_to_none=True);verified=set();history=folder/'history.jsonl'
        torch.save({n:{k:v.detach().cpu() for k,v in a.state_dict().items()} for n,a in adapters.items()},folder/'initial.pt')
        report.update(trainable_parameters=835584,device=torch.cuda.get_device_name(0),torch_version=torch.__version__)
        for exposure,item in enumerate(lock['order'],1):
            before=time.monotonic();g=item['group_id'];seed=item['seed'];data=cache/'examples'/g
            assert next(r for r in lock['rows'] if r['group_id']==g)['role']=='train'
            if g not in verified:
                for path,digest in lock['cache_files'].items():
                    if Path(path).parent==data:assert sha256(Path(path))==digest
                verified.add(g)
            saved=torch.load(data/'conditioning.pt',map_location='cpu',weights_only=False)
            assert saved['role']=='train' and saved['group_id']==g
            features=device_tree(saved['features'],'cuda');flat=saved['conditioning_flat'].cuda()
            conditioning=tuple(x.reshape(s) for x,s in zip(flat.split(saved['sizes']),saved['shapes']))
            native=torch.load(source/'chemistry'/g/'native.pt',map_location='cpu',weights_only=False)
            noise=identity_noise(native['atoms'],seed,device='cuda')
            labels=torch.load(data/'gt_supervision.pt',map_location='cpu',weights_only=False)
            teacher=torch.as_tensor(np.load(data/f's2_seed{seed}.npy'),device='cuda') if recipe['teacher'] else None
            cpu_rng=torch.get_rng_state().clone();gpu_rng=torch.cuda.get_rng_state().clone()
            predicted=diffusion_from_conditioning(model,features,noise,conditioning,steps=1).reshape(-1,3)
            if exposure==1:
                assert np.array_equal(predicted.detach().cpu().numpy(),np.load(data/f's1_seed{seed}.npy')),'zero-adapter cache replay'
            parts=adapter_loss_parts(predicted,labels,teacher,smooth_temperature=temperature)
            loss=sum(recipe['weights'][name]*value for name,value in parts.items())
            assert torch.isfinite(loss)
            (loss/4).backward()
            assert torch.equal(cpu_rng,torch.get_rng_state()) and torch.equal(gpu_rng,torch.cuda.get_rng_state())
            assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in params)
            record=dict(exposure=exposure,epoch=item['epoch'],group_id=g,seed=seed,
                loss=float(loss.detach()),parts={k:float(v.detach()) for k,v in parts.items()})
            if exposure%4==0:
                update=exposure//4
                lr=1e-5*update/32 if update<=32 else 1e-6+.5*(1e-5-1e-6)*(1+math.cos(math.pi*(update-32)/480))
                lr*=recipe['lr_multiplier']
                for group in optimizer.param_groups:group['lr']=lr
                norm=torch.nn.utils.clip_grad_norm_(params,1.,error_if_nonfinite=True)
                optimizer.step();optimizer.zero_grad(set_to_none=True)
                report['updates']=update;record.update(update=update,lr=lr,unclipped_accumulated_grad_norm=float(norm))
                if update%32==0:
                    checkpoint=dict(schema='native_diffusion_learning_v1',arm=arm,update=update,exposures=exposure,
                        rank=8,adapter_seed=lock['adapter_seed'],trained={n:{k:v.detach().cpu() for k,v in a.state_dict().items()} for n,a in adapters.items()},
                        optimizer=optimizer.state_dict(),lock_sha256=sha256(root/'lock.json'))
                    temporary=folder/'checkpoint.tmp';torch.save(checkpoint,temporary);temporary.replace(folder/f'update_{update:04d}.pt')
                    del checkpoint
            record['seconds']=time.monotonic()-before
            with history.open('a') as out:out.write(json.dumps(record)+'\n')
            report.update(exposures=exposure,seconds=time.monotonic()-start,counts=counts,
                peak_gpu_bytes=torch.cuda.max_memory_allocated())
            write_json(folder/'report.json',report)
            del saved,features,flat,conditioning,native,noise,labels,teacher,predicted,parts,loss
            torch.cuda.empty_cache()
        assert counts==dict(pairformer=0,diffusion=2048) and report['updates']==512 and len(verified)==128
        assert all(p.grad is None for p in model.parameters() if not p.requires_grad)
        for name,value in original.items():
            current=model.get_parameter(name[:-7]+'.parametrizations.weight.original') if name.endswith('.weight') and name[:-7] in adapters else model.get_parameter(name)
            assert torch.equal(current.detach().cpu(),value),'base weight changed: '+name
        ph.remove();dh.remove()
        report.update(complete=True,base_parameters_unchanged=len(original),terminal_sha256=sha256(folder/'update_0512.pt'),
            history_sha256=sha256(history),validation_read=False)
    except Exception:report['error']=traceback.format_exc()
    finally:report['seconds']=time.monotonic()-start;write_json(folder/'report.json',report)
    if not report['complete']:raise RuntimeError(report.get('error','incomplete'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--mode',choices=['prepare','train'],required=True);p.add_argument('--arm');a=p.parse_args()
    assert Path(os.environ['PROTENIX_ROOT_DIR']).resolve()==(a.root.parent/'protenix_stage0_pkg/v1_1/runtime').resolve()
    assert os.environ.get('LAYERNORM_TYPE')=='torch'
    if a.mode=='prepare':prepare_diffusion_pilot(a.root)
    else:train_diffusion_pilot(a.root,a.arm)
