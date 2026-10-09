"""Frozen terminal-state interventions with exact endpoint replay gates."""
import argparse,json,time
from pathlib import Path
import numpy as np
import torch
from fastglycan.pair_split import pair_split_conditioning
from fastglycan.models.recycle_lora import RecycleLoRA
from fastglycan.paired_teacher_protocol import sha256,write_json
from run_recycle_lora import LoRARuntime
from run_reference_editor import state_hash


def run_pair_split_audit(args):
    begin=time.monotonic();lock=json.loads((args.root/'audit_lock.json').read_text())
    for name,digest in lock['code'].items(): assert sha256(args.root/'code'/name)==digest,name
    assert sha256(args.root/'protocol.md')==lock['protocol_sha256']
    noise=Path(lock['noise_root']);rt=LoRARuntime(Path(lock['source']),str(args.root/f'work_{args.shard}'));b=rt.base
    banks={};digests={};endpoint_files={}
    for arm in ('single','dual'):
        for seed in (272001,272003):
            name=f'{arm}_{seed}';folder=noise/arm/'runs'/str(seed);cp_path=folder/'checkpoints/8208.pt'
            assert sha256(cp_path)==lock['checkpoints'][name]
            assert sha256(folder/'evaluation_8208.json')==lock['evaluations'][name]
            endpoint_files[name]={r['label']:r for r in json.loads((folder/'evaluation_8208.json').read_text())['predictions']}
            cp=torch.load(cp_path,map_location='cpu',weights_only=False)
            bank=RecycleLoRA(rt.model.pairformer_stack,**cp['config']).cuda().eval()
            bank.load_state_dict(cp['state_dict']);bank.requires_grad_(False)
            banks[name]=bank;digests[name]=state_hash(tuple(bank.parameters()))
    out=args.root/'coordinates';out.mkdir(exist_ok=True)
    guards={pi:state_hash(v[0]) for pi,v in rt.prefixes.items()}
    records=[];sites=[];replay=0;transfer=0;mean_seconds=0.
    with torch.no_grad():
        for index,site in enumerate(b.plan['sites']):
            if index%6!=args.shard: continue
            base_cpu={};base_signatures={}
            for aa in site['candidates']:
                item,c=rt.conditioning(None,site,aa);label=item['label']
                rec=rt.preflight['baseline'][label];path=Path(rt.lock['native_root'])/rec['path']
                assert sha256(path)==rec['sha256']
                xyz=np.stack([b.decode(item,c,ni).cpu().numpy() for ni in (0,1)])
                assert np.array_equal(xyz,np.load(path)['coordinates']),(label,'disabled')
                replay+=1;base_cpu[aa]=tuple(t.cpu() for t in c);base_signatures[aa]=state_hash(base_cpu[aa])
                path=out/f'disabled_{label}.npz';np.savez_compressed(path,coordinates=xyz)
                records.append(dict(path=str(path.relative_to(args.root)),sha256=sha256(path),label=label,arm='disabled'))
            for name,bank in banks.items():
                adapted_cpu={};total=None
                for aa in site['candidates']:
                    item,c=rt.conditioning(bank,site,aa);label=item['label']
                    assert torch.equal(c[0].cpu(),base_cpu[aa][0])
                    arm,seed=name.split('_');rec=endpoint_files[name][label];path=noise/arm/'runs'/seed/rec['path']
                    assert sha256(path)==rec['sha256']
                    xyz=np.stack([b.decode(item,c,ni).cpu().numpy() for ni in (0,1)])
                    assert np.array_equal(xyz,np.load(path)['coordinates']),(name,label,'full')
                    replay+=1
                    path=out/f'{name}_full_{label}.npz';np.savez_compressed(path,coordinates=xyz)
                    records.append(dict(path=str(path.relative_to(args.root)),sha256=sha256(path),label=label,arm=name+'_full'))
                    adapted_cpu[aa]=tuple(t.cpu() for t in c)
                    start=time.monotonic();delta=(adapted_cpu[aa][2]-base_cpu[aa][2]).double()
                    if total is None: total=delta
                    else: total.add_(delta)
                    mean_seconds+=time.monotonic()-start
                    if not sites and name=='single_272001' and aa==site['candidates'][0]:
                        # Direct pair-only decode before CPU restoration, one fixed case per shard.
                        base=tuple(t.cuda() for t in base_cpu[aa]);direct=b.decode(item,(base[0],base[1],c[2]),0).cpu()
                start=time.monotonic();mean=(total/19).float();mean_seconds+=time.monotonic()-start
                for aa in site['candidates']:
                    item=b.item(site['parent_index'],site['position_zero_based'],aa);label=item['label']
                    base=tuple(t.cuda() for t in base_cpu[aa]);adapted=tuple(t.cuda() for t in adapted_cpu[aa]);mg=mean.cuda()
                    for mode in ('pair','common','aa'):
                        mixed=pair_split_conditioning(base,adapted,mg,mode)
                        xyz=np.stack([b.decode(item,mixed,ni).cpu().numpy() for ni in (0,1)])
                        assert np.isfinite(xyz).all()
                        if not sites and name=='single_272001' and aa==site['candidates'][0] and mode=='pair':
                            assert np.array_equal(xyz[0],direct.numpy());transfer+=1
                        path=out/f'{name}_{mode}_{label}.npz';np.savez_compressed(path,coordinates=xyz)
                        records.append(dict(path=str(path.relative_to(args.root)),sha256=sha256(path),label=label,arm=name+'_'+mode))
                    del base,adapted,mg,mixed
                assert all(state_hash(base_cpu[a])==base_signatures[a] for a in site['candidates'])
                del adapted_cpu,total,mean,c
            sites.append(site['site_key'])
            write_json(args.root/f'shard_{args.shard}.json',dict(complete=False,sites=sites,seconds=time.monotonic()-begin))
            print('SPLIT_SITE',args.shard,site['site_key'],time.monotonic()-begin,flush=True)
            del base_cpu
    assert len(sites)==8 and replay==760 and transfer==1 and len(records)==2584
    assert b.counts['recycle']==760 and b.counts['s1']==5169 and b.counts['updates']==0
    assert guards=={pi:state_hash(v[0]) for pi,v in rt.prefixes.items()}
    assert all(digests[n]==state_hash(tuple(bank.parameters())) for n,bank in banks.items())
    rt.finish()
    write_json(args.root/f'shard_{args.shard}.json',dict(complete=True,sites=sites,rows=records,seconds=time.monotonic()-begin,
        mean_cpu_seconds=mean_seconds,endpoint_replays=replay,transfer_audits=transfer,counts=b.counts,runtime=b.runtime,
        audit_lock_sha256=sha256(args.root/'audit_lock.json'),peak_allocated_bytes=torch.cuda.max_memory_allocated()))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--shard',type=int,choices=range(6),required=True)
    run_pair_split_audit(p.parse_args())
