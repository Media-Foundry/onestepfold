"""Run the unchanged tensor verifier with its missing, separately locked dependency.

Never restarts training/scoring or edits their records. Original failed jobs stay
failed; this controller records four new verification-only attempts on HIP4.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def recover_stage_fullbatch_verification(root):
    root = Path(root).resolve()
    recovery = root / 'verification_recovery'
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    read = lambda p: json.loads(p.read_text())
    lock = read(recovery / 'lock.json')
    training = read(root / 'training_lock.json')
    assert sha(root / 'training_lock.json') == lock['training_lock_sha256']
    for name, digest in lock['code'].items():
        assert sha(recovery / 'code' / name) == digest, name

    def protect():
        for name, digest in lock['protected_files'].items():
            assert sha(root / name) == digest, name
        for name, digest in training['code'].items():
            assert sha(root / 'code' / name) == digest, name

    protect()
    assert not (recovery / 'controller.json').exists()
    virtual = Path('/data/user/shuang886/Folding') / root.name
    prefix = ['/media/IntelSSD/onestepfold/diamondhill_migration_20261001/tools/proot/usr/bin/proot',
              '-b', str(root.parent) + ':/data/user/shuang886/Folding',
              '/home/pc/anaconda3/envs/fold/bin/python', '-u']
    env = dict(os.environ, HIP_VISIBLE_DEVICES='4', OMP_NUM_THREADS='1',
               OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', LAYERNORM_TYPE='torch',
               FASTGLYCAN_AUTHORIZED_HIP_0_5='1', PYTHONDONTWRITEBYTECODE='1',
               PROTENIX_ROOT_DIR='/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime',
               PYTHONPATH=':'.join(str(virtual / p) for p in (
                   'code/src', 'code/scripts', 'verification_recovery/code')))
    assert not any(k in env for k in ('CUDA_VISIBLE_DEVICES', 'ROCR_VISIBLE_DEVICES',
                                      'HSA_VISIBLE_DEVICES', 'GPU_DEVICE_ORDINAL'))
    state = dict(complete=False, phase='import_preflight', started_unix=time.time(),
                 lock_sha256=sha(recovery / 'lock.json'), jobs={})

    def save():
        state['observed_unix'] = time.time()
        temp = recovery / 'controller.tmp'
        temp.write_text(json.dumps(state, indent=2) + '\n')
        temp.replace(recovery / 'controller.json')

    save()
    try:
        probe = ("import verify_stage_fullbatch as v, verify_stage_pair_recovery as m; "
                 "from pathlib import Path; "
                 "assert str(Path(m.__file__).parent).endswith('verification_recovery/code'); "
                 "print(v.__file__); print(m.__file__)")
        with (recovery / 'import_preflight.log').open('x') as output:
            subprocess.run(prefix + ['-c', probe], env=dict(env, HIP_VISIBLE_DEVICES=''),
                           stdout=output, stderr=subprocess.STDOUT, check=True, timeout=120)
        state['phase'] = 'verifying'; save()
        for arm in training['arms']:
            for seed in training['seeds']:
                key = f'verify_{arm}_{seed}'
                result = root / 'runs' / arm / str(seed) / 'tensor_verification.json'
                assert not result.exists(), 'never overwrite a previous verification result'
                command = prefix + [str(virtual / 'code/scripts/verify_stage_fullbatch.py'),
                                    '--root', str(virtual), '--arm', arm, '--seed', str(seed)]
                with (recovery / (key + '.log')).open('x') as output:
                    process = subprocess.Popen(command, env=env, stdin=subprocess.DEVNULL,
                        stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
                    job = dict(pid=process.pid, hip=4, started_unix=time.time(), status='running')
                    state['jobs'][key] = job; save()
                    while process.poll() is None:
                        if time.time() - job['started_unix'] > 7200:
                            job['timeout'] = True
                            os.killpg(process.pid, signal.SIGTERM)
                            try:
                                process.wait(timeout=30)
                            except subprocess.TimeoutExpired:
                                os.killpg(process.pid, signal.SIGKILL)
                            break
                        save(); time.sleep(5)
                    code = process.wait()
                job.update(status='complete' if code == 0 else 'failed', exit_code=code,
                           finished_unix=time.time())
                if code == 0:
                    tensor = read(result)
                    assert tensor['complete'] and tensor['feature_forwards'] == 2736
                    job['result_sha256'] = sha(result)
                save()
        protect()
        state['protected_files_unchanged'] = True
        state['frozen_source_files_verified'] = len(training['code'])
        success = len(state['jobs']) == 4 and all(
            j['exit_code'] == 0 and not j.get('timeout') for j in state['jobs'].values())
        state.update(complete=success, phase='closed' if success else 'closed_with_failures')
    except BaseException as error:
        state.update(phase='failed', error=repr(error))
        raise
    finally:
        save()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    recover_stage_fullbatch_verification(parser.parse_args().root)
