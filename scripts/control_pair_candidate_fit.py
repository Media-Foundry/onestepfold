"""Four independent fitting workers; all scientific budgets fixed before launch."""
import argparse
import hashlib
import json
import os
import signal
import subprocess
import time
from pathlib import Path


def control_candidate_fit(root):
    virtual = Path('/data/user/shuang886/Folding') / root.name
    lock = json.loads((root / 'training_lock.json').read_text())
    for path, digest in lock['code'].items():
        assert hashlib.sha256((root / 'code' / path).read_bytes()).hexdigest() == digest, path
    assert hashlib.sha256((root / 'protocol.md').read_bytes()).hexdigest() == lock['protocol_sha256']
    prefix = ['/media/IntelSSD/onestepfold/diamondhill_migration_20261001/tools/proot/usr/bin/proot',
              '-b', str(root.parent) + ':/data/user/shuang886/Folding',
              '/home/pc/anaconda3/envs/fold/bin/python', '-u']
    env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
               LAYERNORM_TYPE='torch', FASTGLYCAN_AUTHORIZED_HIP_0_5='1',
               PROTENIX_ROOT_DIR='/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime',
               PYTHONPATH=str(virtual / 'code/src') + ':' + str(virtual / 'code/scripts'))
    assert not any(k in env for k in ('CUDA_VISIBLE_DEVICES', 'ROCR_VISIBLE_DEVICES',
                                     'HSA_VISIBLE_DEVICES', 'GPU_DEVICE_ORDINAL'))
    # Tests precede all model construction and label use.
    with (root / 'preflight_tests.log').open('x') as log:
        subprocess.run(prefix + ['-m', 'pytest', '-q', str(virtual / 'code/tests/test_pair_candidate_fit.py'),
                                str(virtual / 'code/tests/test_pair_recovery.py'),
                                str(virtual / 'code/tests/test_response_moments.py')],
                       env=dict(env, HIP_VISIBLE_DEVICES='4'), stdout=log, stderr=subprocess.STDOUT, check=True)
    configs = [(arm, seed) for seed in lock['seeds'] for arm in lock['arms']]
    assert len(configs) == 4
    jobs, state = {}, dict(complete=False, phase='running', jobs={})
    start = time.monotonic()
    try:
        for hip, (arm, seed) in enumerate(configs):
            key = f'train_{arm}_{seed}'
            log = (root / f'{key}.log').open('x')
            cmd = prefix + [str(virtual / 'code/scripts/run_pair_candidate_fit.py'), '--root', str(virtual),
                            '--arm', arm, '--seed', str(seed)]
            child = subprocess.Popen(cmd, env=dict(env, HIP_VISIBLE_DEVICES=str(hip)), stdin=subprocess.DEVNULL,
                                     stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            jobs[key] = child, log
            state['jobs'][key] = dict(pid=child.pid, hip=hip, status='running')
        while True:
            for key, (child, _) in list(jobs.items()):
                code = child.poll()
                if code is not None:
                    state['jobs'][key].update(status='complete' if code == 0 else 'failed', exit_code=code)
                    if code:
                        raise RuntimeError(f'{key} exited {code}')
            for arm, seed in configs:
                key = f'score_{arm}_{seed}'
                if key in jobs or state['jobs'][f'train_{arm}_{seed}']['status'] != 'complete':
                    continue
                log = (root / f'{key}.log').open('x')
                cmd = prefix + [str(virtual / 'code/scripts/score_pair_candidate_fit.py'), '--root', str(virtual),
                                '--arm', arm, '--seed', str(seed)]
                child = subprocess.Popen(cmd, env=dict(env, HIP_VISIBLE_DEVICES='4'), stdin=subprocess.DEVNULL,
                                         stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                jobs[key] = child, log
                state['jobs'][key] = dict(pid=child.pid, kind='cpu_score', status='running')
            state['seconds'] = time.monotonic() - start
            if len(jobs) == 8 and all(child.poll() == 0 for child, _ in jobs.values()):
                break
            if state['seconds'] > 6 * 3600:
                raise TimeoutError('fixed six-hour cap; no automatic restart')
            temp = root / 'controller.tmp'
            temp.write_text(json.dumps(state, indent=2) + '\n'); temp.replace(root / 'controller.json')
            time.sleep(5)
        for arm, seed in configs:
            assert json.loads((root / 'runs' / arm / str(seed) / 'score_complete.json').read_text())['complete']
        state.update(complete=True, phase='closed')
    except BaseException as error:
        state.update(phase='failed', error=repr(error))
        for child, _ in jobs.values():
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
        raise
    finally:
        for _, log in jobs.values():
            log.close()
        state['seconds'] = time.monotonic() - start
        (root / 'controller.json').write_text(json.dumps(state, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--root', type=Path, required=True)
    control_candidate_fit(parser.parse_args().root)
