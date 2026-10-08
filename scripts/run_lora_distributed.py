"""torchrun paired DDP: preserve two-candidate update, benchmark before handoff."""
import argparse
import copy
import json
import os
from pathlib import Path
import time
from datetime import timedelta

from fastglycan.paired_distributed import configure_torchrun_worker


def run_distributed(args):
    rank,world,address=configure_torchrun_worker(args.devices)
    import numpy as np
    import torch
    import torch.distributed as dist
    from torch.nn.parallel import DistributedDataParallel as DDP
    from fastglycan.models.recycle_lora import RecycleLoRA
    from fastglycan.paired_distributed import CandidateStructureLoss,atomic_checkpoint,paired_local_index
    from fastglycan.reference_editor_multiref import multiref_update,editor_state_digest
    from fastglycan.paired_teacher_protocol import sha256,write_json
    from run_recycle_lora import LoRARuntime
    from run_reference_editor import coordinate_objective
    paired_local_index(rank,world)
    rt=LoRARuntime(args.source,str(args.output/f'work_{rank}_{time.time_ns()}'));b=rt.base
    dist.init_process_group('nccl',init_method=address,rank=rank,world_size=world,timeout=timedelta(minutes=10))
    torch.cuda.set_device(0)
    cp=torch.load(args.checkpoint,map_location='cpu',weights_only=False)
    checkpoint_digest=sha256(args.checkpoint)
    assert cp['seed']==args.seed and cp['lock_sha256']==sha256(args.source/'lora_lock.json')
    bank=RecycleLoRA(rt.model.pairformer_stack,**cp['config']).cuda();bank.load_state_dict(cp['state_dict'])
    wrapper=CandidateStructureLoss(bank,rt,coordinate_objective)
    ddp=DDP(wrapper,device_ids=[0],broadcast_buffers=False,gradient_as_bucket_view=True)
    opt=torch.optim.AdamW(bank.parameters(),lr=1e-4,weight_decay=1e-4,eps=1e-8);opt.load_state_dict(cp['optimizer'])
    keys=sorted([s['site_key'] for s in b.plan['sites'] if s['role_n15']=='train'],
                key=lambda k:(b.sites[k]['parent_index'],b.sites[k]['position_zero_based']))
    schedule=dict(updates=8208,train_site_keys=keys)
    args.output.mkdir(parents=True,exist_ok=True)
    start=int(cp['step']);records=[]
    if args.mode=='benchmark':
        serial_bank=RecycleLoRA(rt.model.pairformer_stack,**cp['config']).cuda() if rank==0 else None
        serial_opt=torch.optim.AdamW(serial_bank.parameters(),lr=1e-4,weight_decay=1e-4,eps=1e-8) if rank==0 else None
        equivalence=[]
        for j in range(4):
            site,choices=multiref_update(schedule,b.sites,start+j)
            if rank==0:
                serial_bank.load_state_dict(bank.state_dict());serial_opt.load_state_dict(copy.deepcopy(opt.state_dict()))
                serial_opt.zero_grad(set_to_none=True)
                for aa in choices:
                    item,c=rt.conditioning(serial_bank,site,aa);x=b.decode(item,c,0)
                    loss=coordinate_objective(x,item['teacher'][0],item['ca'],item['labels'])[0]
                    (loss/2).backward()
                expected=[p.grad.detach().clone() for p in serial_bank.parameters()]
                torch.nn.utils.clip_grad_norm_(serial_bank.parameters(),1.,error_if_nonfinite=True);serial_opt.step()
            dist.barrier();opt.zero_grad(set_to_none=True)
            loss=ddp(site,choices[rank]);loss.backward()
            if rank==0:
                errors=[]
                for actual,target in zip(bank.parameters(),expected):
                    torch.testing.assert_close(actual.grad,target,rtol=1e-5,atol=1e-7)
                    errors.append(float((actual.grad-target).abs().max()))
            torch.nn.utils.clip_grad_norm_(bank.parameters(),1.,error_if_nonfinite=True);opt.step()
            if rank==0:
                parameter_error=max(float((a-bp).abs().max()) for a,bp in zip(bank.parameters(),serial_bank.parameters()))
                for a,bp in zip(bank.parameters(),serial_bank.parameters()):torch.testing.assert_close(a,bp,rtol=1e-5,atol=1e-7)
                equivalence.append(dict(step=j,gradient_max_abs=max(errors),parameter_max_abs=parameter_error))
            dist.barrier()
        # Representative deterministic index set: all27contexts, two updates/site.
        indices=[i*304+j for i in range(27) for j in (0,1)]
        for mode in ('parallel','serial','serial','parallel'):
            bank.load_state_dict(cp['state_dict']);opt.load_state_dict(copy.deepcopy(cp['optimizer']))
            if rank==0 and mode=='serial':
                serial_bank.load_state_dict(cp['state_dict']);serial_opt.load_state_dict(copy.deepcopy(cp['optimizer']))
            dist.barrier();torch.cuda.synchronize();begin=time.perf_counter()
            for k in indices:
                site,choices=multiref_update(schedule,b.sites,k)
                if mode=='parallel':
                    opt.zero_grad(set_to_none=True);ddp(site,choices[rank]).backward()
                    torch.nn.utils.clip_grad_norm_(bank.parameters(),1.,error_if_nonfinite=True);opt.step()
                elif rank==0:
                    serial_opt.zero_grad(set_to_none=True)
                    for aa in choices:
                        item,c=rt.conditioning(serial_bank,site,aa)
                        loss=coordinate_objective(b.decode(item,c,0),item['teacher'][0],item['ca'],item['labels'])[0]
                        (loss/2).backward()
                    torch.nn.utils.clip_grad_norm_(serial_bank.parameters(),1.,error_if_nonfinite=True);serial_opt.step()
            torch.cuda.synchronize();dist.barrier();elapsed=time.perf_counter()-begin
            if rank==0:records.append(dict(mode=mode,seconds=elapsed,updates=len(indices)))
        rt.finish()
        if rank==0:
            write_json(args.output/'benchmark.json',dict(complete=True,equivalence=equivalence,timing=records,
                source_checkpoint_sha256=checkpoint_digest,world_size=world,runtime=b.runtime,
                discarded_updates_per_arm=4+108,peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                rtol=1e-5,atol=1e-7))
    else:
        history=args.output/'history.jsonl'
        if not 4104<=start<=8208:raise ValueError('migration starts at4104; later atomic checkpoints may resume')
        prefix=history if start>4104 else args.source/'runs'/str(args.seed)/'history.jsonl'
        if rank==0:
            rows=[json.loads(s) for s in prefix.read_text().splitlines() if s.strip()]
            rows=[r for r in rows if r['step']<=start]
            assert len(rows)==start and [r['step'] for r in rows]==list(range(1,start+1))
            history.write_text(''.join(json.dumps(r)+'\n' for r in rows))
        dist.barrier();begin=time.monotonic()
        for step in range(start,8208):
            site,choices=multiref_update(schedule,b.sites,step)
            opt.zero_grad(set_to_none=True);loss=ddp(site,choices[rank]);assert torch.isfinite(loss);loss.backward()
            norm=torch.nn.utils.clip_grad_norm_(bank.parameters(),1.,error_if_nonfinite=True);opt.step()
            components=[None,None];dist.all_gather_object(components,wrapper.last_components)
            if rank==0:
                row=dict(step=step+1,site=site['site_key'],aa=choices,components=components,gradient_norm=float(norm),clipped=bool(norm>1))
                with history.open('a') as f:f.write(json.dumps(row,allow_nan=False)+'\n')
                if (step+1)%128==0 or step+1==8208:
                    payload=dict(state_dict=bank.state_dict(),optimizer=opt.state_dict(),step=step+1,seed=args.seed,
                                 config=bank.config,lock_sha256=cp['lock_sha256'],source_checkpoint_sha256=checkpoint_digest,
                                 execution='paired_DDP_world2',world_size=2)
                    atomic_checkpoint(args.output/'latest.pt',payload)
                    write_json(args.output/'progress.json',dict(step=step+1,seconds=time.monotonic()-begin,complete=step+1==8208))
                    print('DDP_TRAIN',args.seed,step+1,time.monotonic()-begin,flush=True)
                if step+1==8208:
                    atomic_checkpoint(args.output/'checkpoints'/'8208.pt',payload)
            dist.barrier()
        rt.finish()
        digests=[None,None];dist.all_gather_object(digests,editor_state_digest(bank));assert len(set(digests))==1
        counts=[None,None];dist.all_gather_object(counts,dict(b.counts))
        if rank==0:write_json(args.output/'training_complete.json',dict(complete=True,step=8208,replica_hashes=digests,
              seconds=time.monotonic()-begin,rank_counts=counts,counts_scope='this continuation attempt per rank',runtime=b.runtime,
              history_sha256=sha256(history),peak_allocated_bytes=torch.cuda.max_memory_allocated()))
    dist.barrier();dist.destroy_process_group()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--seed',type=int,required=True)
    p.add_argument('--devices',type=int,nargs=2,required=True);p.add_argument('--mode',choices=['benchmark','train'],required=True)
    run_distributed(p.parse_args())
