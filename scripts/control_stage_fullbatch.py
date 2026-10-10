"""Four isolated training workers; finite wall caps and retained failures."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def control_stage_fullbatch(root):
    lock = json.loads((root/'training_lock.json').read_text())
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    assert digest(root/'protocol.md') == lock['protocol_sha256']
    for name, expected in lock['code'].items():
        assert digest(root/'code'/name) == expected, name
    virtual = Path('/data/user/shuang886/Folding')/root.name
    prefix = ['/media/IntelSSD/onestepfold/diamondhill_migration_20261001/tools/proot/usr/bin/proot',
              '-b', str(root.parent)+':/data/user/shuang886/Folding',
              '/home/pc/anaconda3/envs/fold/bin/python', '-u']
    env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
               LAYERNORM_TYPE='torch', FASTGLYCAN_AUTHORIZED_HIP_0_5='1',
               PROTENIX_ROOT_DIR='/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime',
               PYTHONPATH=str(virtual/'code/src')+':'+str(virtual/'code/scripts'))
    assert not any(k in env for k in ('CUDA_VISIBLE_DEVICES','ROCR_VISIBLE_DEVICES','HSA_VISIBLE_DEVICES','GPU_DEVICE_ORDINAL'))
    state = dict(complete=False, phase='tests', started_unix=time.time(), jobs={}, lock_sha256=digest(root/'training_lock.json'))
    jobs = {}

    def save():
        state['observed_unix'] = time.time()
        tmp = root/'controller.tmp'
        tmp.write_text(json.dumps(state, indent=2)+'\n'); tmp.replace(root/'controller.json')

    def launch(kind, arm, seed, hip):
        key = f'{kind}_{arm}_{seed}'
        output = (root/f'{key}.log').open('x')
        script = dict(train='run_stage_fullbatch.py', score='score_stage_fullbatch.py', verify='verify_stage_fullbatch.py')[kind]
        command = prefix+[str(virtual/'code/scripts'/script), '--root', str(virtual), '--arm', arm, '--seed', str(seed)]
        process = subprocess.Popen(command, env=dict(env, HIP_VISIBLE_DEVICES=str(hip)),
            stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
        jobs[key] = process, output
        state['jobs'][key] = dict(pid=process.pid, hip=hip, status='running', started_unix=time.time())
        save()

    save()
    try:
        with (root/'preflight_tests.log').open('x') as output:
            subprocess.run(prefix+['-m','pytest','-q','-p','no:cacheprovider',str(virtual/'code/tests/test_stage_fullbatch.py')],
                env=dict(env,HIP_VISIBLE_DEVICES='4'),stdout=output,stderr=subprocess.STDOUT,check=True,timeout=180)
        # A source snapshot may pass optimizer tests yet omit a verifier import.
        # Catch this before spending any training budget. No model is constructed.
        with (root/'preflight_imports.log').open('x') as output:
            subprocess.run(prefix+['-c', 'import run_stage_fullbatch, score_stage_fullbatch, verify_stage_fullbatch'],
                env=dict(env,HIP_VISIBLE_DEVICES=''),stdout=output,stderr=subprocess.STDOUT,check=True,timeout=120)
        configurations = [(arm, seed) for seed in lock['seeds'] for arm in lock['arms']]
        state['training_deadline_unix'] = time.time()+6*3600
        for hip, (arm, seed) in enumerate(configurations):
            launch('train', arm, seed, hip)
        state['phase'] = 'training'
        while True:
            for key, (process, _) in jobs.items():
                code = process.poll()
                if code is not None:
                    state['jobs'][key].update(status='complete' if code == 0 else 'failed', exit_code=code)
                else:
                    job = state['jobs'][key]
                    deadline = state['training_deadline_unix'] if key.startswith('train_') else job['started_unix']+2*3600
                    if time.time() > deadline:
                        signum = signal.SIGKILL if time.time()-job.get('termination_unix', time.time()) > 30 else signal.SIGTERM
                        try:
                            os.killpg(process.pid, signum)
                        except ProcessLookupError:
                            pass
                        job.setdefault('termination_unix', time.time())
                        job['timeout'] = True
            for arm, seed in configurations:
                train = f'train_{arm}_{seed}'
                score = f'score_{arm}_{seed}'
                if state['jobs'][train]['status'] == 'complete' and score not in jobs:
                    launch('score', arm, seed, 4)
            busy = any(key.startswith('verify_') and process.poll() is None for key,(process,_) in jobs.items())
            if not busy:
                for arm, seed in configurations:
                    score = f'score_{arm}_{seed}'
                    verify = f'verify_{arm}_{seed}'
                    if score in jobs and state['jobs'][score]['status'] == 'complete' and verify not in jobs:
                        launch('verify', arm, seed, 4)
                        break
            save()
            if all(process.poll() is not None for process,_ in jobs.values()):
                break
            time.sleep(5)
        successful = len(jobs) == 12 and all(process.returncode == 0 for process,_ in jobs.values())
        state.update(complete=successful, phase='closed' if successful else 'closed_with_failures')
    except BaseException as error:
        state.update(phase='failed', error=repr(error))
        for process,_ in jobs.values():
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
        raise
    finally:
        for _, output in jobs.values():
            output.close()
        save()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    control_stage_fullbatch(parser.parse_args().root)
