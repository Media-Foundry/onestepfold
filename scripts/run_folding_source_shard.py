#!/usr/bin/env python3
"""Execute the frozen source partition with a scheduler-compatible CPU budget."""
import argparse
import concurrent.futures
import json
import multiprocessing
import os
from pathlib import Path
import time
import torch
from fastglycan.paired_teacher_protocol import sha256, write_json
from migrate_expanded_sources_hpc3 import hpc3_source_worker_init
from prepare_diffusion_training_sources import qualify_adapter_source


def run_folding_source_shard(root, index):
    torch.set_num_threads(1)
    assert not torch.cuda.is_available() and index in (0, 1)
    assert int(os.environ['SLURM_CPUS_PER_TASK']) == 12
    assert not (root / f'shard_{index}.json').exists()
    lock = json.loads((root / 'migration_lock.json').read_text())
    for name, digest in lock['hashes'].items():
        assert sha256(root / name) == digest, name
    execution = json.loads((root / 'folding_resume_lock.json').read_text())
    assert execution['workers_per_shard'] == 12 and execution['shards'] == 2
    assert execution['migration_sha256'] == sha256(root / 'migration_lock.json')
    assert execution['script_sha256'] == sha256(Path(__file__))
    assert sha256(root / 'origin/failed/candidate_order.json') == lock['order_sha256']
    rows = json.loads((root / 'origin/failed/candidate_order.json').read_text())[index::2]
    begin = time.monotonic()
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=12, mp_context=multiprocessing.get_context('spawn'),
        initializer=hpc3_source_worker_init, initargs=(str(root),),
    ) as pool:
        outcomes = list(pool.map(qualify_adapter_source, [(r, root.parent, root) for r in rows]))
    assert [r['group_id'] for r in outcomes] == [r['group_id'] for r in rows]
    write_json(root / f'shard_{index}.json', dict(
        complete=True, index=index, outcomes=outcomes, seconds=time.monotonic()-begin,
        lock_sha256=sha256(root / 'migration_lock.json'),
        execution_lock_sha256=sha256(root / 'folding_resume_lock.json'),
        workers=12, gpu_compute=False,
    ))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--index', type=int, required=True)
    args = parser.parse_args()
    run_folding_source_shard(args.root.resolve(), args.index)
