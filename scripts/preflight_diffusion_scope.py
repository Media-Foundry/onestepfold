#!/usr/bin/env python3
"""Native dense-scope replay, backward, one update and restoration; no learning claim."""
import argparse
import json
from pathlib import Path
import time
import traceback
import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256, write_json


def prepare_diffusion_scope_preflight(root):
    assert not (root/'lock.json').exists()
    parent=root.parent/'diffusion_recipe_scale_v1_20260930'
    old=json.loads((parent/'lock.json').read_text());audit=json.loads((parent/'training_audit.json').read_text())
    assert audit['complete'] and audit['lock_sha256']==sha256(parent/'lock.json')
    first=next(r for r in old['rows'] if r['group_id']==old['order'][0]['group_id'])
    longest=sorted(old['rows'],key=lambda r:(-len(r['sequence']),r['group_id']))[0]
    assert first['group_id']!=longest['group_id']
    write_json(root/'lock.json',dict(parent=str(parent),cache=old['cache'],source=old['source'],
        rows=[first,longest],scopes=['diffusion_dense'],seed=600001,
        weights=old['arm_recipes']['calibrated_high']['weights'],temperature=.1,engineering_lr=1e-5,
        cache_files=old['cache_files'],weight_stats=old['weight_stats'],
        hashes={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.md']},
        expected_nfe_per_scope=12,no_validation=True,no_training_initializer=True,
        replay_protocol='v2: exact frozen-native/reload; bounded scope-dependent arithmetic',
        coordinate_max_abs_tolerance=1e-3,
        predecessor_lock_sha256=sha256(root.parent/'diffusion_scope_preflight_v1_20260930/lock.json'),
        diagnostic_sha256=sha256(root.parent/'diffusion_scope_replay_v2_20260930/report.json')))


def run_diffusion_scope_preflight(root,scope):
    from fastglycan import stage0_confirm_runtime as rt
    from fastglycan.models.soft_sequence_chart import device_tree
    from fastglycan.models.differentiable_mini import diffusion_from_conditioning
    from fastglycan.models.diffusion_scope import select_diffusion_scope
    from fastglycan.hybrid_proposals import identity_noise
    from fastglycan.adapter_supervision import adapter_loss_parts
    lock=json.loads((root/'lock.json').read_text());assert scope in lock['scopes']
    folder=root/scope;folder.mkdir(exist_ok=False);start=time.monotonic()
    report=dict(complete=False,scope=scope,lock_sha256=sha256(root/'lock.json'),cases=[])
    try:
        for path,digest in lock['hashes'].items():assert sha256(Path(path))==digest
        for path,stat in lock['weight_stats'].items():assert [Path(path).stat().st_size,Path(path).stat().st_mtime_ns]==stat
        torch.set_num_threads(1);runner=rt.runner_setup(folder/'work');runner.configs.dtype='fp32'
        model=runner.model.eval();eligible={n for n,p in model.named_parameters() if p.requires_grad}
        intrinsic_fixed={n for n,p in model.named_parameters() if not p.requires_grad}
        model.requires_grad_(False);original={n:p.detach().cpu().clone() for n,p in model.named_parameters()}
        selected=select_diffusion_scope(model,scope,native_trainable_names=eligible);params=list(selected.values())
        assert {id(p) for p in params}=={id(p) for p in model.parameters() if p.requires_grad}
        old_initial=torch.load(Path(lock['parent'])/'calibrated_high/initial.pt',map_location='cpu',weights_only=False)
        token_names={n+'.weight' for n in old_initial};assert len(token_names)==56
        if scope=='token_dense':assert set(selected)==token_names
        else:assert token_names<set(selected)
        assert all(p.dtype==torch.float32 for p in model.parameters())
        state_keys=set(model.state_dict());counts=dict(pairformer=0,diffusion=0)
        ph=model.pairformer_stack.register_forward_hook(lambda *args:counts.__setitem__('pairformer',counts['pairformer']+1))
        dh=model.diffusion_module.register_forward_hook(lambda *args:counts.__setitem__('diffusion',counts['diffusion']+1))
        report.update(selected_tensors=len(params),selected_elements=sum(p.numel() for p in params),
            selected_names=list(selected),intrinsic_fixed=sorted(intrinsic_fixed),original_parameters=len(original),
            device=torch.cuda.get_device_name(0))
        for row in lock['rows']:
            assert row['role']=='train';g=row['group_id'];case=folder/g;case.mkdir()
            data=Path(lock['cache'])/'examples'/g;before=time.monotonic();torch.cuda.reset_peak_memory_stats()
            for path,digest in lock['cache_files'].items():
                if Path(path).parent==data:assert sha256(Path(path))==digest
            saved=torch.load(data/'conditioning.pt',map_location='cpu',weights_only=False);assert saved['role']=='train'
            features=device_tree(saved['features'],'cuda');flat=saved['conditioning_flat'].cuda()
            conditioning=tuple(x.reshape(s) for x,s in zip(flat.split(saved['sizes']),saved['shapes']))
            atoms=torch.load(Path(lock['source'])/'chemistry'/g/'native.pt',map_location='cpu',weights_only=False)['atoms']
            noise=identity_noise(atoms,lock['seed'],device='cuda')
            labels=torch.load(data/'gt_supervision.pt',map_location='cpu',weights_only=False)
            teacher=torch.as_tensor(np.load(data/f's2_seed{lock["seed"]}.npy'),device='cuda')
            native=np.load(data/f's1_seed{lock["seed"]}.npy');cpu_rng=torch.get_rng_state();gpu_rng=torch.cuda.get_rng_state()
            optimizer=torch.optim.AdamW(params,lr=lock['engineering_lr'],betas=(.9,.999),eps=1e-8,weight_decay=0)
            optimizer.zero_grad(set_to_none=True)
            model.requires_grad_(False)
            with torch.no_grad():baseline=diffusion_from_conditioning(model,features,noise,conditioning,steps=1).reshape(-1,3)
            assert np.array_equal(baseline.cpu().numpy(),native),'frozen native cache replay'
            for p in params:p.requires_grad_(True)
            x=diffusion_from_conditioning(model,features,noise,conditioning,steps=1).reshape(-1,3)
            initial_difference=float((x.detach()-baseline).abs().max())
            assert initial_difference<=lock['coordinate_max_abs_tolerance'],'scope-dependent initial arithmetic'
            parts=adapter_loss_parts(x,labels,teacher,smooth_temperature=lock['temperature'])
            loss=sum(lock['weights'][k]*v for k,v in parts.items());loss.backward()
            gradients={n:dict(elements=p.numel(),shape=list(p.shape),present=p.grad is not None,
                finite=bool(torch.isfinite(p.grad).all()) if p.grad is not None else None,
                norm=float(p.grad.double().norm()) if p.grad is not None else None) for n,p in selected.items()}
            write_json(case/'gradients.json',gradients)
            assert all(v['present'] and v['finite'] for v in gradients.values()),'missing/nonfinite selected gradients'
            assert all(p.grad is None for n,p in model.named_parameters() if n not in selected)
            norm=float(torch.nn.utils.clip_grad_norm_(params,1.,error_if_nonfinite=True));optimizer.step();optimizer.zero_grad(set_to_none=True)
            assert all(torch.isfinite(p).all() for p in params)
            assert all(torch.equal(p.detach().cpu(),original[n]) for n,p in model.named_parameters() if n not in selected)
            with torch.no_grad():training_updated=diffusion_from_conditioning(model,features,noise,conditioning,steps=1).reshape(-1,3)
            model.requires_grad_(False)
            with torch.no_grad():updated=diffusion_from_conditioning(model,features,noise,conditioning,steps=1).reshape(-1,3)
            deployment_difference=float((updated-training_updated).abs().max())
            assert deployment_difference<=lock['coordinate_max_abs_tolerance'],'scope-dependent post-update arithmetic'
            assert torch.isfinite(updated).all();np.save(case/'engineering_updated.npy',updated.cpu().numpy())
            partial={n:p.detach().cpu().clone() for n,p in selected.items()};torch.save(partial,case/'engineering_weights.pt')
            changed=[n for n,v in partial.items() if not torch.equal(v,original[n])];assert changed
            with torch.no_grad():
                for n,p in selected.items():p.copy_(original[n].to(p))
                restored=diffusion_from_conditioning(model,features,noise,conditioning,steps=1).reshape(-1,3)
                assert np.array_equal(restored.cpu().numpy(),native),'public restoration replay'
                loaded=torch.load(case/'engineering_weights.pt',map_location='cpu',weights_only=False);assert set(loaded)==set(selected)
                for n,p in selected.items():p.copy_(loaded[n].to(p))
                replay=diffusion_from_conditioning(model,features,noise,conditioning,steps=1).reshape(-1,3)
                assert torch.equal(replay,updated),'saved native weight reload replay'
                for n,p in selected.items():p.copy_(original[n].to(p))
            assert set(model.state_dict())==state_keys
            assert all(torch.equal(p.detach().cpu(),original[n]) for n,p in model.named_parameters())
            assert torch.equal(cpu_rng,torch.get_rng_state()) and torch.equal(gpu_rng,torch.cuda.get_rng_state())
            result=dict(group_id=g,pdb_id=row['pdb_id'],length=len(row['sequence']),loss=float(loss.detach()),
                parts={k:float(v.detach()) for k,v in parts.items()},unclipped_norm=norm,
                changed_tensors=len(changed),zero_gradient_tensors=sum(v['norm']==0 for v in gradients.values()),
                native_replay=True,restoration_replay=True,checkpoint_replay=True,excluded_frozen=True,
                initial_scope_max_abs=initial_difference,post_update_scope_max_abs=deployment_difference,
                checkpoint_sha256=sha256(case/'engineering_weights.pt'),gradients_sha256=sha256(case/'gradients.json'),
                peak_allocated=torch.cuda.max_memory_allocated(),peak_reserved=torch.cuda.max_memory_reserved(),seconds=time.monotonic()-before)
            write_json(case/'report.json',result);report['cases'].append(result);write_json(folder/'report.json',report)
            del saved,features,flat,conditioning,atoms,noise,labels,teacher,x,loss,parts,updated,partial,loaded,restored,replay,optimizer,baseline,training_updated
            torch.cuda.empty_cache()
        assert counts==dict(diffusion=lock['expected_nfe_per_scope'],pairformer=0)
        ph.remove();dh.remove();report.update(complete=True,counts=counts,no_quality_selection=True,no_training_initializer=True)
    except Exception:report['error']=traceback.format_exc()
    report['seconds']=time.monotonic()-start;write_json(folder/'report.json',report)
    if not report['complete']:raise RuntimeError(report.get('error'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--mode',choices=['prepare','worker'],required=True);p.add_argument('--scope',choices=['token_dense','diffusion_dense']);a=p.parse_args()
    if a.mode=='prepare':prepare_diffusion_scope_preflight(a.root)
    else:run_diffusion_scope_preflight(a.root,a.scope)
