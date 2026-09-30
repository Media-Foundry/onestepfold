#!/usr/bin/env python3
"""Terminal-only native S1/S2 and merged-adapter comparison from frozen caches."""
import argparse
import copy
import json
import os
from pathlib import Path
import shutil
import time
import traceback

import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256, write_json


def prepare_diffusion_evaluation(root):
    assert not (root/'lock.json').exists()
    train=root.parent/'diffusion_learning_pilot_v1_20260930'
    audit=json.loads((train/'training_audit.json').read_text());assert audit['complete']
    assert audit['lock_sha256']==sha256(train/'lock.json')
    train_lock=json.loads((train/'lock.json').read_text());cache=Path(train_lock['cache'])
    cache_lock=json.loads((cache/'lock.json').read_text())
    assert sha256(cache/'lock.json')==train_lock['cache_lock_sha256']
    for checkpoint in audit['checkpoints'].values():assert sha256(Path(checkpoint['path']))==checkpoint['sha256']
    inputs={str(train/'training_audit.json'):sha256(train/'training_audit.json'),str(train/'lock.json'):sha256(train/'lock.json')}
    for row in cache_lock['rows']:
        folder=cache/'examples'/row['group_id']
        for name,digest in json.loads((folder/'report.json').read_text())['files'].items():
            assert sha256(folder/name)==digest;inputs[str(folder/name)]=digest
    hashes={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.md']}
    bands=root/'code/docs/connection_reference_bands.json';assert bands.exists();hashes[str(bands)]=sha256(bands)
    for f in ['differentiable_mini.py','diffusion_adapter.py','soft_sequence_chart.py']:
        assert sha256(root/'code/src/fastglycan/models'/f)==sha256(train/'code/src/fastglycan/models'/f)
    assignments=[[] for _ in range(8)];loads=[0]*8
    for row in sorted(cache_lock['rows'],key=lambda r:(-len(r['sequence']),r['group_id'])):
        i=min(range(8),key=lambda j:(loads[j],j));assignments[i].append(row);loads[i]+=len(row['sequence'])**2
    write_json(root/'lock.json',dict(train=str(train),cache=str(cache),source=cache_lock['source'],
        rows=cache_lock['rows'],assignments=assignments,checkpoints=audit['checkpoints'],
        hashes=hashes,input_hashes=inputs,weights_sha256=cache_lock['weights_sha256'],weight_stats=cache_lock['weight_stats'],
        train_seeds=cache_lock['train_seeds'],validation_seeds=cache_lock['validation_seeds'],
        models=['native_s1','native_s2','gt','gt_s2'],probe=next(r for r in cache_lock['rows'] if r['role']=='train'),
        bootstrap=dict(replicates=10000,seed=20260930,unit='protein after mean over two noises'),
        primary='validation mean paired all-atom lDDT; no best checkpoint/seed or pooled TRAIN+VAL'))


def run_diffusion_evaluation(root,index):
    from fastglycan import stage0_confirm_runtime as rt
    from fastglycan.models.soft_sequence_chart import device_tree
    from fastglycan.models.differentiable_mini import diffusion_from_conditioning
    from fastglycan.models.diffusion_adapter import attach_diffusion_adapter, merge_diffusion_adapter
    from fastglycan.hybrid_proposals import identity_noise
    lock=json.loads((root/'lock.json').read_text());cache=Path(lock['cache']);source=Path(lock['source'])
    folder=root/f'worker_{index}';folder.mkdir(exist_ok=False);start=time.monotonic()
    report=dict(complete=False,index=index,rows=[],lock_sha256=sha256(root/'lock.json'))
    try:
        for path,digest in lock['hashes'].items():assert sha256(Path(path))==digest
        for path,stat in lock['weight_stats'].items():assert [Path(path).stat().st_size,Path(path).stat().st_mtime_ns]==stat
        torch.set_num_threads(1);runner=rt.runner_setup(folder/'work');runner.configs.dtype='fp32'
        model=runner.model.eval().requires_grad_(False)
        assert all(p.dtype==torch.float32 for p in model.parameters() if p.is_floating_point())
        probe=lock['probe'];data=cache/'examples'/probe['group_id']
        saved=torch.load(data/'conditioning.pt',map_location='cpu',weights_only=False)
        flat=saved['conditioning_flat'].cuda();features=device_tree(saved['features'],'cuda')
        conditioning=tuple(x.reshape(s) for x,s in zip(flat.split(saved['sizes']),saved['shapes']))
        atoms=torch.load(source/'chemistry'/probe['group_id']/'native.pt',map_location='cpu',weights_only=False)['atoms']
        noise=identity_noise(atoms,lock['train_seeds'][0],device='cuda');models={'native':model};probe_results={}
        with torch.no_grad():
            native=diffusion_from_conditioning(model,features,noise.clone(),conditioning,steps=1).reshape(-1,3)
            assert np.array_equal(native.cpu().numpy(),np.load(data/f's1_seed{lock["train_seeds"][0]}.npy'))
            for arm in lock['checkpoints']:
                student=copy.deepcopy(model);adapters=attach_diffusion_adapter(student)
                zero=diffusion_from_conditioning(student,features,noise.clone(),conditioning,steps=1).reshape(-1,3)
                assert torch.equal(zero,native)
                checkpoint=lock['checkpoints'][arm];assert sha256(Path(checkpoint['path']))==checkpoint['sha256']
                state=torch.load(checkpoint['path'],map_location='cpu',weights_only=False)
                assert state['update']==512 and state['arm']==arm and set(state['trained'])==set(adapters)
                for name,adapter in adapters.items():adapter.load_state_dict(state['trained'][name])
                unmerged=diffusion_from_conditioning(student,features,noise.clone(),conditioning,steps=1).reshape(-1,3)
                merge_diffusion_adapter(student,adapters);student.requires_grad_(False)
                merged=diffusion_from_conditioning(student,features,noise.clone(),conditioning,steps=1).reshape(-1,3)
                assert torch.equal(unmerged,merged) and torch.isfinite(merged).all()
                assert set(student.state_dict())==set(model.state_dict())
                probe_results[arm]=dict(zero_parity=True,merged_parity=True,restored_native_state_keys=True)
                np.save(folder/f'{arm}_probe.npy',merged.cpu().numpy());models[arm]=student
                del student,adapters,state,zero,unmerged,merged
        del saved,flat,features,conditioning,atoms,noise,native
        report['probe']=probe_results;report['probe_nfe']=1+3*len(lock['checkpoints'])
        calls={name:0 for name in models};handles=[]
        for name,m in models.items():
            handles.append(m.diffusion_module.register_forward_hook(lambda *unused,key=name:calls.__setitem__(key,calls[key]+1)))
        with torch.no_grad():
            for row in lock['assignments'][index]:
                g=row['group_id'];target=root/'examples'/g;target.mkdir(parents=True,exist_ok=False)
                data=cache/'examples'/g;path=data/'conditioning.pt';assert sha256(path)==lock['input_hashes'][str(path)]
                saved=torch.load(path,map_location='cpu',weights_only=False);assert saved['role']==row['role']
                flat=saved['conditioning_flat'].cuda();features=device_tree(saved['features'],'cuda')
                conditioning=tuple(x.reshape(s) for x,s in zip(flat.split(saved['sizes']),saved['shapes']))
                atoms=torch.load(source/'chemistry'/g/'native.pt',map_location='cpu',weights_only=False)['atoms']
                entries=[];seeds=lock['train_seeds'] if row['role']=='train' else lock['validation_seeds']
                for seed in seeds:
                    noise=identity_noise(atoms,seed,device='cuda')
                    for name in lock['models']:
                        file=target/f'{name}_seed{seed}.npy';steps=2 if name=='native_s2' else 1
                        reused=lock.get('reuse_models',{}).get(name)
                        cached=row['role']=='train' and (name.startswith('native') or reused is not None)
                        if cached:
                            previous=(Path(reused['root'])/g/f'{reused["model"]}_seed{seed}.npy'
                                if reused else data/f's{steps}_seed{seed}.npy')
                            assert sha256(previous)==lock['input_hashes'][str(previous)];shutil.copyfile(previous,file);seconds=None
                        else:
                            selected=models['native' if name.startswith('native') else name]
                            torch.cuda.synchronize();begin=time.monotonic()
                            cpu_rng=torch.get_rng_state().clone();gpu_rng=torch.cuda.get_rng_state().clone()
                            coordinate=diffusion_from_conditioning(selected,features,noise.clone(),conditioning,steps=steps).reshape(-1,3)
                            torch.cuda.synchronize();seconds=time.monotonic()-begin
                            assert torch.isfinite(coordinate).all()
                            assert torch.equal(cpu_rng,torch.get_rng_state()) and torch.equal(gpu_rng,torch.cuda.get_rng_state())
                            np.save(file,coordinate.cpu().numpy());del coordinate
                        entries.append(dict(model=name,seed=seed,name=file.name,sha256=sha256(file),
                            cached_native_train=cached and name.startswith('native'),
                            reused_prediction=cached,nfe=0 if cached else steps,seconds=seconds))
                result=dict(group_id=g,role=row['role'],entries=entries,lock_sha256=sha256(root/'lock.json'))
                write_json(target/'report.json',result);report['rows'].append(result);write_json(folder/'report.json',report)
                del saved,flat,features,conditioning,atoms,noise
                torch.cuda.empty_cache()
        nval=sum(r['role']=='validation' for r in lock['assignments'][index]);n=len(lock['assignments'][index])
        assert calls==dict(native=6*nval,**{arm:2*n for arm in lock['checkpoints']})
        for h in handles:h.remove()
        report.update(complete=True,calls=calls,peak_gpu_bytes=torch.cuda.max_memory_allocated(),
            timing_scope='diffusion only with cached conditioning; includes reference cache rebuild, not ESM/PF runtime')
    except Exception:report['error']=traceback.format_exc()
    finally:report['seconds']=time.monotonic()-start;write_json(folder/'report.json',report)
    if not report['complete']:raise RuntimeError(report.get('error','incomplete'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--mode',choices=['prepare','worker'],required=True);p.add_argument('--index',type=int);a=p.parse_args()
    assert Path(os.environ['PROTENIX_ROOT_DIR']).resolve()==(a.root.parent/'protenix_stage0_pkg/v1_1/runtime').resolve()
    assert os.environ.get('LAYERNORM_TYPE')=='torch'
    if a.mode=='prepare':prepare_diffusion_evaluation(a.root)
    else:run_diffusion_evaluation(a.root,a.index)
