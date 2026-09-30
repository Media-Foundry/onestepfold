#!/usr/bin/env python3
"""Fixed-budget native-parameter diffusion scope comparison, TRAIN only."""
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


def prepare_dense_diffusion(root):
    assert not (root/'lock.json').exists()
    parent=root.parent/'diffusion_recipe_scale_v1_20260930'
    lock=json.loads((parent/'lock.json').read_text());audit=json.loads((parent/'training_audit.json').read_text())
    assert audit['complete'] and audit['lock_sha256']==sha256(parent/'lock.json')
    preflights={}
    for arm,version in [('token_dense','v1'),('diffusion_dense','v2')]:
        r=root.parent/f'diffusion_scope_preflight_{version}_20260930'
        p=r/arm/'report.json';x=json.loads(p.read_text())
        assert x['complete'] and len(x['cases'])==2 and x['lock_sha256']==sha256(r/'lock.json')
        assert all(c['checkpoint_replay'] and c['excluded_frozen'] and c['zero_gradient_tensors']==0 for c in x['cases'])
        preflights[arm]=dict(path=str(p),sha256=sha256(p),selected_names=x['selected_names'],
            selected_tensors=x['selected_tensors'],selected_elements=x['selected_elements'])
    assert len(lock['rows'])==128 and all(r['role']=='train' for r in lock['rows']) and len(lock['order'])==2048
    lock.update(schema='native_dense_diffusion_training_v1',arms=['token_dense','diffusion_dense'],
        preflights=preflights,weights=lock['arm_recipes']['calibrated_high']['weights'],smooth_temperature=.1,
        learning_rate=dict(peak=1e-5,warmup_updates=32,terminal=1e-6),
        optimizer=dict(betas=[.9,.999],eps=1e-8,weight_decay=0.,clip=1.),
        hashes={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.md']},
        no_validation=True,checkpoint_schema='native_dense_diffusion_v1',coordinate_replay_bound=1e-3)
    for k in ['rank','adapter_seed','arm_recipes','checkpoints_every']:lock.pop(k,None)
    write_json(root/'lock.json',lock)


def train_dense_diffusion(root,arm):
    from fastglycan import stage0_confirm_runtime as rt
    from fastglycan.models.soft_sequence_chart import device_tree
    from fastglycan.models.differentiable_mini import diffusion_from_conditioning
    from fastglycan.models.diffusion_scope import select_diffusion_scope
    from fastglycan.hybrid_proposals import identity_noise
    from fastglycan.adapter_supervision import adapter_loss_parts
    lock=json.loads((root/'lock.json').read_text());assert arm in lock['arms']
    folder=root/arm;folder.mkdir(exist_ok=False);start=time.monotonic()
    report=dict(complete=False,arm=arm,updates=0,exposures=0,lock_sha256=sha256(root/'lock.json'))
    try:
        for p,d in lock['hashes'].items():assert sha256(Path(p))==d
        for p,stat in lock['weight_stats'].items():assert [Path(p).stat().st_size,Path(p).stat().st_mtime_ns]==stat
        for x in lock['preflights'].values():assert sha256(Path(x['path']))==x['sha256']
        cache=Path(lock['cache']);source=Path(lock['source'])
        assert sha256(cache/'audit.json')==lock['cache_audit_sha256'] and sha256(cache/'lock.json')==lock['cache_lock_sha256']
        torch.set_num_threads(1);runner=rt.runner_setup(folder/'work');runner.configs.dtype='fp32'
        model=runner.model.eval();eligible={n for n,p in model.named_parameters() if p.requires_grad}
        model.requires_grad_(False);original={n:p.detach().cpu().clone() for n,p in model.named_parameters()}
        fingerprints={n:hashlib.sha256(v.numpy().tobytes()).hexdigest() for n,v in original.items()}
        write_json(folder/'initial_fingerprints.json',fingerprints)
        selected=select_diffusion_scope(model,arm,native_trainable_names=eligible);params=list(selected.values())
        assert list(selected)==lock['preflights'][arm]['selected_names']
        assert {id(p) for p in params}=={id(p) for p in model.parameters() if p.requires_grad}
        assert sum(p.numel() for p in params)==lock['preflights'][arm]['selected_elements']
        assert all(p.dtype==torch.float32 for p in model.parameters());native_keys=set(model.state_dict())
        counts=dict(pairformer=0,diffusion=0)
        ph=model.pairformer_stack.register_forward_hook(lambda *args:counts.__setitem__('pairformer',counts['pairformer']+1))
        dh=model.diffusion_module.register_forward_hook(lambda *args:counts.__setitem__('diffusion',counts['diffusion']+1))
        optimizer=torch.optim.AdamW(params,lr=1e-5,betas=(.9,.999),eps=1e-8,weight_decay=0)
        optimizer.zero_grad(set_to_none=True);verified=set();history=folder/'history.jsonl'
        report.update(selected_tensors=len(params),trainable_parameters=sum(p.numel() for p in params),
            selected_names=list(selected),initial_sha256=sha256(folder/'initial_fingerprints.json'),
            device=torch.cuda.get_device_name(0),torch_version=torch.__version__)
        for exposure,item in enumerate(lock['order'],1):
            before=time.monotonic();g=item['group_id'];seed=item['seed'];data=cache/'examples'/g
            assert next(r for r in lock['rows'] if r['group_id']==g)['role']=='train'
            if g not in verified:
                for p,d in lock['cache_files'].items():
                    if Path(p).parent==data:assert sha256(Path(p))==d
                verified.add(g)
            saved=torch.load(data/'conditioning.pt',map_location='cpu',weights_only=False)
            assert saved['role']=='train' and saved['group_id']==g
            features=device_tree(saved['features'],'cuda');flat=saved['conditioning_flat'].cuda()
            conditioning=tuple(x.reshape(s) for x,s in zip(flat.split(saved['sizes']),saved['shapes']))
            native=torch.load(source/'chemistry'/g/'native.pt',map_location='cpu',weights_only=False)
            noise=identity_noise(native['atoms'],seed,device='cuda')
            labels=torch.load(data/'gt_supervision.pt',map_location='cpu',weights_only=False)
            teacher=torch.as_tensor(np.load(data/f's2_seed{seed}.npy'),device='cuda')
            cpu_rng=torch.get_rng_state().clone();gpu_rng=torch.cuda.get_rng_state().clone()
            predicted=diffusion_from_conditioning(model,features,noise,conditioning,steps=1).reshape(-1,3)
            if exposure==1:
                delta=np.max(np.abs(predicted.detach().cpu().numpy()-np.load(data/f's1_seed{seed}.npy')))
                report['initial_coordinate_max_abs']=float(delta);assert delta<=lock['coordinate_replay_bound']
                if arm=='token_dense':assert delta==0
            parts=adapter_loss_parts(predicted,labels,teacher,smooth_temperature=.1)
            loss=sum(lock['weights'][k]*v for k,v in parts.items());assert torch.isfinite(loss)
            (loss/4).backward()
            assert torch.equal(cpu_rng,torch.get_rng_state()) and torch.equal(gpu_rng,torch.cuda.get_rng_state())
            assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in params)
            record=dict(exposure=exposure,epoch=item['epoch'],group_id=g,seed=seed,
                loss=float(loss.detach()),parts={k:float(v.detach()) for k,v in parts.items()})
            if exposure%4==0:
                update=exposure//4
                lr=1e-5*update/32 if update<=32 else 1e-6+.5*9e-6*(1+math.cos(math.pi*(update-32)/480))
                for group in optimizer.param_groups:group['lr']=lr
                norm=torch.nn.utils.clip_grad_norm_(params,1.,error_if_nonfinite=True)
                optimizer.step();optimizer.zero_grad(set_to_none=True)
                report['updates']=update;record.update(update=update,lr=lr,unclipped_accumulated_grad_norm=float(norm))
                if update%128==0:
                    assert all(torch.equal(p.detach().cpu(),original[n]) for n,p in model.named_parameters() if n not in selected)
                    checkpoint=dict(schema='native_dense_diffusion_v1',arm=arm,update=update,exposures=exposure,
                        trained={n:p.detach().cpu().clone() for n,p in selected.items()},optimizer=optimizer.state_dict(),
                        lock_sha256=sha256(root/'lock.json'))
                    temporary=folder/'checkpoint.tmp';torch.save(checkpoint,temporary)
                    temporary.replace(folder/('update_0512.pt' if update==512 else 'rolling.pt'));del checkpoint
            record['seconds']=time.monotonic()-before
            with history.open('a') as f:f.write(json.dumps(record)+'\n')
            report.update(exposures=exposure,counts=counts,seconds=time.monotonic()-start,
                peak_gpu_bytes=torch.cuda.max_memory_allocated())
            write_json(folder/'report.json',report)
            del saved,features,flat,conditioning,native,noise,labels,teacher,predicted,parts,loss
            torch.cuda.empty_cache()
        assert counts==dict(pairformer=0,diffusion=2048) and report['updates']==512 and len(verified)==128
        assert set(model.state_dict())==native_keys
        assert all(p.grad is None for n,p in model.named_parameters() if n not in selected)
        assert all(torch.equal(p.detach().cpu(),original[n]) for n,p in model.named_parameters() if n not in selected)
        ph.remove();dh.remove()
        report.update(complete=True,excluded_parameters_unchanged=len(original)-len(selected),validation_read=False,
            terminal_sha256=sha256(folder/'update_0512.pt'),history_sha256=sha256(history))
    except Exception:report['error']=traceback.format_exc()
    finally:report['seconds']=time.monotonic()-start;write_json(folder/'report.json',report)
    if not report['complete']:raise RuntimeError(report.get('error','incomplete'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--mode',choices=['prepare','train'],required=True);p.add_argument('--arm');a=p.parse_args()
    assert Path(os.environ['PROTENIX_ROOT_DIR']).resolve()==(a.root.parent/'protenix_stage0_pkg/v1_1/runtime').resolve()
    assert os.environ.get('LAYERNORM_TYPE')=='torch'
    if a.mode=='prepare':prepare_dense_diffusion(a.root)
    else:train_dense_diffusion(a.root,a.arm)
