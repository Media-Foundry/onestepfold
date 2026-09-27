#!/usr/bin/env python3
"""Exact optimizer continuation of the locked pretrained ESMC scaling pair."""
import argparse
from collections import Counter, OrderedDict
from datetime import timedelta
import json
import logging
import os
from pathlib import Path
import time

import numpy as np
import torch
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel

from fastglycan.frame_supervision import training_sampler_seed
from fastglycan.models.esmc_core import ESMCFoldCore
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.pretrained_conditioning import install_pretrained_bridge
from fastglycan.pretrained_gt import configure_gt_optimizer, gt_epoch_batches, gt_loss_parts
from fastglycan.teacher_pairing import feature_digest


def gather(value):
    values=[None]*dist.get_world_size()
    dist.all_gather_object(values,value)
    return values


def identical(value):
    values=gather(value)
    assert all(x==value for x in values),values


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--size',type=int,choices=(2048,8192),required=True)
    a=p.parse_args();root=a.root.resolve();rank=int(os.environ['LOCAL_RANK'])
    assert int(os.environ['WORLD_SIZE'])==4 and torch.cuda.device_count()==4
    torch.cuda.set_device(rank);torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
    dist.init_process_group('nccl',timeout=timedelta(seconds=600),device_id=torch.device('cuda',rank))
    started=time.monotonic();lock=json.loads((root/'lock.json').read_text())
    assert torch.cuda.get_device_name()==lock['gpu_model']
    assert lock['max_updates']==16384 and lock['global_batch']==4
    assert lock['training_sizes']==[2048,8192]
    for name,digest in lock['common_files'].items():assert sha256(root/name)==digest,name
    source=json.loads((root/'code_v1/source_manifest.json').read_text())
    for name,digest in source['files'].items():assert sha256(root/'code_v1'/name)==digest,name
    acceptance=json.loads((root/'data_acceptance.json').read_text())
    assert acceptance['complete'] and acceptance['groups']==8320
    assert acceptance['data_manifest_sha256']==sha256(root/'data_manifest.json')
    manifest=json.loads((root/'data_manifest.json').read_text())
    rows=manifest['selection'];train=[r for r in rows if r['split']=='train'][:a.size]
    val=[r for r in rows if r['split']=='validation']
    byid={r['group_id']:r for r in rows};probe=[byid[g] for g in lock['train_probe_groups']]
    assert len(train)==a.size and len(val)==128 and len(probe)==32
    assert {r['group_id'] for r in probe}<={r['group_id'] for r in train}
    out=root/('train_%d'%a.size)
    if rank==0:out.mkdir(exist_ok=False)
    dist.barrier()
    import protenix
    from protenix.utils.seed import seed_everything
    package=Path(protenix.__file__).resolve().parent
    contract=json.loads((root/'runtime_contract.json').read_text())
    for path,digest in contract['runtime_source_sha256'].items():
        assert sha256(package/path.split('/site-packages/protenix/',1)[1])==digest
    native={k.removeprefix('module.'):v for k,v in torch.load(root/'native.pt',map_location='cpu',weights_only=True)['model'].items()}
    bridge=torch.load(root/'bridge.pt',map_location='cpu',weights_only=True)
    model=ESMCFoldCore(seed=101,deterministic_capacity=True)
    assert model.config.to_dict()==contract['config']
    install_pretrained_bridge(model,native,bridge);del native,bridge
    model.cuda().train();optimizer=configure_gt_optimizer(model)
    initial=feature_digest(model.state_dict());identical(initial)
    assert initial==lock['initial_model_state_sha256']
    parent=Path(lock['parent_root'])
    assert sha256(parent/'lock.json')==lock['parent_lock_sha256']
    resume=parent/('train_%d'%a.size)/'step_4096.pt'
    assert sha256(resume)==lock['resume_sha256'][str(a.size)]
    saved=torch.load(resume,map_location='cpu',weights_only=True)
    assert saved['step']==4096 and saved['samples_seen']==16384 and saved['training_size']==a.size
    assert saved['lock_sha256']==lock['parent_lock_sha256']
    model.load_state_dict(saved['model'],strict=True)
    optimizer.load_state_dict(saved['optimizer'])
    assert feature_digest(optimizer.state_dict())==feature_digest(saved['optimizer'])
    assert feature_digest(model.state_dict())==saved['model_state_sha256']
    assert all(int(v['step'].item())==4096 for v in optimizer.state.values())
    identical(feature_digest(model.state_dict()))
    del saved
    frozen=lambda:feature_digest({n:p for n,p in model.named_parameters() if not p.requires_grad})
    frozen_hash=frozen();ddp=DistributedDataParallel(model,device_ids=[rank],find_unused_parameters=True)
    logging.getLogger('protenix.model.modules.embedders').setLevel(logging.ERROR)
    counts={};sampling={};handles=[]
    for name,module in [('trunk',model.core.pairformer_stack),('structure',model.core.diffusion_module),('confidence',model.core.confidence_head)]:
        def hook(*_,name=name):counts[name]+=1
        handles.append(module.register_forward_pre_hook(hook))
    original=model.core.sample_diffusion
    def sampler(**kwargs):
        sampling.update(noise_schedule=kwargs['noise_schedule'].detach().cpu().tolist(),N_sample=kwargs['N_sample'],
                        parameters={k:model.config.sample_diffusion[k] for k in ('gamma0','gamma_min','noise_scale_lambda','step_scale_eta')})
        assert sampling==lock['sampling']
        return original(**kwargs)
    model.core.sample_diffusion=sampler
    cache=OrderedDict();verified=set()
    def packet(group):
        if group in cache:
            cache.move_to_end(group);return cache[group]
        folder=root/'data'/group
        if group not in verified:
            for name in ('inputs.pt','supervision.pt'):
                assert sha256(folder/name)==manifest['data_files'][group][name],(group,name)
            verified.add(group)
        data=torch.load(folder/'inputs.pt',map_location='cpu',weights_only=True)
        data['supervision']=torch.load(folder/'supervision.pt',map_location='cpu',weights_only=True)
        assert data['features']['esm_token_embedding'].shape==(len(byid[group]['sequence']),1152)
        cache[group]=data
        while len(cache)>16:cache.popitem(last=False)
        return data
    def forward(data,noise,training):
        seed_everything(noise,deterministic=True)
        counts.update(trunk=0,structure=0,confidence=0)
        if training:
            result=ddp(data['features'],confidence=False)
        else:
            with torch.no_grad():result=model(data['features'],confidence=False)
        assert counts=={'trunk':1,'structure':1,'confidence':0}
        x=result['coordinate'][0];assert torch.isfinite(x).all()
        return x,result['timing']
    def save(step,immutable=False):
        if rank==0:
            path=out/('step_%04d.pt'%step if immutable else 'recovery.pt')
            if immutable:assert not path.exists()
            temp=path.with_suffix('.partial')
            torch.save({'model':model.state_dict(),'optimizer':optimizer.state_dict(),'step':step,
                        'samples_seen':step*4,'training_size':a.size,'lock_sha256':sha256(root/'lock.json'),
                        'initial_model_state_sha256':initial,'seed_rule':'group_id and one-based dataset epoch',
                        'model_state_sha256':feature_digest(model.state_dict())},temp)
            os.replace(temp,path)
        dist.barrier()
    def evaluate(step):
        before=time.monotonic();state=feature_digest(model.state_dict());identical(state)
        model.eval();items=[];evalrows=val+probe
        folder=out/'predictions'/('step_%04d'%step)
        if rank==0:folder.mkdir(parents=True,exist_ok=False)
        dist.barrier()
        for index,row in enumerate(evalrows[rank::4]):
            group=row['group_id'];data=packet(group)
            for noise in lock['evaluation_seeds']:
                x,timing=forward(data,noise,False);x=x.detach().cpu().numpy()
                if index==0:
                    repeat,_=forward(data,noise,False)
                    assert np.array_equal(x,repeat.detach().cpu().numpy())
                if step==4096:
                    previous=parent/('train_%d'%a.size)/'predictions/step_4096'/(group+'_'+str(noise)+'.npy')
                    assert sha256(previous)==lock['resume_predictions'][str(a.size)][group][str(noise)]
                    assert np.array_equal(x,np.load(previous,allow_pickle=False)),('initial replay',group,noise)
                path=folder/(group+'_'+str(noise)+'.npy');np.save(path,x)
                items.append({'group_id':group,'split':row['split'],'noise':noise,'path':str(path.relative_to(root)),
                              'sha256':sha256(path),'counts':dict(counts),'sampling':dict(sampling),'timing':timing})
        model.train();assert feature_digest(model.state_dict())==state
        lists=gather(items);seconds=max(gather(time.monotonic()-before))
        if rank==0:
            result={'complete':True,'step':step,'size':a.size,'model_state_sha256':state,'predictions':sum(lists,[]),
                    'lock_sha256':sha256(root/'lock.json'),'evaluation_seconds':seconds,'weights_unchanged':True,
                    'parent_replay_exact':step==4096,'selection':'Fixed DEV128 plus common TRAIN32, two single-sample noises; no best-of-K'}
            assert len(result['predictions'])==320
            write_json(out/('evaluation_%04d.json'%step),result)
            print(json.dumps({'evaluation_complete':step,'seconds':seconds}),flush=True)
        return seconds
    report={'complete':False,'size':a.size,'world_size':4,'initial_model_state_sha256':initial,
            'lock_sha256':sha256(root/'lock.json'),'runtime':{'torch':torch.__version__,'hip':torch.version.hip,'gpu':torch.cuda.get_device_name()},
            'max_updates':lock['max_updates'],'evaluation_steps':lock['evaluation_steps']}
    if rank==0:write_json(out/'contract.json',report)
    save(4096,immutable=True);evaluation_seconds=evaluate(4096)
    step=4096;epoch=4096*4//a.size+1;seen=Counter();residues_seen=0;training_seconds=0.;checkpoint_seconds=0.
    while step<lock['max_updates']:
        for batch in gt_epoch_batches(train,epoch):
            if step>=lock['max_updates']:break
            begin=time.monotonic();row=batch[rank];data=packet(row['group_id'])
            optimizer.zero_grad(set_to_none=True)
            x,_=forward(data,training_sampler_seed(row['group_id'],epoch),True)
            parts=gt_loss_parts(x,data['labels'],data['supervision']);sum(parts).backward()
            norm=torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad],10,error_if_nonfinite=True)
            optimizer.step();torch.cuda.synchronize();elapsed=time.monotonic()-begin
            local={'group_id':row['group_id'],'length':len(row['sequence']),'weighted_losses':[float(v.detach()) for v in parts],
                   'preclip_norm':float(norm),'seconds':elapsed}
            allrows=gather(local);step+=1
            assert len({r['group_id'] for r in allrows})==4
            duration=max(r['seconds'] for r in allrows);training_seconds+=duration
            for r in allrows:seen[r['group_id']]+=1;residues_seen+=r['length']
            if rank==0:
                with (out/'training.jsonl').open('a') as f:f.write(json.dumps({'step':step,'epoch':epoch,'samples_seen':step*4,'rows':allrows})+'\n')
                if step%16==0 or step==1:
                    progress={'step':step,'epoch':epoch,'samples_seen':step*4,'unique_train_seen':len(seen),
                              'residues_seen':residues_seen,'training_seconds':training_seconds,'elapsed_seconds':time.monotonic()-started,
                              'evaluation_seconds':evaluation_seconds,'checkpoint_seconds':checkpoint_seconds,'last_update_seconds':duration}
                    write_json(out/'progress.json',progress);print(json.dumps(progress),flush=True)
            del x,parts,data
            if step%128==0:
                startsave=time.monotonic();save(step,immutable=step in lock['evaluation_steps'])
                checkpoint_seconds+=time.monotonic()-startsave
            if step in lock['evaluation_steps']:evaluation_seconds+=evaluate(step)
        epoch+=1
    assert set(seen)=={r['group_id'] for r in train}
    assert set(seen.values())=={(lock['max_updates']-4096)*4//a.size}
    assert frozen()==frozen_hash and all(torch.isfinite(p).all() for p in model.parameters())
    state=feature_digest(model.state_dict());identical(state)
    if rank==0:
        report.update(complete=True,resume_step=4096,additional_samples_seen=(step-4096)*4,steps=step,samples_seen=step*4,residues_seen=residues_seen,exposures=dict(seen),
                      training_seconds=training_seconds,evaluation_seconds=evaluation_seconds,checkpoint_seconds=checkpoint_seconds,
                      elapsed_seconds=time.monotonic()-started,final_model_state_sha256=state,frozen_heads_unchanged=True,
                      training_log_sha256=sha256(out/'training.jsonl'),last_checkpoint_sha256=sha256(out/('step_%04d.pt'%step)),
                      peak_gpu_allocated_bytes_by_rank=gather(torch.cuda.max_memory_allocated()))
        write_json(out/'report.json',report);print(json.dumps({'complete':True,'size':a.size,'steps':step}),flush=True)
    else:gather(torch.cuda.max_memory_allocated())
    for handle in handles:handle.remove()
    dist.barrier();dist.destroy_process_group()


if __name__=='__main__':main()
