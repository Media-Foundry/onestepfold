"""Prepare real candidate suffix boundaries and TRAIN-only teacher stage labels."""
import argparse
import json
from pathlib import Path
import time
import numpy as np
import torch
from fastglycan.models.stage_pair_recovery import StagePairRecovery
from fastglycan.models.compensated_recycle import initialize_cached_recycle, capture_cached_prefix, native_recycle_step
from fastglycan.models.prefix_recycle import capture_rng_state, restore_rng_state
from fastglycan.pair_recovery_data import PairRecoveryData
from fastglycan.stage_pair_data import PairStageCapture
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.reference_editor_multiref import editor_state_digest
from run_recycle_lora import LoRARuntime
from run_reference_editor import state_hash


def build_stage_cache(root, shard):
    begin=time.monotonic();lock=json.loads((root/'build_lock.json').read_text())
    for name,digest in lock['code'].items():assert sha256(root/'code'/name)==digest,name
    assert sha256(root/'protocol.md')==lock['protocol_sha256']
    rt=LoRARuntime(Path(lock['source']),str(root/f'cache_work_{shard}'));b=rt.base
    data=PairRecoveryData(lock['build_root'],lock['cache_manifest_sha256'])
    nets={seed:StagePairRecovery(list(rt.model.pairformer_stack.blocks[-2:]),seed).cuda().eval() for seed in lock['seeds']}
    initial={str(seed):editor_state_digest(net) for seed,net in nets.items()}
    reference_guard={pi:state_hash(v[0]) for pi,v in rt.prefixes.items()}
    rows=[];teacher_calls=0;identities=0
    (root/'cache').mkdir(exist_ok=True)
    with torch.no_grad():
        for index,site in enumerate(b.plan['sites']):
            if index%4!=shard:continue
            pi,pos=site['parent_index'],site['position_zero_based']
            for aa in site['candidates']:
                item=b.item(pi,pos,aa);label=item['label'];base=data.base(label)
                with PairStageCapture(rt.model.pairformer_stack) as capture:
                    _,actual=rt.conditioning(None,site,aa)
                assert all(torch.equal(x,y) for x,y in zip(actual,base)),(label,'base replay')
                boundary,warm_hint=capture.values[13],capture.values[14]
                for seed,net in nets.items():
                    c,stages=net(base,boundary,rt.prefixes[pi][0][1],pos,b.aa.index(site['original_aa']),b.aa.index(aa))
                    assert torch.equal(stages[0],warm_hint) and torch.equal(c[2],base[2]),(label,seed,'native suffix identity')
                    assert c[0] is base[0] and c[1] is base[1]
                    identities+=1
                rec=rt.preflight['baseline'][label];p=Path(rt.lock['native_root'])/rec['path'];assert sha256(p)==rec['sha256']
                expected=np.load(p)['coordinates']
                for ni in (0,1):assert np.array_equal(b.decode(item,c,ni).cpu().numpy(),expected[ni])
                target_hint=None
                if site['role_n15']=='train':
                    ambient=capture_rng_state()
                    try:
                        init=initialize_cached_recycle(rt.model,item['features'],rt.candidate_input(item))
                        target3,rng=capture_cached_prefix(rt.model,item['features'],init)
                        with PairStageCapture(rt.model.pairformer_stack,indices=(14,)) as target_capture:
                            target4=native_recycle_step(rt.model,item['features'],init,target3,rng=rng)
                        tp=b.store.path(pi,label,'conditioning.pt')
                        archived=torch.load(tp,map_location='cpu',weights_only=False)['conditioning']
                        assert all(torch.equal(t.cpu(),a) for t,a in zip(target4,archived[1:])),(label,'target replay')
                        target_hint=target_capture.values[14].cpu();teacher_calls+=1
                    finally:restore_rng_state(ambient)
                path=root/'cache'/f'{label}.pt'
                torch.save(dict(boundary=boundary.cpu(),warm_hint=warm_hint.cpu(),target_hint=target_hint),path)
                rows.append(dict(label=label,site=site['site_key'],role=site['role_n15'],
                                 path=str(path.relative_to(root)),sha256=sha256(path),bytes=path.stat().st_size))
            print('STAGE_CACHE_SITE',shard,site['site_key'],time.monotonic()-begin,flush=True)
            write_json(root/f'cache_{shard}.json',dict(complete=False,candidates=len(rows),teacher_candidates=teacher_calls,seconds=time.monotonic()-begin))
    assert len(rows)==228 and identities==456
    assert b.counts==dict(c4=0,input_embedder=0,updates=0,recycle=228+4*teacher_calls,s1=456)
    assert reference_guard=={pi:state_hash(v[0]) for pi,v in rt.prefixes.items()}
    rt.finish()
    assert initial=={str(seed):editor_state_digest(net) for seed,net in nets.items()}
    write_json(root/f'cache_{shard}.json',dict(complete=True,records=rows,initial_hashes=initial,
        parameters=sum(p.numel() for p in next(iter(nets.values())).parameters()),counts=b.counts,
        teacher_candidates=teacher_calls,identities=identities,seconds=time.monotonic()-begin,
        peak_allocated_bytes=torch.cuda.max_memory_allocated(),runtime=b.runtime))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--shard',type=int,choices=range(4),required=True)
    a=p.parse_args();build_stage_cache(a.root,a.shard)
