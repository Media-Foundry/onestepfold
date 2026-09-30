#!/usr/bin/env python3
"""Sixteen hash-bound TRAIN forwards and three weighted VJPs per forward."""
import argparse
import hashlib
import json
import os
import platform
from pathlib import Path
import time
import traceback
import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.folding_parameter_budget import parameter_gradient_grams


def run_folding_parameter_budget(root,index):
    from fastglycan import stage0_confirm_runtime as rt
    from fastglycan.models.diffusion_scope import select_diffusion_scope,load_dense_diffusion_checkpoint
    from fastglycan.models.differentiable_mini import diffusion_from_conditioning
    from fastglycan.folding_scale import load_folding_scale_terminal
    from fastglycan.adapter_supervision import adapter_loss_parts
    from fastglycan.global_distance_supervision import global_ca_distance_loss
    from train_folding_scale import folding_training_input
    start=time.monotonic();lock=json.loads((root/'lock.json').read_text());folder=root/f'worker_{index}';folder.mkdir(exist_ok=False)
    out=dict(complete=False,index=index,points=[],lock_sha256=sha256(root/'lock.json'))
    try:
        for p,h in lock['hashes'].items():assert sha256(Path(p))==h,p
        train=json.loads(Path(lock['training_lock']).read_text());assert sha256(Path(lock['training_lock']))==lock['training_lock_sha256']
        for p,stat in train['weight_stats'].items():assert [Path(p).stat().st_size,Path(p).stat().st_mtime_ns]==stat
        torch.set_num_threads(1);runner=rt.runner_setup(folder/'work');runner.configs.dtype='fp32';model=runner.model.eval()
        eligible={n for n,p in model.named_parameters() if p.requires_grad};model.requires_grad_(False)
        calls=dict(pairformer=0,diffusion=0)
        ph=model.pairformer_stack.register_forward_hook(lambda *a:calls.__setitem__('pairformer',calls['pairformer']+1))
        dh=model.diffusion_module.register_forward_hook(lambda *a:calls.__setitem__('diffusion',calls['diffusion']+1))
        out['environment']=dict(hostname=platform.node(),torch=torch.__version__,gpu_uuid=str(getattr(torch.cuda.get_device_properties(0),'uuid',None)),deterministic=torch.are_deterministic_algorithms_enabled(),cublas=os.environ.get('CUBLAS_WORKSPACE_CONFIG'),tf32=torch.backends.cuda.matmul.allow_tf32)
        verified=set()
        for stage,c in lock['checkpoints'].items():
            assert sha256(Path(c['path']))==c['sha256'];state=torch.load(c['path'],map_location='cpu',weights_only=False)
            model.requires_grad_(False)
            if stage=='retained512':load_dense_diffusion_checkpoint(model,state,arm='diffusion_dense',expected_names=train['selected_names'])
            else:load_folding_scale_terminal(model,state,arm='expanded',expected_names=train['selected_names'],lock_sha256=lock['training_lock_sha256'])
            del state
            originals={n:hashlib.sha256(p.detach().cpu().numpy().tobytes()).hexdigest() for n,p in model.named_parameters()}
            selected=select_diffusion_scope(model,'diffusion_dense',native_trainable_names=eligible);params=list(selected.values())
            assert list(selected)==train['selected_names'] and sum(p.numel() for p in params)==69777841 and len(params)==288
            assert all(p.dtype==torch.float32 for p in model.parameters())
            for row in lock['assignments'][index]:
                begin=time.monotonic();g=row['group_id'];seed=lock['seed'];assert g in train['probe_groups'] and g in train['arms']['expanded']
                features,cond,noise,labels,teacher,atoms=folding_training_input(train,g,seed,verified)
                cpu_rng=torch.get_rng_state().clone();gpu_rng=torch.cuda.get_rng_state().clone()
                input_sha=hashlib.sha256(noise.cpu().numpy().tobytes()+b''.join(v.cpu().numpy().tobytes() for v in cond)).hexdigest()
                torch.cuda.synchronize()
                x=diffusion_from_conditioning(model,features,noise,cond,steps=1).reshape(-1,3)
                ref=lock['references'][stage][g];assert sha256(Path(ref['path']))==ref['sha256'];expected=np.load(ref['path'])
                assert np.array_equal(x.detach().cpu().numpy(),expected),'archived coordinate replay mismatch'
                gl=train['global_distance']['labels'][g];assert sha256(Path(gl['path']))==gl['sha256']
                bundle=torch.load(gl['path'],map_location='cpu',weights_only=False)
                for key,array in [('atom_names',atoms.atom_name),('residue_ids',atoms.res_id),('chain_ids',atoms.chain_id)]:assert np.array_equal(bundle[key],array)
                parts=adapter_loss_parts(x,labels,teacher,smooth_temperature=train['smooth_temperature']);parts['global_distance']=global_ca_distance_loss(x,bundle['labels'])
                objectives=dict(old_coordinate=.01*parts['coordinate'],global_distance=train['weights']['global_distance']*parts['global_distance'],rest=sum(train['weights'][k]*v for k,v in parts.items() if k not in ['coordinate','global_distance']))
                vectors={};coordinate_vectors={}
                for i,(name,loss) in enumerate(objectives.items()):
                    grads=torch.autograd.grad(loss,[x,*params],retain_graph=i<2);assert all(torch.isfinite(v).all() for v in grads)
                    coordinate_vectors[name]=grads[0].detach().cpu();vectors[name]=[v.detach().cpu() for v in grads[1:]];del grads
                statistics=parameter_gradient_grams(vectors,list(selected));cm=torch.stack([v.flatten().double() for v in coordinate_vectors.values()]);coordinate_gram=(cm@cm.T).tolist()
                assert torch.equal(cpu_rng,torch.get_rng_state()) and torch.equal(gpu_rng,torch.cuda.get_rng_state())
                point=dict(group_id=g,pdb_id=row['pdb_id'],length=row['length'],stage=stage,seed=seed,archive_replay_exact=True,coordinate_sha256=ref['sha256'],input_noise_conditioning_sha256=input_sha,
                    losses={k:float(v.detach()) for k,v in parts.items()},statistics=statistics,coordinate_gram=coordinate_gram,
                    component_order=list(objectives),seconds=time.monotonic()-begin,scope='Weighted Euclidean VJPs; no Adam preconditioning/update or step-size calibration')
                write_json(folder/f'{stage}_{g}.json',point);out['points'].append(point);write_json(folder/'report.json',out)
                del features,cond,noise,labels,teacher,atoms,x,expected,bundle,parts,objectives,vectors,coordinate_vectors,cm
                torch.cuda.empty_cache()
            assert all(hashlib.sha256(p.detach().cpu().numpy().tobytes()).hexdigest()==originals[n] for n,p in model.named_parameters())
            assert all(p.grad is None for p in model.parameters())
        assert calls==dict(pairformer=0,diffusion=2*len(lock['assignments'][index]));ph.remove();dh.remove()
        out.update(complete=True,calls=calls,parameters_unchanged_each_state=True,optimizer_updates=0,validation_read=False,
                   peak_gpu_bytes=torch.cuda.max_memory_allocated(),device=torch.cuda.get_device_name(0))
    except Exception:out['error']=traceback.format_exc()
    finally:out['seconds']=time.monotonic()-start;write_json(folder/'report.json',out)
    if not out['complete']:raise RuntimeError(out.get('error','incomplete'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--index',type=int,required=True);a=p.parse_args()
    assert Path(os.environ['PROTENIX_ROOT_DIR']).resolve()==a.root.parent/'protenix_stage0_pkg/v1_1/runtime'
    assert os.environ.get('LAYERNORM_TYPE')=='torch'
    run_folding_parameter_budget(a.root.resolve(),a.index)
