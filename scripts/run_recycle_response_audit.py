"""Read-only WT3/target3/target4 response diagnostic with native replay gates."""
import argparse
import json
from pathlib import Path
import time
import numpy as np
import torch

from fastglycan.response_moments import ResponseMoments
from fastglycan.models.recycle_lora import RecycleLoRA
from fastglycan.models.compensated_recycle import initialize_cached_recycle,capture_cached_prefix,native_recycle_step
from fastglycan.paired_teacher_protocol import sha256,write_json
from run_recycle_lora import LoRARuntime
from run_reference_editor import state_hash


def run_recycle_response_audit(args):
    begin=time.monotonic()
    lock=json.loads((args.root/'audit_lock.json').read_text())
    for name,digest in lock['code'].items():assert sha256(args.root/'code'/name)==digest,name
    assert sha256(args.root/'protocol.md')==lock['protocol_sha256']
    noise=Path(lock['noise_root']);source=Path(lock['source'])
    rt=LoRARuntime(source,str(args.root/f'work_{args.shard}'));b=rt.base
    banks={};digests={}
    for arm in ('single','dual'):
        for seed in (272001,272003):
            name=f'{arm}_{seed}';path=noise/arm/'runs'/str(seed)/'checkpoints/8208.pt'
            assert sha256(path)==lock['checkpoints'][name]
            cp=torch.load(path,map_location='cpu',weights_only=False)
            bank=RecycleLoRA(rt.model.pairformer_stack,**cp['config']).cuda().eval()
            bank.load_state_dict(cp['state_dict']);bank.requires_grad_(False)
            banks[name]=bank;digests[name]=state_hash(tuple(bank.parameters()))
    rows=[];replays=0;target_replays=0;prefix_hash={pi:state_hash(v[0]) for pi,v in rt.prefixes.items()}
    with torch.no_grad():
        for index,site in enumerate(b.plan['sites']):
            if index%6!=args.shard:continue
            pi,pos=site['parent_index'],site['position_zero_based'];wt3,_=rt.prefixes[pi];wt4=b.references[pi][1:]
            before={f:ResponseMoments() for f in ('s','z')}
            outputs={name:{f:ResponseMoments() for f in ('s','z')} for name in ('disabled',*banks)}
            increments={name:{f:ResponseMoments() for f in ('s','z')} for name in banks}
            for aa in site['candidates']:
                item=b.item(pi,pos,aa);label=item['label']
                path=b.store.path(pi,label,'conditioning.pt')
                archived=torch.load(path,map_location='cpu',weights_only=False)['conditioning']
                inputs=rt.candidate_input(item)
                assert torch.equal(inputs.cpu(),archived[0])
                init=initialize_cached_recycle(rt.model,item['features'],inputs)
                target3,rng=capture_cached_prefix(rt.model,item['features'],init)
                target4=native_recycle_step(rt.model,item['features'],init,target3,rng=rng)
                assert all(torch.equal(t.cpu(),a) for t,a in zip(target4,archived[1:])),(label,'target3+1 replay')
                for ni in (0,1):assert torch.equal(b.decode(item,(inputs,*target4),ni),item['teacher'][ni])
                target_replays+=1
                for f,t,w in zip(('s','z'),target3,wt3):before[f].add(torch.zeros_like(t),t-w)
                _,c=rt.conditioning(None,site,aa);disabled=c[1:]
                expected=np.load(Path(rt.lock['native_root'])/rt.preflight['baseline'][label]['path'])['coordinates']
                for ni in (0,1):assert np.array_equal(b.decode(item,c,ni).cpu().numpy(),expected[ni])
                replays+=1
                for f,p,t,w in zip(('s','z'),disabled,target4,wt4):outputs['disabled'][f].add(p-w,t-w)
                for name,bank in banks.items():
                    _,c=rt.conditioning(bank,site,aa)
                    arm,seed=name.split('_')
                    expected=np.load(noise/arm/'runs'/seed/'coordinates'/f'8208_adapted_{label}.npz')['coordinates']
                    for ni in (0,1):assert np.array_equal(b.decode(item,c,ni).cpu().numpy(),expected[ni]),(name,label,ni)
                    replays+=1
                    for f,p,t,w,d in zip(('s','z'),c[1:],target4,wt4,disabled):
                        outputs[name][f].add(p-w,t-w)
                        increments[name][f].add(p-d,t-d)
                del archived,target3,target4,disabled,inputs,init,c,item
            row=dict(site=site['site_key'],pdb=site['pdb_id'],parent=pi,role=site['role_n15'],
                before={f:m.result() for f,m in before.items()},
                after={a:{f:m.result() for f,m in fs.items()} for a,fs in outputs.items()},
                increment={a:{f:m.result() for f,m in fs.items()} for a,fs in increments.items()})
            rows.append(row)
            write_json(args.root/f'shard_{args.shard}.json',dict(complete=False,rows=rows,seconds=time.monotonic()-begin))
            print('RESPONSE_SITE',args.shard,site['site_key'],time.monotonic()-begin,flush=True)
            del before,outputs,increments
    assert len(rows)==8 and target_replays==152 and replays==760
    assert all(state_hash(v[0])==prefix_hash[pi] for pi,v in rt.prefixes.items())
    assert all(state_hash(tuple(bank.parameters()))==digests[name] for name,bank in banks.items())
    rt.finish()
    write_json(args.root/f'shard_{args.shard}.json',dict(complete=True,rows=rows,seconds=time.monotonic()-begin,
        target_replays=target_replays,candidate_replays=replays,counts=b.counts,runtime=b.runtime,
        audit_lock_sha256=sha256(args.root/'audit_lock.json'),peak_allocated_bytes=torch.cuda.max_memory_allocated()))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--shard',type=int,choices=range(6),required=True)
    run_recycle_response_audit(p.parse_args())
