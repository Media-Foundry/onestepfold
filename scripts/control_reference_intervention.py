"""Four fixed inference-only jobs, followed by CPU scoring; no run selection."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def control_reference_intervention(root):
    lock = json.loads((root/'intervention_lock.json').read_text())
    for path, digest in lock['code'].items():
        assert hashlib.sha256((root/'audit_code'/path).read_bytes()).hexdigest() == digest, path
    virtual = Path('/data/user/shuang886/Folding') / root.name
    base = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
                LAYERNORM_TYPE='torch', PROTENIX_ROOT_DIR='/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime',
                PYTHONPATH=f'{virtual}/audit_code/src:{virtual}/audit_code/scripts')
    if any(k in base for k in ('CUDA_VISIBLE_DEVICES','ROCR_VISIBLE_DEVICES','GPU_DEVICE_ORDINAL','HSA_VISIBLE_DEVICES')):
        raise RuntimeError('conflicting inherited selector')
    command = ['/media/IntelSSD/onestepfold/diamondhill_migration_20261001/tools/proot/usr/bin/proot',
               '-b',str(root.parent)+':/data/user/shuang886/Folding',
               '/home/pc/anaconda3/envs/fold/bin/python','-u',
               str(virtual/'audit_code/scripts/run_reference_intervention.py'),'--root',str(virtual)]
    records, active = {}, {}
    begin = time.monotonic()
    for hip, run in enumerate(lock['runs']):
        name = run['run_id']
        log = (root/f'decode_{name}.log').open('w')
        p = subprocess.Popen(command+['--run-id',name,'--mode','decode'],env=dict(base,HIP_VISIBLE_DEVICES=str(hip)),
                             stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        active[name] = (p,log,'decode',time.monotonic())
        records[name] = dict(decode_pid=p.pid,status='decoding')
    while active:
        for name,(p,log,phase,started) in list(active.items()):
            code = p.poll()
            if code is None and time.monotonic()-started > 7200:
                os.killpg(p.pid,signal.SIGTERM)
                try:
                    p.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    os.killpg(p.pid,signal.SIGKILL); p.wait()
                code = 124
            if code is None:
                continue
            log.close(); del active[name]
            records[name][f'{phase}_exit_code'] = code
            if code:
                records[name]['status'] = 'failed'
            elif phase == 'decode':
                log = (root/f'score_{name}.log').open('w')
                p = subprocess.Popen(command+['--run-id',name,'--mode','score'],env=base,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                active[name] = (p,log,'score',time.monotonic())
                records[name].update(status='scoring',score_pid=p.pid)
            else:
                records[name]['status'] = 'complete'
        state = dict(complete=not active and all(r['status']=='complete' for r in records.values()),
                     phase='running' if active else 'closed',jobs=records,seconds=time.monotonic()-begin)
        temp = root/'controller.tmp'
        temp.write_text(json.dumps(state,indent=2)+'\n'); temp.replace(root/'controller.json')
        if active:
            time.sleep(5)
    if state['complete']:
        summaries = {name: json.loads((root/'runs'/name/'summary.json').read_text()) for name in records}
        reports = {name: json.loads((root/'runs'/name/'report.json').read_text()) for name in records}
        assert sum(r['counts']['s1'] for r in reports.values()) == 8208
        assert sum(r['original_outputs_replayed_bitwise'] for r in reports.values()) == 2736
        aggregate = dict(complete=True,summaries=summaries,counts=dict(s1=8208,updates=0,c4=0,input_embedder=0),
                         original_outputs_replayed_bitwise=2736,independent_confirmation=False,promoted=False)
        (root/'aggregate.json').write_text(json.dumps(aggregate,indent=2,allow_nan=False)+'\n')


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    control_reference_intervention(p.parse_args().root)
