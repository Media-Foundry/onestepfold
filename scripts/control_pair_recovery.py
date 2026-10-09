"""Four independent fixed training runs and bounded CPU assessment workers."""
import argparse
import hashlib
import json
import os
import signal
import subprocess
import time
from pathlib import Path


def control_pair_recovery(root):
    virtual = Path('/data/user/shuang886/Folding') / root.name
    lock = json.loads((root / 'training_lock.json').read_text())
    assert json.loads((root / 'preflight.json').read_text())['complete']
    assert hashlib.sha256((root / 'preflight.json').read_bytes()).hexdigest() == lock['preflight_sha256']
    for name, digest in lock['code'].items():
        assert hashlib.sha256((root / 'code' / name).read_bytes()).hexdigest() == digest, name
    prefix = [
        '/media/IntelSSD/onestepfold/diamondhill_migration_20261001/tools/proot/usr/bin/proot',
        '-b', str(root.parent) + ':/data/user/shuang886/Folding',
        '/home/pc/anaconda3/envs/fold/bin/python', '-u',
    ]
    env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
               MKL_NUM_THREADS='1', LAYERNORM_TYPE='torch', FASTGLYCAN_AUTHORIZED_HIP_0_5='1',
               PROTENIX_ROOT_DIR='/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime',
               PYTHONPATH=str(virtual / 'code/src') + ':' + str(virtual / 'code/scripts'))
    assert not any(k in env for k in ('CUDA_VISIBLE_DEVICES', 'ROCR_VISIBLE_DEVICES',
                                     'HSA_VISIBLE_DEVICES', 'GPU_DEVICE_ORDINAL'))
    configurations = [(arm, seed) for seed in lock['seeds'] for arm in lock['arms']]
    assert len(configurations) == 4
    jobs = {}
    state = dict(complete=False, phase='training_and_fixed_evaluation', jobs={})
    start = time.monotonic()
    try:
        for hip, (arm, seed) in enumerate(configurations):
            key = f'train_{arm}_{seed}'
            log = (root / f'{key}.log').open('x')
            cmd = prefix + [str(virtual / 'code/scripts/run_pair_recovery.py'),
                            '--root', str(virtual), '--arm', arm, '--seed', str(seed)]
            child = subprocess.Popen(cmd, env=dict(env, HIP_VISIBLE_DEVICES=str(hip)),
                                     stdin=subprocess.DEVNULL, stdout=log,
                                     stderr=subprocess.STDOUT, start_new_session=True)
            jobs[key] = (child, log)
            state['jobs'][key] = dict(pid=child.pid, hip=hip, status='running', kind='training')
        while True:
            for key, (child, _) in jobs.items():
                code = child.poll()
                if code is not None:
                    state['jobs'][key].update(status='complete' if code == 0 else 'failed', exit_code=code)
                    if code:
                        raise RuntimeError(f'{key} exited with {code}')
            scoring = sum(child.poll() is None and key.startswith('score_')
                          for key, (child, _) in jobs.items())
            for arm, seed in configurations:
                for step in lock['checkpoints']:
                    key = f'score_{arm}_{seed}_{step}'
                    path = root / 'runs' / arm / str(seed) / f'evaluation_{step}.json'
                    if key in jobs or not path.exists() or scoring >= 4:
                        continue
                    try:
                        ready = json.loads(path.read_text())['complete']
                    except (json.JSONDecodeError, KeyError):
                        continue
                    if not ready:
                        continue
                    log = (root / f'{key}.log').open('x')
                    cmd = prefix + [str(virtual / 'code/scripts/score_pair_recovery.py'),
                                    '--root', str(virtual), '--arm', arm,
                                    '--seed', str(seed), '--step', str(step)]
                    child = subprocess.Popen(cmd, env=dict(env, HIP_VISIBLE_DEVICES='4'),
                                             stdin=subprocess.DEVNULL, stdout=log,
                                             stderr=subprocess.STDOUT, start_new_session=True)
                    jobs[key] = (child, log)
                    state['jobs'][key] = dict(pid=child.pid, status='running', kind='cpu_scoring')
                    scoring += 1
            state['seconds'] = time.monotonic() - start
            if len(jobs) == 12 and all(child.poll() is not None for child, _ in jobs.values()):
                break
            if state['seconds'] > 6 * 3600:
                raise TimeoutError('six-hour fixed execution limit; no automatic restart')
            temporary = root / 'controller.tmp'
            temporary.write_text(json.dumps(state, indent=2) + '\n')
            temporary.replace(root / 'controller.json')
            time.sleep(5)
        for arm, seed in configurations:
            folder = root / 'runs' / arm / str(seed)
            assert json.loads((folder / 'report.json').read_text())['complete']
            for step in lock['checkpoints']:
                result = json.loads((folder / f'summary_{step}.json').read_text())
                assert result['complete'] and result['initialization'] == arm
        for key, (child, _) in jobs.items():
            assert child.poll() == 0, key
            state['jobs'][key].update(status='complete', exit_code=0)
        state.update(complete=True, phase='closed', seconds=time.monotonic() - start)
    except BaseException as error:
        state.update(phase='failed', error=repr(error), seconds=time.monotonic() - start)
        for child, _ in jobs.values():
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
        raise
    finally:
        for _, log in jobs.values():
            log.close()
        (root / 'controller.json').write_text(json.dumps(state, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    control_pair_recovery(parser.parse_args().root)
