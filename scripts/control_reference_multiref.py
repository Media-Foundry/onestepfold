"""Run a frozen preflight followed by eight fixed jobs, without failed-seed retries."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def control_reference_multiref(root):
    virtual = Path('/data/user/shuang886/Folding') / root.name
    base = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
                LAYERNORM_TYPE='torch',
                PROTENIX_ROOT_DIR='/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime',
                PYTHONPATH=f'{virtual}/code/src:{virtual}/code/scripts')
    if any(k in base for k in ('CUDA_VISIBLE_DEVICES', 'ROCR_VISIBLE_DEVICES',
                               'GPU_DEVICE_ORDINAL', 'HSA_VISIBLE_DEVICES')):
        raise RuntimeError('conflicting inherited selector')
    command = ['/media/IntelSSD/onestepfold/diamondhill_migration_20261001/tools/proot/usr/bin/proot',
               '-b', str(root.parent)+':/data/user/shuang886/Folding',
               '/home/pc/anaconda3/envs/fold/bin/python', '-u',
               str(virtual/'code/scripts/run_reference_multiref.py'), '--root', str(virtual)]
    started = time.monotonic()
    status = dict(complete=False, phase='preflight', jobs={}, seconds=0)
    status_path = root/'controller.json'
    status_path.write_text(json.dumps(status, indent=2)+'\n')
    with (root/'preflight.log').open('w') as log:
        process = subprocess.Popen(command+['--mode', 'preflight'], env=dict(base, HIP_VISIBLE_DEVICES='0'),
                                   stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = process.wait(timeout=5400)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL); process.wait()
            code = 124
    status['preflight_exit_code'] = code
    if code != 0:
        status.update(phase='preflight_failed', seconds=time.monotonic()-started)
        status_path.write_text(json.dumps(status, indent=2)+'\n')
        return
    assert json.loads((root/'preflight.json').read_text())['complete']
    plan = json.loads((root/'plan.json').read_text())
    pending = sorted(plan['runs'], key=lambda r: (-r['updates'], r['run_id']))
    # Only this subset has passed the existing PCI guard on this host.
    slots = [0, 1, 2, 3]
    active = {}
    status['phase'] = 'training'
    while pending or active:
        for hip in slots:
            if hip in active or not pending:
                continue
            run = pending.pop(0); name = run['run_id']
            log = (root/f'{name}.log').open('w')
            proc = subprocess.Popen(command+['--mode', 'train', '--run-id', name],
                                    env=dict(base, HIP_VISIBLE_DEVICES=str(hip)), stdout=log,
                                    stderr=subprocess.STDOUT, start_new_session=True)
            active[hip] = (proc, log, name, time.monotonic())
            status['jobs'][name] = dict(pid=proc.pid, status='running', updates_budget=run['updates'])
        for hip, (proc, log, name, begin) in list(active.items()):
            code = proc.poll()
            if code is None and time.monotonic()-begin > 21600:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL); proc.wait()
                code = 124
            if code is not None:
                log.close(); del active[hip]
                status['jobs'][name].update(status='complete' if code == 0 else 'failed',
                                           exit_code=code, seconds=time.monotonic()-begin)
        status['seconds'] = time.monotonic()-started
        temporary = status_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(status, indent=2)+'\n'); temporary.replace(status_path)
        if pending or active:
            time.sleep(5)
    status.update(phase='closed', complete=all(x['exit_code'] == 0 for x in status['jobs'].values()))
    status_path.write_text(json.dumps(status, indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    control_reference_multiref(parser.parse_args().root)
