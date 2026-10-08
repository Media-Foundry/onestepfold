"""Fresh matched DDP runs: only training noise coverage differs."""
import argparse
import copy
import json
from pathlib import Path
import time
from datetime import timedelta

from fastglycan.paired_distributed import configure_torchrun_worker


def run_noise_lora(args):
    rank, world, address = configure_torchrun_worker(args.devices)
    import numpy as np
    import torch
    import torch.distributed as dist
    from torch.nn.parallel import DistributedDataParallel as DDP
    from fastglycan.noise_lora import NoiseCandidateLoss, noise_index_for_exposure, read_noise_lock
    from fastglycan.models.recycle_lora import RecycleLoRA
    from fastglycan.paired_distributed import atomic_checkpoint, paired_local_index
    from fastglycan.reference_editor_multiref import multiref_update, editor_state_digest
    from fastglycan.paired_teacher_protocol import sha256, write_json
    from run_recycle_lora import LoRARuntime
    from run_reference_editor import coordinate_objective

    paired_local_index(rank, world)
    lock = read_noise_lock(args.root)
    source = Path(lock['source'])
    folder = args.root / args.arm / 'runs' / str(args.seed)
    folder.mkdir(parents=True, exist_ok=True)
    rt = LoRARuntime(source, str(folder / f'work_{args.mode}_{rank}_{time.time_ns()}'))
    b = rt.base
    dist.init_process_group('nccl', init_method=address, rank=rank, world_size=world,
                            timeout=timedelta(minutes=15))
    initial = source / 'runs' / str(args.seed) / 'checkpoints/0.pt'
    cp = torch.load(initial, map_location='cpu', weights_only=False)
    assert cp['step'] == 0 and cp['seed'] == args.seed
    bank = RecycleLoRA(rt.model.pairformer_stack, **cp['config']).cuda()
    bank.load_state_dict(cp['state_dict'])
    wrapper = NoiseCandidateLoss(bank, rt, coordinate_objective)
    ddp = DDP(wrapper, device_ids=[0], broadcast_buffers=False, gradient_as_bucket_view=True)
    opt = torch.optim.AdamW(bank.parameters(), lr=1e-4, weight_decay=1e-4, eps=1e-8)
    opt.load_state_dict(cp['optimizer'])
    keys = sorted([s['site_key'] for s in b.plan['sites'] if s['role_n15'] == 'train'],
                  key=lambda k: (b.sites[k]['parent_index'], b.sites[k]['position_zero_based']))
    assert len(keys) == 27 and b.noises == lock['noises']
    schedule = dict(updates=8208, train_site_keys=keys)
    initial_hash = editor_state_digest(bank)
    begin = time.monotonic()
    if args.mode == 'preflight':
        # Independent rank copies must reproduce both archived noises at zero
        # adaptation, before any discarded gradient checks.
        site = b.sites['p3_s37']
        aa = site['candidates'][0]
        with torch.no_grad():
            item, cond = rt.conditioning(bank, site, aa)
            expected = np.load(source / 'runs' / str(args.seed) / 'coordinates' /
                               f'0_adapted_{item["label"]}.npz')['coordinates']
            for ni in (0, 1):
                assert np.array_equal(b.decode(item, cond, ni).cpu().numpy(), expected[ni])
        serial = RecycleLoRA(rt.model.pairformer_stack, **cp['config']).cuda() if rank == 0 else None
        serial_opt = torch.optim.AdamW(serial.parameters(), lr=1e-4, weight_decay=1e-4, eps=1e-8) if rank == 0 else None
        checks = []
        for step in (0, 9*27, 10*27, 19*27):
            site, choices = multiref_update(schedule, b.sites, step)
            ni = [noise_index_for_exposure('dual', step, r) for r in (0, 1)]
            if rank == 0:
                serial.load_state_dict(bank.state_dict())
                serial_opt.load_state_dict(copy.deepcopy(opt.state_dict()))
                serial_opt.zero_grad(set_to_none=True)
                for j, choice in enumerate(choices):
                    item, cond = rt.conditioning(serial, site, choice)
                    loss = coordinate_objective(b.decode(item, cond, ni[j]), item['teacher'][ni[j]], item['ca'], item['labels'])[0]
                    (loss / 2).backward()
                expected_grad = [p.grad.detach().clone() for p in serial.parameters()]
                torch.nn.utils.clip_grad_norm_(serial.parameters(), 1., error_if_nonfinite=True)
                serial_opt.step()
            dist.barrier()
            opt.zero_grad(set_to_none=True)
            ddp(site, choices[rank], ni[rank]).backward()
            if rank == 0:
                for p, g in zip(bank.parameters(), expected_grad):
                    torch.testing.assert_close(p.grad, g, rtol=1e-5, atol=1e-7)
                grad_error = max(float((p.grad-g).abs().max()) for p,g in zip(bank.parameters(), expected_grad))
            torch.nn.utils.clip_grad_norm_(bank.parameters(), 1., error_if_nonfinite=True)
            opt.step()
            if rank == 0:
                for p, q in zip(bank.parameters(), serial.parameters()):
                    torch.testing.assert_close(p, q, rtol=1e-5, atol=1e-7)
                checks.append(dict(step_index=step, noise_indices=ni, gradient_max_abs=grad_error,
                    parameter_max_abs=max(float((p-q).abs().max()) for p,q in zip(bank.parameters(), serial.parameters()))))
            dist.barrier()
        rt.finish()
        if rank == 0:
            write_json(args.root / f'preflight_{args.seed}.json', dict(complete=True, initial_hash=initial_hash,
                source_checkpoint_sha256=sha256(initial), zero_replay_both_noises=True,
                checks=checks, discarded_updates=4, rtol=1e-5, atol=1e-7, runtime=b.runtime,
                seconds=time.monotonic()-begin, noise_lock_sha256=sha256(args.root/'noise_lock.json')))
    else:
        for seed in lock['seeds']:
            assert json.loads((args.root/f'preflight_{seed}.json').read_text())['complete']
        history = folder / 'history.jsonl'
        if rank == 0:
            if history.exists():
                raise RuntimeError('fresh runs only; explicit recovery required for existing history')
            history.touch()
        dist.barrier()
        for step in range(8208):
            site, choices = multiref_update(schedule, b.sites, step)
            ni = [noise_index_for_exposure(args.arm, step, r) for r in (0, 1)]
            opt.zero_grad(set_to_none=True)
            loss = ddp(site, choices[rank], ni[rank])
            assert torch.isfinite(loss)
            loss.backward()
            norm = torch.nn.utils.clip_grad_norm_(bank.parameters(), 1., error_if_nonfinite=True)
            opt.step()
            components = [None, None]
            dist.all_gather_object(components, wrapper.last_components)
            if rank == 0:
                row = dict(step=step+1, site=site['site_key'], aa=choices, noise_indices=ni,
                           components=components, gradient_norm=float(norm), clipped=bool(norm>1))
                with history.open('a') as f:
                    f.write(json.dumps(row, allow_nan=False)+'\n')
                if (step+1)%128 == 0 or step+1 in (4104, 8208):
                    payload = dict(state_dict=bank.state_dict(), optimizer=opt.state_dict(), step=step+1,
                        seed=args.seed, arm=args.arm, config=bank.config, lock_sha256=cp['lock_sha256'],
                        noise_lock_sha256=sha256(args.root/'noise_lock.json'), initial_hash=initial_hash,
                        execution='paired_DDP_from_zero', world_size=2)
                    atomic_checkpoint(folder/'latest.pt', payload)
                    write_json(folder/'progress.json', dict(step=step+1, seconds=time.monotonic()-begin,
                                                           complete=step+1==8208))
                    print('NOISE_TRAIN', args.arm, args.seed, step+1, time.monotonic()-begin, flush=True)
                    if step+1 in (4104, 8208):
                        atomic_checkpoint(folder/'checkpoints'/f'{step+1}.pt', payload)
            dist.barrier()
        rt.finish()
        hashes = [None, None]
        dist.all_gather_object(hashes, editor_state_digest(bank))
        assert len(set(hashes)) == 1
        counts = [None, None]
        dist.all_gather_object(counts, b.counts)
        if rank == 0:
            write_json(folder/'training_complete.json', dict(complete=True, step=8208, arm=args.arm,
                seed=args.seed, initial_hash=initial_hash, replica_hashes=hashes, rank_counts=counts,
                history_sha256=sha256(history), seconds=time.monotonic()-begin, runtime=b.runtime,
                noise_lock_sha256=sha256(args.root/'noise_lock.json')))
    dist.barrier()
    dist.destroy_process_group()


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--arm', choices=['single', 'dual'], required=True)
    p.add_argument('--seed', type=int, choices=[272001,272003], required=True)
    p.add_argument('--devices', type=int, nargs=2, required=True)
    p.add_argument('--mode', choices=['preflight','train'], required=True)
    run_noise_lora(p.parse_args())
