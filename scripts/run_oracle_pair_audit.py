"""Oracle target-z with actual candidate's unadapted final single; no learning."""
import argparse,json,time
from pathlib import Path
import numpy as np
import torch
from fastglycan.pair_split import pair_split_conditioning
from fastglycan.paired_teacher_protocol import sha256,write_json
from run_recycle_lora import LoRARuntime
from run_reference_editor import state_hash


def run_oracle_pair_audit(args):
    start=time.monotonic();lock=json.loads((args.root/'audit_lock.json').read_text())
    for path,digest in lock['code'].items(): assert sha256(args.root/'code'/path)==digest,path
    assert sha256(args.root/'protocol.md')==lock['protocol_sha256']
    rt=LoRARuntime(Path(lock['source']),str(args.root/f'work_{args.shard}'));b=rt.base
    guards={pi:state_hash(v[0]) for pi,v in rt.prefixes.items()}
    out=args.root/'coordinates';out.mkdir(exist_ok=True);records=[];sites=[];target_hashes={}
    with torch.no_grad():
        for index,site in enumerate(b.plan['sites']):
            if index%6!=args.shard:continue
            for aa in site['candidates']:
                item,base=rt.conditioning(None,site,aa);label=item['label']
                path=b.store.path(site['parent_index'],label,'conditioning.pt')
                target_hashes[label]=sha256(path)
                target=tuple(t.cuda() for t in torch.load(path,map_location='cpu',weights_only=False)['conditioning'])
                assert torch.equal(base[0],target[0]),(label,'candidate input mismatch')
                mixed=pair_split_conditioning(base,target,None,'pair')
                assert mixed[0] is base[0] and mixed[1] is base[1] and mixed[2] is target[2]
                rec=rt.preflight['baseline'][label];bp=Path(rt.lock['native_root'])/rec['path']
                assert sha256(bp)==rec['sha256'];expected=np.load(bp)['coordinates']
                for name,c in (('exact',target),('disabled',base),('oracle_pair',mixed)):
                    xyz=np.stack([b.decode(item,c,ni).cpu().numpy() for ni in (0,1)])
                    assert np.isfinite(xyz).all()
                    if name=='exact':assert np.array_equal(xyz,item['teacher'].cpu().numpy()),(label,'exact')
                    if name=='disabled':assert np.array_equal(xyz,expected),(label,'disabled')
                    p=out/f'{name}_{label}.npz';np.savez_compressed(p,coordinates=xyz)
                    records.append(dict(path=str(p.relative_to(args.root)),sha256=sha256(p),label=label,arm=name))
                del target,base,mixed,c,item
            sites.append(site['site_key'])
            write_json(args.root/f'shard_{args.shard}.json',dict(complete=False,sites=sites,seconds=time.monotonic()-start))
            print('ORACLE_SITE',args.shard,site['site_key'],time.monotonic()-start,flush=True)
    assert len(sites)==8 and len(records)==456 and len(target_hashes)==152
    assert b.counts['recycle']==152 and b.counts['s1']==912 and b.counts['updates']==0
    assert guards=={pi:state_hash(v[0]) for pi,v in rt.prefixes.items()}
    rt.finish()
    write_json(args.root/f'shard_{args.shard}.json',dict(complete=True,sites=sites,rows=records,counts=b.counts,runtime=b.runtime,
        target_conditioning_sha256=target_hashes,seconds=time.monotonic()-start,
        audit_lock_sha256=sha256(args.root/'audit_lock.json'),peak_allocated_bytes=torch.cuda.max_memory_allocated()))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--shard',type=int,choices=range(6),required=True)
    run_oracle_pair_audit(p.parse_args())
