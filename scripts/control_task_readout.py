"""One bounded matched two-arm, two-seed coverage batch, with all checkpoints decoded independently of NMSE."""
import argparse
import json
import os
import signal
import subprocess
import time
from pathlib import Path


def control_task_readout(root):
    virtual = Path('/data/user/shuang886/Folding')/root.name
    start = time.monotonic()
    stages = []
    env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
               LAYERNORM_TYPE='torch', PROTENIX_ROOT_DIR='/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime',
               PYTHONPATH=f'{virtual}/code/src:{virtual}/code/scripts')
    for key in ('CUDA_VISIBLE_DEVICES', 'ROCR_VISIBLE_DEVICES', 'GPU_DEVICE_ORDINAL', 'HSA_VISIBLE_DEVICES'):
        env.pop(key, None)
    def save(name, value):
        p = root/name
        p.parent.mkdir(parents=True, exist_ok=True)
        temp = p.with_suffix(p.suffix+'.part')
        temp.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')
        temp.replace(p)
    def pool(mode, tasks, cpu=False):
        active = []
        stage = dict(mode=mode, complete=False, jobs=[])
        stages.append(stage)
        (root/'logs').mkdir(exist_ok=True)
        try:
            for index, args in enumerate(tasks):
                assert index < 4
                cmd = ['/media/IntelSSD/onestepfold/diamondhill_migration_20261001/tools/proot/usr/bin/proot',
                       '-b', str(root.parent)+':/data/user/shuang886/Folding',
                       '/home/pc/anaconda3/envs/fold/bin/python', '-u',
                       str(virtual/'code/scripts/run_task_readout.py'), '--root', str(virtual), '--mode', mode, *args]
                with (root/'logs'/f'{mode}_{len(stages)}_{index}.log').open('w') as log:
                    p = subprocess.Popen(cmd, env=dict(env, HIP_VISIBLE_DEVICES='' if cpu else str(index)),
                                         stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                active.append((p, index, time.monotonic()))
            while active:
                for p, index, begin in list(active):
                    if time.monotonic()-begin > 7200:
                        raise TimeoutError(f'{mode} worker{index} exceeded2h')
                    if p.poll() is not None:
                        stage['jobs'].append(dict(index=index, exit=p.returncode, seconds=time.monotonic()-begin))
                        active.remove((p, index, begin))
                        if p.returncode:
                            raise RuntimeError(f'{mode} worker{index} exit{p.returncode}')
                save('status.json', dict(complete=False, phase=mode,
                                         active=[dict(pid=p.pid, index=i, seconds=time.monotonic()-t) for p, i, t in active],
                                         stages=stages, seconds=time.monotonic()-start))
                if active:
                    time.sleep(5)
            stage['complete'] = True
        except BaseException:
            for p, index, begin in active:
                if p.poll() is None:
                    os.killpg(p.pid, signal.SIGTERM)
            raise
    try:
        assert not (root/'lock.json').exists()
        pool('prepare', [[]], cpu=True)
        pool('train', [['--job', f'{arm}_context_s{seed}'] for arm in ('restricted','expanded') for seed in (231301,231303)])
        pool('train', [['--job', f'{arm}_aa_only_s{seed}'] for arm in ('restricted','expanded') for seed in (231301,231303)], cpu=True)
        pool('eval', [['--index', str(i)] for i in range(4)])
        pool('collect', [[]], cpu=True)
        save('execution.json', dict(complete=True, stages=stages, seconds=time.monotonic()-start))
        save('status.json', dict(complete=True, phase='closed', active=[], seconds=time.monotonic()-start))
    except BaseException as e:
        save('execution.json', dict(complete=False, error=repr(e), stages=stages, seconds=time.monotonic()-start))
        raise


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    control_task_readout(p.parse_args().root)
