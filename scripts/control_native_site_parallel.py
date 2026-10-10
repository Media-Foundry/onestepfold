"""Own one finite torchrun audit group, then independently verify on CPU."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def control_native_site_parallel(root):
    root = Path(root).resolve()
    lock = json.loads((root/'audit_lock.json').read_text())
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    for name, value in lock['code'].items():
        assert digest(root/'code'/name) == value, name
    assert digest(root/'protocol.md') == lock['protocol_sha256']
    state = dict(complete=False, phase='starting', jobs={}, started_unix=time.time(),
                 audit_lock_sha256=digest(root/'audit_lock.json'))
    deadline = state['started_unix']+lock['timeout_seconds']
    assert lock['timeout_seconds'] == 1800

    def save():
        state['observed_unix'] = time.time()
        temporary = root/'controller.tmp'
        temporary.write_text(json.dumps(state, indent=2)+'\n')
        temporary.replace(root/'controller.json')

    env = dict(os.environ)
    assert not any(k in env for k in ('CUDA_VISIBLE_DEVICES','ROCR_VISIBLE_DEVICES','GPU_DEVICE_ORDINAL'))
    virtual = lock['virtual_root']
    env.update(HIP_VISIBLE_DEVICES=','.join(map(str,lock['hip_devices'])),
               FASTGLYCAN_AUTHORIZED_HIP_0_5='1',
               PROTENIX_ROOT_DIR=lock['protenix_root_dir'], LAYERNORM_TYPE='torch',
               PYTHONPATH=virtual+'/code/src:'+virtual+'/code/scripts',
               OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
               GLOO_SOCKET_IFNAME='lo', PYTHONUNBUFFERED='1')
    prefix = [lock['proot'], '-b', lock['bind_source']+':'+lock['bind_target'], lock['python']]

    def run(name, command, environment):
        state['phase'] = name
        with (root/(name+'.log')).open('x') as output:
            process = subprocess.Popen(command, env=environment, cwd=root/'code',
                                       stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
            record = dict(pid=process.pid, status='running', started_unix=time.time())
            state['jobs'][name] = record; save()
            try:
                while process.poll() is None:
                    if time.time() >= deadline:
                        raise TimeoutError('finite native audit budget expired')
                    save()
                    try:
                        process.wait(timeout=min(5, max(.1, deadline-time.time())))
                    except subprocess.TimeoutExpired:
                        pass
                record.update(exit_code=process.returncode, status='complete' if process.returncode==0 else 'failed')
                if process.returncode:
                    raise RuntimeError(f'{name} exited {process.returncode}; no retry')
            except BaseException:
                if process.poll() is None:
                    assert os.getpgid(process.pid) == process.pid
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=20)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL); process.wait()
                record.update(exit_code=process.returncode, status='failed')
                raise
            finally:
                save()

    try:
        run('native', prefix+['-m','torch.distributed.run','--standalone','--nproc-per-node=6',
            '--max-restarts=0',virtual+'/code/scripts/audit_native_site_parallel.py','--root',virtual], env)
        cpu_env = dict(env, HIP_VISIBLE_DEVICES='')
        command = 'from fastglycan.native_parallel_audit import verify_native_parallel_audit; print(verify_native_parallel_audit('+repr(virtual)+'))'
        run('verify', prefix+['-c',command], cpu_env)
        state.update(complete=True, phase='complete', verification_sha256=digest(root/'verification.json'))
    except BaseException as error:
        state.update(phase='failed', error=repr(error)); raise
    finally:
        save()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--root', type=Path, required=True)
    control_native_site_parallel(parser.parse_args().root)
