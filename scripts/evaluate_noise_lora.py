"""Immutable checkpoint evaluation, with original candidate/noise protocol."""
import argparse
import json
from pathlib import Path
import time
import numpy as np
import torch

from fastglycan.noise_lora import read_noise_lock
from fastglycan.models.recycle_lora import RecycleLoRA
from fastglycan.paired_teacher_protocol import sha256, write_json
from run_recycle_lora import LoRARuntime


def evaluate_noise_lora(args):
    begin = time.monotonic()
    lock = read_noise_lock(args.root)
    folder = args.root/args.arm/'runs'/str(args.seed)
    path = folder/'checkpoints'/f'{args.step}.pt'
    digest = sha256(path)
    cp = torch.load(path, map_location='cpu', weights_only=False)
    assert cp['seed'] == args.seed and cp['step'] == args.step and cp['arm'] == args.arm
    assert cp['noise_lock_sha256'] == sha256(args.root/'noise_lock.json')
    rt = LoRARuntime(Path(lock['source']), str(folder/f'eval_{args.step}_{args.shard}_{time.time_ns()}'))
    bank = RecycleLoRA(rt.model.pairformer_stack, **cp['config']).cuda().eval()
    bank.load_state_dict(cp['state_dict'])
    coords = folder/'coordinates'
    coords.mkdir(exist_ok=True)
    records = []
    index = 0
    with torch.no_grad():
        for site in rt.base.plan['sites']:
            for aa in site['candidates']:
                mine = index % 2 == args.shard
                index += 1
                if not mine:
                    continue
                item, cond = rt.conditioning(bank, site, aa)
                xyz = np.stack([rt.base.decode(item, cond, ni).cpu().numpy() for ni in (0,1)])
                assert np.isfinite(xyz).all()
                output = coords/f'{args.step}_adapted_{item["label"]}.npz'
                np.savez_compressed(output, coordinates=xyz)
                records.append(dict(path=str(output.relative_to(folder)), sha256=sha256(output),
                                    label=item['label'], arm='adapted'))
    assert len(records) == 456 and sha256(path) == digest
    rt.finish()
    write_json(folder/f'shard_{args.step}_{args.shard}.json', dict(complete=True, predictions=records,
        seconds=time.monotonic()-begin, counts=rt.base.counts, runtime=rt.base.runtime,
        checkpoint_sha256=digest, step=args.step, noise_lock_sha256=sha256(args.root/'noise_lock.json')))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--arm', choices=['single','dual'], required=True)
    p.add_argument('--seed', type=int, required=True)
    p.add_argument('--step', type=int, choices=[4104,8208], required=True)
    p.add_argument('--shard', type=int, choices=[0,1], required=True)
    evaluate_noise_lora(p.parse_args())
