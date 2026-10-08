"""Independent candidate shards on spare GPUs; checkpoint immutable per evaluation."""
import argparse
import json
from pathlib import Path
import time
import numpy as np
import torch

from run_recycle_lora import LoRARuntime
from fastglycan.models.recycle_lora import RecycleLoRA
from fastglycan.paired_teacher_protocol import sha256,write_json


def evaluate_shard(args):
    begin=time.monotonic();rt=LoRARuntime(args.source,str(args.output/f'work_{args.seed}_{args.shard}'))
    cp=torch.load(args.checkpoint,map_location='cpu',weights_only=False)
    assert cp['seed']==args.seed and cp['step']==8208
    assert cp['lock_sha256']==sha256(args.source/'lora_lock.json')
    bank=RecycleLoRA(rt.model.pairformer_stack,**cp['config']).cuda().eval();bank.load_state_dict(cp['state_dict'])
    folder=args.output/'runs'/str(args.seed);coords=folder/'coordinates';coords.mkdir(parents=True,exist_ok=True)
    records=[];index=0
    with torch.no_grad():
        for site in rt.base.plan['sites']:
            for aa in site['candidates']:
                mine=index%2==args.shard;index+=1
                if not mine:continue
                item,c=rt.conditioning(bank,site,aa)
                xyz=np.stack([rt.base.decode(item,c,ni).cpu().numpy() for ni in range(2)])
                assert np.isfinite(xyz).all()
                path=coords/f'8208_adapted_{item["label"]}.npz';np.savez_compressed(path,coordinates=xyz)
                records.append(dict(path=str(path.relative_to(folder)),sha256=sha256(path),label=item['label'],arm='adapted'))
    assert len(records)==456;rt.finish()
    write_json(folder/f'shard_{args.shard}.json',dict(complete=True,predictions=records,seconds=time.monotonic()-begin,
               counts=rt.base.counts,runtime=rt.base.runtime,checkpoint_sha256=sha256(args.checkpoint)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--seed',type=int,required=True);p.add_argument('--shard',type=int,choices=[0,1],required=True)
    evaluate_shard(p.parse_args())
