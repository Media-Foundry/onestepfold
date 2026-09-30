#!/usr/bin/env python3
"""Frozen TRAIN-only component VJPs; no optimizer update or validation access."""
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


def prepare_gradient_budget_probe(root):
    assert not (root/'lock.json').exists()
    train=root.parent/'diffusion_learning_pilot_v1_20260930';evaluation=root.parent/'diffusion_learning_evaluation_v1_20260930'
    training=json.loads((train/'lock.json').read_text());audit=json.loads((train/'training_audit.json').read_text())
    assert audit['complete'] and audit['lock_sha256']==sha256(train/'lock.json')
    cache=Path(training['cache']);cache_lock=json.loads((cache/'lock.json').read_text())
    rows=[]
    for low,high in [(50,127),(128,255),(256,511),(512,1024)]:
        candidates=[r for r in training['rows'] if low<=len(r['sequence'])<=high];assert len(candidates)>=4
        selected=sorted(candidates,key=lambda r:hashlib.sha256(('diffusion-gradient-budget-v1:20260930:'+r['group_id']).encode()).hexdigest())[:4]
        rows.extend(dict(r,stratum=f'{low}-{high}') for r in selected)
    assert len(rows)==16 and all(r['role']=='train' for r in rows)
    hashes={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.md']}
    for relative in ['src/fastglycan/adapter_supervision.py','src/fastglycan/models/diffusion_adapter.py','src/fastglycan/models/differentiable_mini.py']:
        assert sha256(root/'code'/relative)==sha256(train/'code'/relative)
    inputs={str(train/'lock.json'):sha256(train/'lock.json'),str(train/'training_audit.json'):sha256(train/'training_audit.json')}
    for c in audit['checkpoints'].values():assert sha256(Path(c['path']))==c['sha256'];inputs[c['path']]=c['sha256']
    source=Path(training['source'])
    for row in rows:
        g=row['group_id'];report=json.loads((evaluation/'examples'/g/'report.json').read_text());assert report['role']=='train'
        inputs[str(evaluation/'examples'/g/'report.json')]=sha256(evaluation/'examples'/g/'report.json')
        for path,digest in training['cache_files'].items():
            if Path(path).parent==cache/'examples'/g:assert sha256(Path(path))==digest;inputs[path]=digest
        for name in ['native.pt','mapping.npz']:
            path=source/'chemistry'/g/name;digest=cache_lock['input_hashes'][str(path)]
            assert sha256(path)==digest;inputs[str(path)]=digest
        for entry in report['entries']:
            if entry['model'] in ['gt','gt_s2']:
                path=evaluation/'examples'/g/entry['name'];assert sha256(path)==entry['sha256'];inputs[str(path)]=entry['sha256']
    assignments=[[] for _ in range(8)];loads=[0]*8
    for row in sorted(rows,key=lambda r:(-len(r['sequence']),r['group_id'])):
        i=min(range(8),key=lambda j:(loads[j],j));assignments[i].append(row);loads[i]+=len(row['sequence'])**2
    write_json(root/'lock.json',dict(train=str(train),cache=str(cache),evaluation=str(evaluation),source=str(source),
        rows=rows,assignments=assignments,states=['initial','gt','gt_s2'],seeds=cache_lock['train_seeds'],
        names=['coordinate','smooth_lddt','bond','chirality','clash','teacher'],weights=training['loss_weights'],
        checkpoints=audit['checkpoints'],hashes=hashes,input_hashes=inputs,weight_stats=training['weight_stats'],
        planned_points=96,planned_nfe=96,optimizer_updates=0,validation_read=False))


def run_gradient_budget_probe(root,index):
    from fastglycan import stage0_confirm_runtime as rt
    from fastglycan.models.soft_sequence_chart import device_tree
    from fastglycan.models.differentiable_mini import diffusion_from_conditioning
    from fastglycan.models.diffusion_adapter import attach_diffusion_adapter
    from fastglycan.hybrid_proposals import identity_noise
    from fastglycan.adapter_supervision import adapter_loss_parts
    from fastglycan.gradient_budget import component_gradient_statistics
    lock=json.loads((root/'lock.json').read_text());source=Path(lock['source']);cache=Path(lock['cache'])
    folder=root/f'worker_{index}';folder.mkdir(exist_ok=False);start=time.monotonic()
    report=dict(complete=False,index=index,points=[],lock_sha256=sha256(root/'lock.json'))
    try:
        for path,digest in lock['hashes'].items():assert sha256(Path(path))==digest
        for path,stat in lock['weight_stats'].items():assert [Path(path).stat().st_size,Path(path).stat().st_mtime_ns]==stat
        torch.set_num_threads(1);runner=rt.runner_setup(folder/'work');runner.configs.dtype='fp32'
        model=runner.model.eval().requires_grad_(False)
        assert all(p.dtype==torch.float32 for p in model.parameters() if p.is_floating_point())
        original={n:(p,p.detach().cpu().clone()) for n,p in model.named_parameters()}
        adapters=attach_diffusion_adapter(model);params=[];parameter_names=[];sizes=[]
        for name,adapter in adapters.items():
            for kind,p in adapter.named_parameters():params.append(p);parameter_names.append(name+'.'+kind);sizes.append(p.numel())
        assert sum(sizes)==835584 and len(params)==112
        states={'initial':{n:{k:v.detach().cpu().clone() for k,v in a.state_dict().items()} for n,a in adapters.items()}}
        for name,c in lock['checkpoints'].items():
            assert sha256(Path(c['path']))==c['sha256'];states[name]=torch.load(c['path'],map_location='cpu',weights_only=False)['trained']
        calls=dict(pairformer=0,diffusion=0)
        ph=model.pairformer_stack.register_forward_hook(lambda *unused:calls.__setitem__('pairformer',calls['pairformer']+1))
        dh=model.diffusion_module.register_forward_hook(lambda *unused:calls.__setitem__('diffusion',calls['diffusion']+1))
        for row in lock['assignments'][index]:
            g=row['group_id'];data=cache/'examples'/g;native_path=source/'chemistry'/g/'native.pt'
            for path in [data/'conditioning.pt',data/'gt_supervision.pt',native_path]:assert sha256(path)==lock['input_hashes'][str(path)]
            saved=torch.load(data/'conditioning.pt',map_location='cpu',weights_only=False);assert saved['role']=='train'
            flat=saved['conditioning_flat'].cuda();features=device_tree(saved['features'],'cuda')
            conditioning=tuple(x.reshape(s) for x,s in zip(flat.split(saved['sizes']),saved['shapes']))
            atoms=torch.load(native_path,map_location='cpu',weights_only=False)['atoms']
            labels=torch.load(data/'gt_supervision.pt',map_location='cpu',weights_only=False)
            for state in lock['states']:
                for name,a in adapters.items():a.load_state_dict(states[state][name])
                for seed in lock['seeds']:
                    begin=time.monotonic();noise=identity_noise(atoms,seed,device='cuda')
                    teacher_path=data/f's2_seed{seed}.npy';assert sha256(teacher_path)==lock['input_hashes'][str(teacher_path)]
                    teacher=torch.as_tensor(np.load(teacher_path),device='cuda')
                    cpu_rng=torch.get_rng_state().clone();gpu_rng=torch.cuda.get_rng_state().clone()
                    x=diffusion_from_conditioning(model,features,noise,conditioning,steps=1).reshape(-1,3)
                    replay=data/f's1_seed{seed}.npy' if state=='initial' else Path(lock['evaluation'])/'examples'/g/f'{state}_seed{seed}.npy'
                    assert sha256(replay)==lock['input_hashes'][str(replay)]
                    assert np.array_equal(x.detach().cpu().numpy(),np.load(replay)),'frozen-state replay mismatch'
                    parts=adapter_loss_parts(x,labels,teacher);vectors=[]
                    for component in lock['names']:
                        grads=torch.autograd.grad(parts[component],params,retain_graph=True)
                        assert all(torch.isfinite(v).all() for v in grads)
                        vectors.append(torch.cat([v.detach().flatten() for v in grads]).cpu());del grads
                    matrix=torch.stack(vectors);del vectors
                    objective=sum(lock['weights'][n]*parts[n] for n in lock['names'][:-1])
                    direct_gt=torch.autograd.grad(objective,params,retain_graph=True)
                    direct_gt=torch.cat([v.detach().flatten() for v in direct_gt]).cpu()
                    direct_plus=torch.autograd.grad(objective+lock['weights']['teacher']*parts['teacher'],params)
                    direct_plus=torch.cat([v.detach().flatten() for v in direct_plus]).cpu()
                    weighted=matrix.double()*torch.tensor([lock['weights'][n] for n in lock['names']],dtype=torch.float64)[:,None]
                    gt_error=float((weighted[:5].sum(0)-direct_gt.double()).norm()/direct_gt.double().norm().clamp_min(1e-30))
                    plus_error=float((weighted.sum(0)-direct_plus.double()).norm()/direct_plus.double().norm().clamp_min(1e-30))
                    assert max(gt_error,plus_error)<1e-4
                    assert torch.equal(cpu_rng,torch.get_rng_state()) and torch.equal(gpu_rng,torch.cuda.get_rng_state())
                    stats=component_gradient_statistics(matrix,lock['names'],lock['weights'])
                    slices=matrix.split(sizes,dim=1)
                    block_norms={kind:torch.stack([v.double().square().sum(1) for n,v in zip(parameter_names,slices) if n.endswith('.'+kind)]).sum(0).sqrt().tolist() for kind in ['down','up']}
                    if state=='initial':assert all(v==0 for v in block_norms['down'])
                    target=root/'points'/g/f'{state}_{seed}';target.mkdir(parents=True,exist_ok=False)
                    torch.save(dict(raw_gradients=matrix,direct_gt=direct_gt,direct_gt_s2=direct_plus,
                        names=lock['names'],parameter_names=parameter_names,sizes=sizes,
                        group_id=g,state=state,seed=seed,lock_sha256=sha256(root/'lock.json')),target/'gradients.pt')
                    point=dict(group_id=g,pdb_id=row['pdb_id'],length=len(row['sequence']),stratum=row['stratum'],state=state,seed=seed,
                        parts={n:float(v.detach()) for n,v in parts.items()},statistics=stats,raw_block_norms=block_norms,
                        gt_chain_relative=gt_error,gt_s2_chain_relative=plus_error,archive_replay_exact=True,
                        gradient_sha256=sha256(target/'gradients.pt'),gradient_bytes=(target/'gradients.pt').stat().st_size,
                        seconds=time.monotonic()-begin)
                    write_json(target/'report.json',point);report['points'].append(point);write_json(folder/'report.json',report)
                    del x,parts,objective,matrix,direct_gt,direct_plus,weighted,slices,teacher,noise
                    torch.cuda.empty_cache()
            del saved,flat,features,conditioning,atoms,labels
        assert calls==dict(pairformer=0,diffusion=6*len(lock['assignments'][index]))
        assert all(p.grad is None for p in model.parameters())
        assert all(torch.equal(p.detach().cpu(),before) for p,before in original.values())
        for name,a in adapters.items():
            assert all(torch.equal(v.cpu(),states['gt_s2'][name][k]) for k,v in a.state_dict().items())
        ph.remove();dh.remove()
        report.update(complete=True,calls=calls,base_parameters_unchanged=len(original),
            no_optimizer_updates=True,peak_gpu_bytes=torch.cuda.max_memory_allocated())
    except Exception:report['error']=traceback.format_exc()
    finally:report['seconds']=time.monotonic()-start;write_json(folder/'report.json',report)
    if not report['complete']:raise RuntimeError(report.get('error','incomplete'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--mode',choices=['prepare','worker'],required=True);p.add_argument('--index',type=int);a=p.parse_args()
    assert Path(os.environ['PROTENIX_ROOT_DIR']).resolve()==(a.root.parent/'protenix_stage0_pkg/v1_1/runtime').resolve()
    assert os.environ.get('LAYERNORM_TYPE')=='torch'
    if a.mode=='prepare':prepare_gradient_budget_probe(a.root)
    else:run_gradient_budget_probe(a.root,a.index)
