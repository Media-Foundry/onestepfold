#!/usr/bin/env python3
"""Audited same-start folding-only continuation on TRAIN128 versus TRAIN423."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
import traceback
import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.folding_scale import PARENT_SHA256, folding_scale_lr


def prepare_folding_training(root, cycle, cache, checkpoint):
    assert not (root/'lock.json').exists()
    experiment=json.loads((cycle/'lock.json').read_text());audit=json.loads((cache/'audit.json').read_text())
    cl=json.loads((cache/'lock.json').read_text())
    assert audit['complete'] and audit['lock_sha256']==sha256(cache/'lock.json')
    assert audit['cycle_lock_sha256']==sha256(cycle/'lock.json')==cl['cycle_lock_sha256']
    assert audit['artifact_manifest_sha256']==sha256(cache/'artifact_manifest.json')
    assert sha256(checkpoint)==experiment['initial_checkpoint_sha256']==PARENT_SHA256
    prior=json.loads((cycle/'initial_training_lock.json').read_text())
    assert sha256(cycle/'initial_training_lock.json')==experiment['initial_training_lock_sha256']
    assert experiment['updates']==2048 and experiment['exposures']==8192 and experiment['accumulation']==4
    rows=json.loads((cycle/'selection.json').read_text());lookup={r['group_id']:r for r in rows}
    for arm,order in experiment['orders'].items():
        assert len(order)==8192 and set(x['group_id'] for x in order)==set(experiment['arms'][arm])
        assert all(lookup[x['group_id']]['role']=='train' and x['seed'] in experiment['training_seeds'] for x in order)
    probe=sorted(experiment['original_train_ids'],key=lambda g:hashlib.sha256(('folding-scale-trainprobe-v1:'+g).encode()).hexdigest())[:32]
    engineering=sorted(experiment['original_train_ids'],key=lambda g:(len(lookup[g]['sequence']),g))
    expected=prior['preflights']['diffusion_dense']
    lock=dict(experiment,cycle=str(cycle),cache=str(cache),initial_checkpoint=str(checkpoint),
        rows=rows,cache_audit_sha256=sha256(cache/'audit.json'),cache_lock_sha256=sha256(cache/'lock.json'),
        cache_manifest_sha256=sha256(cache/'artifact_manifest.json'),cache_files=json.loads((cache/'artifact_manifest.json').read_text()),
        selected_names=expected['selected_names'],selected_elements=expected['selected_elements'],
        probe_groups=probe,probe_updates=[0,512,1024,2048],engineering_groups=[engineering[0],engineering[-1]],
        weight_stats=cl['weight_stats'],hashes={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.json','.md']},
        cycle_lock_sha256=sha256(cycle/'lock.json'),coordinate_replay_bound=1e-3,
        checkpoint_schema='folding_scale_continuation_v1')
    assert len(lock['selected_names'])==288 and lock['selected_elements']==69777841
    write_json(root/'lock.json',lock)


def folding_training_input(lock, group, seed, verified):
    from fastglycan.models.soft_sequence_chart import device_tree
    from fastglycan.hybrid_proposals import identity_noise
    cache=Path(lock['cache']);source=Path(lock['source']);folder=cache/'examples'/group
    if group not in verified:
        for path,digest in lock['cache_files'].items():
            if Path(path).parent==folder:assert sha256(Path(path))==digest,path
        verified.add(group)
    saved=torch.load(folder/'conditioning.pt',map_location='cpu',weights_only=False)
    assert saved['role']=='train' and saved['group_id']==group
    features=device_tree(saved['features'],'cuda');flat=saved['conditioning_flat'].cuda()
    conditioning=tuple(x.reshape(s) for x,s in zip(flat.split(saved['sizes']),saved['shapes']))
    native=torch.load(source/'chemistry'/group/'native.pt',map_location='cpu',weights_only=False)
    labels=torch.load(folder/'gt_supervision.pt',map_location='cpu',weights_only=False)
    teacher=torch.as_tensor(np.load(folder/f's2_seed{seed}.npy'),device='cuda')
    noise=identity_noise(native['atoms'],seed,device='cuda')
    return features,conditioning,noise,labels,teacher,native['atoms']


def folding_training_probe(model, lock, folder, update, verified):
    from fastglycan.models.differentiable_mini import diffusion_from_conditioning
    from fastglycan.diffusion_pilot_metrics import prepare_pilot_scoring, score_diffusion_pilot
    calibration=json.loads((folder.parent/'code/docs/connection_reference_bands.json').read_text())
    lookup={r['group_id']:r for r in lock['rows']};out=folder/f'probe_{update:04d}';out.mkdir()
    records=[];begin=time.monotonic()
    with torch.no_grad():
        for g in lock['probe_groups']:
            for seed in lock['training_seeds']:
                features,cond,noise,labels,teacher,atoms=folding_training_input(lock,g,seed,verified)
                x=diffusion_from_conditioning(model,features,noise,cond,steps=1).reshape(-1,3)
                assert torch.isfinite(x).all();array=x.cpu().numpy();p=out/f'{g}_{seed}.npy';np.save(p,array)
                mapping=dict(np.load(Path(lock['source'])/'chemistry'/g/'mapping.npz'))
                context=prepare_pilot_scoring(mapping,atoms.bonds.as_array(),lookup[g]['sequence'])
                score=score_diffusion_pilot(array,context,calibration)
                records.append(dict(group_id=g,seed=seed,sha256=sha256(p),**score))
                del features,cond,noise,labels,teacher,atoms,x,array,mapping,context
    report=dict(update=update,role='train_probe_only',proteins=32,outputs=64,records=records,
        all_atom_lddt=float(np.mean([r['all_atom_lddt'] for r in records])),
        ca_lddt=float(np.mean([r['ca_lddt'] for r in records])),
        severe_pairs=sum(r['geometry']['severe_pairs'] for r in records),
        zero_and_strict=sum(r['geometry']['severe_pairs']==0 and r['geometry']['strict_checked_chirality'] for r in records),
        seconds=time.monotonic()-begin)
    write_json(out/'report.json',report)
    return {k:v for k,v in report.items() if k!='records'}


def run_folding_training(root, mode, arm):
    from fastglycan import stage0_confirm_runtime as rt
    from fastglycan.models.differentiable_mini import diffusion_from_conditioning
    from fastglycan.models.diffusion_scope import select_diffusion_scope, load_dense_diffusion_checkpoint
    from fastglycan.adapter_supervision import adapter_loss_parts
    lock=json.loads((root/'lock.json').read_text())
    assert mode in ('preflight','train') and (mode=='preflight' or arm in lock['arms'])
    folder=root/('preflight' if mode=='preflight' else arm);folder.mkdir(exist_ok=False)
    begin=time.monotonic();report=dict(complete=False,mode=mode,arm=arm,updates=0,exposures=0,
        lock_sha256=sha256(root/'lock.json'),validation_read=False)
    try:
        for p,d in lock['hashes'].items():assert sha256(Path(p))==d,p
        for p,stat in lock['weight_stats'].items():assert [Path(p).stat().st_size,Path(p).stat().st_mtime_ns]==stat
        cache=Path(lock['cache']);assert sha256(cache/'audit.json')==lock['cache_audit_sha256']
        assert sha256(cache/'lock.json')==lock['cache_lock_sha256']
        assert sha256(cache/'artifact_manifest.json')==lock['cache_manifest_sha256']
        assert sha256(Path(lock['initial_checkpoint']))==PARENT_SHA256
        if mode=='train':
            release=json.loads((root/'release.json').read_text());preflight=json.loads((root/'preflight/report.json').read_text())
            assert release['preflight_sha256']==sha256(root/'preflight/report.json') and preflight['complete']
            assert release['lock_sha256']==sha256(root/'lock.json')==preflight['lock_sha256']
        torch.set_num_threads(1);runner=rt.runner_setup(folder/'work');runner.configs.dtype='fp32'
        model=runner.model.eval();eligible={n for n,p in model.named_parameters() if p.requires_grad}
        model.requires_grad_(False);public={n:p.detach().cpu().clone() for n,p in model.named_parameters()}
        verified=set();state=torch.load(lock['initial_checkpoint'],map_location='cpu',weights_only=False)
        report.update(device=torch.cuda.get_device_name(0),torch_version=torch.__version__)
        if mode=='preflight':
            report['public_replay']=[]
            with torch.no_grad():
                for g in lock['engineering_groups']:
                    features,cond,noise,labels,teacher,atoms=folding_training_input(lock,g,lock['training_seeds'][0],verified)
                    x=diffusion_from_conditioning(model,features,noise,cond,steps=1).reshape(-1,3)
                    expected=np.load(cache/'examples'/g/f's1_seed{lock["training_seeds"][0]}.npy')
                    delta=float(np.max(np.abs(x.cpu().numpy()-expected)));assert delta<=lock['coordinate_replay_bound']
                    report['public_replay'].append(dict(group_id=g,max_abs=delta))
                    del features,cond,noise,labels,teacher,atoms,x,expected
        load_dense_diffusion_checkpoint(model,state,arm='diffusion_dense',expected_names=lock['selected_names'])
        original={n:p.detach().cpu().clone() for n,p in model.named_parameters()}
        fingerprints={n:hashlib.sha256(v.numpy().tobytes()).hexdigest() for n,v in original.items()}
        write_json(folder/'initial_fingerprints.json',fingerprints)
        selected=select_diffusion_scope(model,'diffusion_dense',native_trainable_names=eligible);params=list(selected.values())
        assert list(selected)==lock['selected_names'] and sum(p.numel() for p in params)==lock['selected_elements']
        assert {id(p) for p in params}=={id(p) for p in model.parameters() if p.requires_grad}
        assert all(torch.equal(original[n],public[n]) for n in original if n not in selected)
        assert all(torch.equal(original[n],state['trained'][n]) for n in selected)
        assert all(p.dtype==torch.float32 for p in model.parameters())
        report.update(initial_sha256=sha256(folder/'initial_fingerprints.json'),selected_names=list(selected),
            selected_tensors=len(selected),trainable_parameters=sum(p.numel() for p in params))
        del public
        if mode=='preflight':
            cases=[]
            for g in lock['engineering_groups']:
                features,cond,noise,labels,teacher,atoms=folding_training_input(lock,g,lock['training_seeds'][0],verified)
                cpu_rng=torch.get_rng_state().clone();gpu_rng=torch.cuda.get_rng_state().clone()
                x=diffusion_from_conditioning(model,features,noise,cond,steps=1).reshape(-1,3)
                parts=adapter_loss_parts(x,labels,teacher,smooth_temperature=lock['smooth_temperature'])
                loss=sum(lock['weights'][k]*v for k,v in parts.items());assert torch.isfinite(loss);loss.backward()
                assert all(p.grad is not None and torch.isfinite(p.grad).all() and bool(p.grad.abs().max()>0) for p in params)
                assert torch.equal(cpu_rng,torch.get_rng_state()) and torch.equal(gpu_rng,torch.cuda.get_rng_state())
                expected=x.detach().clone();norm=float(torch.sqrt(sum(p.grad.double().square().sum() for p in params)))
                assert all(torch.equal(p.detach().cpu(),original[n]) for n,p in model.named_parameters())
                model.zero_grad(set_to_none=True);model.requires_grad_(False)
                load_dense_diffusion_checkpoint(model,state,arm='diffusion_dense',expected_names=lock['selected_names'])
                selected=select_diffusion_scope(model,'diffusion_dense',native_trainable_names=eligible);params=list(selected.values())
                replay=diffusion_from_conditioning(model,features,noise,cond,steps=1).reshape(-1,3)
                assert torch.equal(expected,replay.detach()),'learned checkpoint replay mismatch'
                cases.append(dict(group_id=g,loss=float(loss.detach()),gradient_norm=norm,replay_exact=True,
                    selected_nonzero_gradients=len(params),parameters_unchanged=True,peak_gpu_bytes=torch.cuda.max_memory_allocated()))
                del features,cond,noise,labels,teacher,atoms,x,parts,loss,expected,replay
                torch.cuda.empty_cache()
            report.update(complete=True,cases=cases,parameter_updates=0)
        else:
            assert report['initial_sha256']==preflight['initial_sha256']
            optimizer=torch.optim.AdamW(params,lr=lock['learning_rate']['peak'],
                betas=tuple(lock['optimizer']['betas']),eps=lock['optimizer']['eps'],weight_decay=lock['optimizer']['weight_decay'])
            assert not optimizer.state;optimizer.zero_grad(set_to_none=True)
            counts=dict(pairformer=0,diffusion=0)
            ph=model.pairformer_stack.register_forward_hook(lambda *args:counts.__setitem__('pairformer',counts['pairformer']+1))
            dh=model.diffusion_module.register_forward_hook(lambda *args:counts.__setitem__('diffusion',counts['diffusion']+1))
            report['probes']=[folding_training_probe(model,lock,folder,0,verified)]
            history=folder/'history.jsonl';trained_seen=set();order=lock['orders'][arm]
            for exposure,item in enumerate(order,1):
                started=time.monotonic();g=item['group_id'];seed=item['seed']
                assert g in lock['arms'][arm];trained_seen.add(g)
                features,cond,noise,labels,teacher,atoms=folding_training_input(lock,g,seed,verified)
                cpu_rng=torch.get_rng_state().clone();gpu_rng=torch.cuda.get_rng_state().clone()
                x=diffusion_from_conditioning(model,features,noise,cond,steps=1).reshape(-1,3)
                parts=adapter_loss_parts(x,labels,teacher,smooth_temperature=lock['smooth_temperature'])
                loss=sum(lock['weights'][k]*v for k,v in parts.items());assert torch.isfinite(loss)
                (loss/lock['accumulation']).backward()
                assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in params)
                assert torch.equal(cpu_rng,torch.get_rng_state()) and torch.equal(gpu_rng,torch.cuda.get_rng_state())
                record=dict(exposure=exposure,epoch=item['epoch'],group_id=g,seed=seed,loss=float(loss.detach()),parts={k:float(v.detach()) for k,v in parts.items()})
                if exposure%lock['accumulation']==0:
                    update=exposure//lock['accumulation'];lr=folding_scale_lr(update,lock['learning_rate'],lock['updates'])
                    for param_group in optimizer.param_groups:param_group['lr']=lr
                    norm=torch.nn.utils.clip_grad_norm_(params,lock['optimizer']['clip'],error_if_nonfinite=True)
                    optimizer.step();optimizer.zero_grad(set_to_none=True)
                    record.update(update=update,lr=lr,unclipped_accumulated_grad_norm=float(norm));report['updates']=update
                record['seconds']=time.monotonic()-started
                with history.open('a') as stream:stream.write(json.dumps(record)+'\n')
                del features,cond,noise,labels,teacher,atoms,x,parts,loss
                if exposure%lock['accumulation']==0 and update in lock['probe_updates']:
                    assert all(torch.equal(p.detach().cpu(),original[n]) for n,p in model.named_parameters() if n not in selected)
                    checkpoint=dict(schema=lock['checkpoint_schema'],arm=arm,update=update,exposures=exposure,
                        parent_sha256=PARENT_SHA256,trained={n:p.detach().cpu().clone() for n,p in selected.items()},
                        optimizer=optimizer.state_dict(),lock_sha256=sha256(root/'lock.json'))
                    temporary=folder/'checkpoint.tmp';torch.save(checkpoint,temporary);temporary.replace(folder/f'update_{update:04d}.pt');del checkpoint
                    report['probes'].append(folding_training_probe(model,lock,folder,update,verified))
                report.update(exposures=exposure,counts=counts,seconds=time.monotonic()-begin,peak_gpu_bytes=torch.cuda.max_memory_allocated())
                write_json(folder/'report.json',report);torch.cuda.empty_cache()
            assert report['updates']==2048 and trained_seen==set(lock['arms'][arm])
            assert counts==dict(pairformer=0,diffusion=8192+4*64)
            assert all(int(optimizer.state[p]['step'])==2048 for p in params)
            assert all(torch.equal(p.detach().cpu(),original[n]) for n,p in model.named_parameters() if n not in selected)
            assert all(p.grad is None for p in model.parameters())
            ph.remove();dh.remove()
            report.update(complete=True,terminal_sha256=sha256(folder/'update_2048.pt'),
                history_sha256=sha256(history),excluded_parameters_unchanged=True,unique_train_proteins=len(trained_seen))
    except Exception:report['error']=traceback.format_exc()
    finally:
        report['seconds']=time.monotonic()-begin;write_json(folder/'report.json',report)
    if not report['complete']:raise RuntimeError(report.get('error','incomplete'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--mode',choices=['prepare','preflight','train'],required=True);p.add_argument('--arm')
    p.add_argument('--cycle',type=Path);p.add_argument('--cache',type=Path);p.add_argument('--checkpoint',type=Path)
    a=p.parse_args();root=a.root.resolve()
    if a.mode=='prepare':prepare_folding_training(root,a.cycle.resolve(),a.cache.resolve(),a.checkpoint.resolve())
    else:
        assert Path(os.environ['PROTENIX_ROOT_DIR']).resolve()==root.parent/'protenix_stage0_pkg/v1_1/runtime'
        assert os.environ.get('LAYERNORM_TYPE')=='torch'
        run_folding_training(root,a.mode,a.arm)
