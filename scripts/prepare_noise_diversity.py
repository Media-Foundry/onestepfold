#!/usr/bin/env python3
"""Build same-platform native S2 teachers for fixed and fresh training noise."""
import argparse
import json
import time
from pathlib import Path
import numpy as np
import torch
from fastglycan.noise_diversity import diverse_exposure_order
from fastglycan.paired_teacher_protocol import sha256,write_json


def prepare_noise_diversity_cache(root):
    assert not (root/'cache_plan.json').exists()
    control=root.parent/'rocm_matched_training_v1_20261001/weak'
    base=json.loads((control/'lock.json').read_text())
    audit=json.loads((control.parent/'terminal_audit.json').read_text());assert audit['complete']
    assert audit['training_locks']['weak']==sha256(control/'lock.json')
    groups=base['arms']['expanded'];seeds={g:set(base['training_seeds']) for g in groups}
    order=diverse_exposure_order(base['orders']['expanded'])
    for item in order:seeds[item['group_id']].add(item['seed'])
    assert sum(map(len,seeds.values()))==9038
    cache=root/'cache';cache.mkdir(exist_ok=False);old=Path(base['cache']);files={}
    previous=root.parent/'rocm_matched_evaluation_v1_20261001/lock.json'
    evaluation=json.loads(previous.read_text());native_files={}
    for g in groups:
        native=Path(base['source'])/'chemistry'/g/'native.pt'
        native_files[str(native)]=sha256(native)
        assert native_files[str(native)]==evaluation['input_hashes'][str(native)]
        destination=cache/'examples'/g;destination.mkdir(parents=True)
        for name in ['conditioning.pt','gt_supervision.pt']:
            original=old/'examples'/g/name;assert sha256(original)==base['cache_files'][str(original)]
            target=destination/name;target.symlink_to(original);files[str(target)]=sha256(target)
        for seed in base['training_seeds']:
            original=old/'examples'/g/f's1_seed{seed}.npy'
            if original.exists():
                target=destination/original.name;target.symlink_to(original);files[str(target)]=sha256(target)
    # Engineering anchors are explicit ROCm public S1 references, never overwrite CUDA data.
    for g,ref in base['backend']['engineering_references'].items():
        target=cache/'examples'/g/'s1_seed600001.npy';target.unlink()
        target.symlink_to(Path(ref['public']));files[str(target)]=sha256(target)
        assert files[str(target)]==base['hashes'][ref['public']]
    rows={r['group_id']:r for r in base['rows']};assignments=[[] for _ in range(8)];loads=[0]*8
    for g in sorted(groups,key=lambda g:(-len(rows[g]['sequence']),g)):
        i=min(range(8),key=lambda i:(loads[i],i));assignments[i].append(g);loads[i]+=len(rows[g]['sequence'])**2*len(seeds[g])
    hashes={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.json','.md']}
    write_json(root/'cache_plan.json',dict(complete=True,control=str(control),control_lock_sha256=sha256(control/'lock.json'),
        source_cache=str(old),source=base['source'],groups=groups,seeds={g:sorted(s) for g,s in seeds.items()},
        assignments=assignments,files=files,native_files=native_files,hashes=hashes,teachers=9038,teacher_nfe=18076,
        engineering_groups=base['engineering_groups'],weight_stats=base['weight_stats'],weights_sha256=evaluation['weights_sha256']))


def generate_noise_teachers(root,index):
    from fastglycan import stage0_confirm_runtime as rt
    from fastglycan.models.differentiable_mini import diffusion_from_conditioning
    from fastglycan.models.soft_sequence_chart import device_tree
    from fastglycan.hybrid_proposals import identity_noise
    torch.set_num_threads(1);plan=json.loads((root/'cache_plan.json').read_text())
    folder=root/f'teacher_worker_{index}';folder.mkdir(exist_ok=False);begin=time.monotonic()
    for p,h in plan['hashes'].items():assert sha256(Path(p))==h
    for p,stat in plan['weight_stats'].items():assert [Path(p).stat().st_size,Path(p).stat().st_mtime_ns]==stat
    runner=rt.runner_setup(folder/'work');runner.configs.dtype='fp32';model=runner.model.eval().requires_grad_(False)
    count=[0];handle=model.diffusion_module.register_forward_hook(lambda *unused:count.__setitem__(0,count[0]+1))
    records=[];source=Path(plan['source'])
    with torch.no_grad():
        for g in plan['assignments'][index]:
            data=root/'cache/examples'/g;path=data/'conditioning.pt';assert sha256(path)==plan['files'][str(path)]
            saved=torch.load(path,map_location='cpu',weights_only=False);assert saved['role']=='train' and saved['group_id']==g
            flat=saved['conditioning_flat'].cuda();features=device_tree(saved['features'],'cuda')
            cond=tuple(x.reshape(s) for x,s in zip(flat.split(saved['sizes']),saved['shapes']))
            native=source/'chemistry'/g/'native.pt'
            assert sha256(native)==plan['native_files'][str(native)]
            atoms=torch.load(native,map_location='cpu',weights_only=False)['atoms'];files={}
            for seed in plan['seeds'][g]:
                file=data/f's2_seed{seed}.npy';assert not file.exists()
                noise=identity_noise(atoms,seed,device='cuda');cpu=torch.get_rng_state().clone();gpu=torch.cuda.get_rng_state().clone()
                x=diffusion_from_conditioning(model,features,noise,cond,steps=2).reshape(-1,3)
                assert torch.isfinite(x).all() and torch.equal(cpu,torch.get_rng_state()) and torch.equal(gpu,torch.cuda.get_rng_state())
                np.save(file,x.cpu().numpy());files[str(file)]=sha256(file)
            records.append(dict(group_id=g,files=files));write_json(folder/'progress.json',dict(records=records,complete=False))
            del saved,flat,features,cond,atoms,x,noise;torch.cuda.empty_cache()
    handle.remove();assert count[0]==2*sum(len(r['files']) for r in records)
    write_json(folder/'report.json',dict(complete=True,index=index,records=records,nfe=count[0],seconds=time.monotonic()-begin,
        cache_plan_sha256=sha256(root/'cache_plan.json'),parameter_updates=0))


def collect_noise_teachers(root):
    plan=json.loads((root/'cache_plan.json').read_text());execution=json.loads((root/'teacher_execution.json').read_text())
    assert execution['complete'] and all(j['exit_code']==0 for j in execution['jobs']) and len(execution['jobs'])==8
    files=dict(plan['files']);seen=set();nfe=0
    for i,groups in enumerate(plan['assignments']):
        p=root/f'teacher_worker_{i}/report.json';r=json.loads(p.read_text());assert r['complete'] and r['cache_plan_sha256']==sha256(root/'cache_plan.json')
        assert [x['group_id'] for x in r['records']]==groups;nfe+=r['nfe']
        for x in r['records']:
            g=x['group_id'];assert g not in seen;seen.add(g)
            assert set(x['files'])=={str(root/'cache/examples'/g/f's2_seed{s}.npy') for s in plan['seeds'][g]}
            files.update(x['files'])
    assert seen==set(plan['groups']) and nfe==18076
    for p,h in files.items():
        assert sha256(Path(p))==h
        if Path(p).name.startswith('s2_seed'):
            x=np.load(p);assert x.dtype==np.float32 and x.ndim==2 and x.shape[1]==3 and np.isfinite(x).all()
    cache=root/'cache'
    write_json(cache/'lock.json',dict(schema='noise_diversity_teacher_cache_v1',plan_sha256=sha256(root/'cache_plan.json'),
        groups=plan['groups'],seeds=plan['seeds'],source=plan['source'],teacher='frozen public native C4/S2, synthetic not experimental GT'))
    write_json(cache/'artifact_manifest.json',files)
    write_json(cache/'audit.json',dict(complete=True,teachers=9038,nfe=nfe,files=len(files),
        lock_sha256=sha256(cache/'lock.json'),manifest_sha256=sha256(cache/'artifact_manifest.json')))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--mode',choices=['prepare','worker','collect'],required=True);p.add_argument('--index',type=int)
    a=p.parse_args()
    if a.mode=='prepare':prepare_noise_diversity_cache(a.root)
    elif a.mode=='worker':generate_noise_teachers(a.root,a.index)
    else:collect_noise_teachers(a.root)
