"""Build immutable unadapted B cache and TRAIN-only residual scale statistics."""
import argparse,json,time
from pathlib import Path
import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.response_moments import ResponseMoments
from run_recycle_lora import LoRARuntime


def prepare_pair_recovery(args):
    start=time.monotonic();lock=json.loads((args.root/'build_lock.json').read_text())
    for p,h in lock['code'].items():assert sha256(args.root/'code'/p)==h,p
    rt=LoRARuntime(Path(lock['source']),str(args.root/f'prepare_work_{args.shard}'));b=rt.base
    cache=args.root/'cache';cache.mkdir(exist_ok=True);rows=[];stats=[]
    with torch.no_grad():
        for i,site in enumerate(b.plan['sites']):
            if i%6!=args.shard:continue
            moments=ResponseMoments()
            for aa in site['candidates']:
                item,base=rt.conditioning(None,site,aa);label=item['label']
                rec=rt.preflight['baseline'][label];path=Path(rt.lock['native_root'])/rec['path'];assert sha256(path)==rec['sha256']
                xyz=np.stack([b.decode(item,base,n).cpu().numpy() for n in (0,1)])
                assert np.array_equal(xyz,np.load(path)['coordinates'])
                tp=b.store.path(site['parent_index'],label,'conditioning.pt')
                target=torch.load(tp,map_location='cpu',weights_only=False)['conditioning']
                assert torch.equal(target[0],base[0].cpu())
                e=target[2].cuda()-base[2];moments.add(torch.zeros_like(e),e)
                p=cache/f'{label}.pt';torch.save(dict(base=tuple(t.cpu() for t in base)),p)
                rows.append(dict(label=label,path=str(p.relative_to(args.root)),sha256=sha256(p),
                    target_path=str(tp),target_sha256=sha256(tp),bytes=p.stat().st_size))
            m=moments.result();stats.append(dict(site=site['site_key'],parent=site['parent_index'],role=site['role_n15'],
                length=len(base[1]),mean_squared_residual=m['raw']['target_energy']/base[2].numel(),moments=m))
            write_json(args.root/f'cache_shard_{args.shard}.json',dict(complete=False,sites=len(stats),seconds=time.monotonic()-start))
            print('CACHE_SITE',args.shard,site['site_key'],flush=True)
    rt.finish();assert len(rows)==152 and len(stats)==8 and b.counts['recycle']==152 and b.counts['s1']==304
    write_json(args.root/f'cache_shard_{args.shard}.json',dict(complete=True,records=rows,stats=stats,counts=b.counts,runtime=b.runtime,
        seconds=time.monotonic()-start,build_lock_sha256=sha256(args.root/'build_lock.json')))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--shard',type=int,required=True)
    prepare_pair_recovery(p.parse_args())
