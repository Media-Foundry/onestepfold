"""Bounded four-worker TRAIN diagnostic; report completion is mandatory."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def control_stage_update_audit(root):
    begin = time.monotonic()
    lock = json.loads((root/'audit_lock.json').read_text())
    virtual = Path('/data/user/shuang886/Folding')/root.name
    prefix = ['/media/IntelSSD/onestepfold/diamondhill_migration_20261001/tools/proot/usr/bin/proot',
              '-b',str(root.parent)+':/data/user/shuang886/Folding',
              '/home/pc/anaconda3/envs/fold/bin/python','-u']
    state = dict(complete=False,phase='audit',jobs=[],deadline_unix=lock['deadline_unix'])
    def save():
        state['seconds'] = time.monotonic()-begin
        p=root/'controller.tmp';p.write_text(json.dumps(state,indent=2)+'\n');p.replace(root/'controller.json')
    active=[]
    try:
        for hip,(arm,seed) in enumerate((('final',272001),('final',272003),('hint',272001),('hint',272003))):
            env=dict(os.environ,HIP_VISIBLE_DEVICES=str(hip),OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',
                     MKL_NUM_THREADS='1',LAYERNORM_TYPE='torch',FASTGLYCAN_AUTHORIZED_HIP_0_5='1',
                     PROTENIX_ROOT_DIR='/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime',
                     PYTHONPATH=str(virtual/'code/src')+':'+str(virtual/'code/scripts'))
            assert not any(k in env for k in ('CUDA_VISIBLE_DEVICES','ROCR_VISIBLE_DEVICES','HSA_VISIBLE_DEVICES','GPU_DEVICE_ORDINAL'))
            log=(root/f'audit_{arm}_{seed}.log').open('x')
            process=subprocess.Popen(prefix+[str(virtual/'code/scripts/audit_stage_updates.py'),
                '--root',str(virtual),'--arm',arm,'--seed',str(seed)],env=env,stdin=subprocess.DEVNULL,
                stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            job=dict(arm=arm,seed=seed,hip=hip,pid=process.pid,status='running')
            state['jobs'].append(job);active.append((process,log,job));save()
        while active:
            for process,log,job in active[:]:
                code=process.poll()
                if code is None:continue
                log.close();active.remove((process,log,job));job['exit_code']=code
                report_path=root/'runs'/job['arm']/str(job['seed'])/'report.json'
                report=json.loads(report_path.read_text()) if report_path.exists() else {}
                ok=code==0 and report.get('complete') and len(report.get('nodes',[]))==3
                job['status']='complete' if ok else 'failed';save()
                if not ok:raise RuntimeError(f'Incomplete audit {job}')
            if time.time()>lock['deadline_unix']:raise TimeoutError('six-hour diagnostic cap reached')
            if active:time.sleep(5)
        state.update(complete=True,phase='closed');save()
    except BaseException as error:
        state.update(phase='failed',error=repr(error));save()
        for process,log,job in active:
            if process.poll() is None:
                os.killpg(process.pid,signal.SIGTERM)
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
            job.update(status='terminated_after_audit_failure',exit_code=process.returncode);log.close()
        save();raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    control_stage_update_audit(p.parse_args().root)
