#!/usr/bin/env python3
"""DiamondHill weak/strong global-weight pair; unchanged original training loop."""
import argparse
import hashlib
import json
import math
import time
import traceback
from pathlib import Path
import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.rocm_matched_training import make_rocm_matched_lock,verify_rocm_matched_lock,BASE_LOCK_SHA256
from fastglycan.global_distance_training import global_distance_training_hooks
from fastglycan.folding_scale import PARENT_SHA256,folding_scale_lr
from fastglycan.teacher_pairing import feature_digest,tensor_digest

BASE=Path('/data/user/shuang886/Folding/folding_global_distance_training_v1_20260930')
PROBE=Path('/media/IntelSSD/onestepfold/backend_replay_probe_v1_20261001')


def prepare_rocm_matched(root,arm):
    assert not (root/'lock.json').exists()
    assert sha256(BASE/'lock.json')==BASE_LOCK_SHA256
    base=json.loads((BASE/'lock.json').read_text());assert json.loads((BASE/'global_training_audit.json').read_text())['complete']
    execution=json.loads((PROBE/'execution.json').read_text());assert execution['complete']
    references={};hashes=dict(base['hashes'])
    for i,g in enumerate(base['engineering_groups']):
        report=PROBE/f'case_{i}/report.json';p=json.loads(report.read_text())
        assert p['complete'] and p['group_id']==g and p['parameter_updates']==0
        assert all(v['repeat']['exact'] and v['parameters_unchanged'] for v in p['stages'].values())
        references[g]=dict(report=str(report),sha256=sha256(report),**{s:str(report.parent/f'{s}_0.npy') for s in ['public','retained']})
        for file in [report,report.parent/'public_0.npy',report.parent/'retained_0.npy']:hashes[str(file)]=sha256(file)
    for p,h in base['hashes'].items():
        assert sha256(Path(p))==h,p
        if Path(p).is_relative_to(BASE/'code'):assert sha256(root/'code'/Path(p).relative_to(BASE/'code'))==h,p
    hashes.update({str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.md','.json']})
    for p in [BASE/'lock.json',BASE/'global_training_audit.json',PROBE/'execution.json']:hashes[str(p)]=sha256(p)
    backend=dict(source_lock_sha256=BASE_LOCK_SHA256,platform='DiamondHill/ROCm',training_updates=0,
        engineering_references=references,torch=p_version(),numpy=np.__version__,hip=torch.version.hip,
        source='same immutable HPC3 cache, GT, teacher and ordered exposures; platform-specific replay anchors')
    lock=make_rocm_matched_lock(base,arm=arm,hashes=hashes,backend=backend,
        protocol_sha256=sha256(root/'code/docs/mini_folding_rocm_matched_v1.md'),script_sha256=sha256(Path(__file__)))
    write_json(root/'lock.json',lock)


def p_version():
    assert torch.version.hip and str(torch.__version__)=='2.12.0a0+git78258b9'
    return str(torch.__version__)


def validated_lock(root):
    assert sha256(BASE/'lock.json')==BASE_LOCK_SHA256
    lock=json.loads((root/'lock.json').read_text());verify_rocm_matched_lock(lock,json.loads((BASE/'lock.json').read_text()))
    assert lock['backend']['torch']==p_version() and lock['backend']['numpy']==np.__version__ and lock['backend']['hip']==torch.version.hip
    for p,h in lock['hashes'].items():assert sha256(Path(p))==h,p
    return lock


def preflight_rocm_matched(root):
    from fastglycan import stage0_confirm_runtime as rt
    from fastglycan.models.differentiable_mini import diffusion_from_conditioning
    from fastglycan.models.diffusion_scope import load_dense_diffusion_checkpoint,select_diffusion_scope
    import train_folding_scale as trainer
    import fastglycan.adapter_supervision as supervision
    lock=validated_lock(root);torch.set_num_threads(1);folder=root/'preflight';folder.mkdir(exist_ok=False)
    start=time.monotonic();report=dict(complete=False,lock_sha256=sha256(root/'lock.json'),cases=[],parameter_updates=0)
    try:
        assert sha256(Path(lock['initial_checkpoint']))==PARENT_SHA256
        for p,stat in lock['weight_stats'].items():assert [Path(p).stat().st_size,Path(p).stat().st_mtime_ns]==stat
        runner=rt.runner_setup(folder/'work');runner.configs.dtype='fp32';model=runner.model.eval()
        eligible={n for n,p in model.named_parameters() if p.requires_grad};model.requires_grad_(False)
        public={n:p.detach().cpu().clone() for n,p in model.named_parameters()};verified=set()
        with global_distance_training_hooks(trainer,supervision,lock):
            for g in lock['engineering_groups']:
                features,cond,noise,labels,teacher,atoms=trainer.folding_training_input(lock,g,lock['training_seeds'][0],verified)
                ref=lock['backend']['engineering_references'][g];source=json.loads(Path(ref['report']).read_text())
                assert source['input_hashes']==dict(conditioning=feature_digest(cond),features=feature_digest(features),noise=tensor_digest(noise))
                with torch.no_grad():x=diffusion_from_conditioning(model,features,noise,cond,steps=1).reshape(-1,3)
                delta=float(np.max(np.abs(x.cpu().numpy()-np.load(ref['public']))));assert delta<=lock['coordinate_replay_bound']
                report['cases'].append(dict(group_id=g,public_rocm_replay_max_abs=delta))
            state=torch.load(lock['initial_checkpoint'],map_location='cpu',weights_only=False)
            load_dense_diffusion_checkpoint(model,state,arm='diffusion_dense',expected_names=lock['selected_names'])
            original={n:p.detach().cpu().clone() for n,p in model.named_parameters()}
            fingerprints={n:hashlib.sha256(v.numpy().tobytes()).hexdigest() for n,v in original.items()}
            assert fingerprints==json.loads((BASE/'expanded/initial_fingerprints.json').read_text())
            write_json(folder/'initial_fingerprints.json',fingerprints)
            selected=select_diffusion_scope(model,'diffusion_dense',native_trainable_names=eligible);params=list(selected.values())
            assert list(selected)==lock['selected_names'] and sum(p.numel() for p in params)==lock['selected_elements']==69777841
            assert {id(p) for p in model.parameters() if p.requires_grad}=={id(p) for p in params}
            assert all(torch.equal(original[n],public[n]) for n in original if n not in selected)
            assert all(torch.equal(original[n],state['trained'][n]) for n in selected)
            assert all(p.dtype==torch.float32 for p in model.parameters());del public
            for item in report['cases']:
                g=item['group_id'];features,cond,noise,labels,teacher,atoms=trainer.folding_training_input(lock,g,lock['training_seeds'][0],verified)
                source=json.loads(Path(lock['backend']['engineering_references'][g]['report']).read_text())
                assert source['input_hashes']==dict(conditioning=feature_digest(cond),features=feature_digest(features),noise=tensor_digest(noise))
                cpu=torch.get_rng_state().clone();gpu=torch.cuda.get_rng_state().clone()
                x=diffusion_from_conditioning(model,features,noise,cond,steps=1).reshape(-1,3)
                delta=float(np.max(np.abs(x.detach().cpu().numpy()-np.load(lock['backend']['engineering_references'][g]['retained']))));assert delta<=lock['coordinate_replay_bound']
                parts=supervision.adapter_loss_parts(x,labels,teacher,smooth_temperature=lock['smooth_temperature'])
                assert set(parts)==set(lock['weights']);loss=sum(lock['weights'][k]*v for k,v in parts.items());assert torch.isfinite(loss);loss.backward()
                assert all(p.grad is not None and torch.isfinite(p.grad).all() and bool(p.grad.abs().max()>0) for p in params)
                assert torch.equal(cpu,torch.get_rng_state()) and torch.equal(gpu,torch.cuda.get_rng_state())
                norm=float(torch.sqrt(sum(p.grad.double().square().sum() for p in params)))
                assert all(torch.equal(p.detach().cpu(),original[n]) for n,p in model.named_parameters())
                model.zero_grad(set_to_none=True)
                replay=diffusion_from_conditioning(model,features,noise,cond,steps=1).reshape(-1,3)
                assert torch.equal(x.detach(),replay.detach())
                file=folder/f'{g}.npy';np.save(file,x.detach().cpu().numpy())
                item.update(retained_rocm_replay_max_abs=delta,loss=float(loss.detach()),parts={k:float(v.detach()) for k,v in parts.items()},
                    gradient_norm=norm,selected_nonzero_gradients=len(params),replay_exact=True,coordinate_sha256=sha256(file),parameters_unchanged=True)
                del x,replay,parts,loss;torch.cuda.empty_cache()
        report.update(complete=True,initial_sha256=sha256(folder/'initial_fingerprints.json'),selected_tensors=288,selected_elements=69777841)
    except Exception:report['error']=traceback.format_exc()
    report.update(seconds=time.monotonic()-start,peak_gpu_bytes=torch.cuda.max_memory_allocated());write_json(folder/'report.json',report)
    if not report['complete']:raise RuntimeError(report['error'])
    write_json(root/'release.json',dict(lock_sha256=sha256(root/'lock.json'),preflight_sha256=sha256(folder/'report.json'),paired_release_required=True))


def train_rocm_matched(root):
    import train_folding_scale as trainer
    import fastglycan.adapter_supervision as supervision
    lock=validated_lock(root);pair=root.parent/'pair_release.json';release=json.loads(pair.read_text())
    assert release['complete'] and release['locks'][lock['backend']['arm']]==sha256(root/'lock.json')
    with global_distance_training_hooks(trainer,supervision,lock):trainer.run_folding_training(root,'train','expanded')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--mode',choices=['prepare','preflight','train'],required=True);p.add_argument('--arm',choices=['weak','strong']);a=p.parse_args();root=a.root.resolve()
    if a.mode=='prepare':prepare_rocm_matched(root,a.arm)
    elif a.mode=='preflight':preflight_rocm_matched(root)
    else:train_rocm_matched(root)
