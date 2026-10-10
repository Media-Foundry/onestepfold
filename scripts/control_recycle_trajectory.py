"""Wait for the current locked batch and verification, then run a bounded audit."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def preceding_batches_complete(dependencies):
    """Completion requires successful recorded jobs and unchanged source locks."""
    complete=True
    for dep in dependencies:
        root=Path(dep['root'])
        digest=hashlib.sha256((root/dep['lock_file']).read_bytes()).hexdigest()
        if digest!=dep['lock_sha256']:
            raise RuntimeError('preceding batch lock changed')
        value=json.loads((root/'controller.json').read_text())
        jobs=value.get('jobs',{})
        if (value.get('phase')=='failed' or value.get('error')
                or any(j.get('status')=='failed' or j.get('exit_code',0)!=0
                       for j in jobs.values())):
            raise RuntimeError('preceding batch failed; no automatic replacement')
        if value.get('complete',False):
            if (value.get('phase')!='complete' or not jobs
                    or any(j.get('status')!='complete' or j.get('exit_code')!=0
                           for j in jobs.values())):
                raise RuntimeError('inconsistent preceding completion record')
        else:
            complete=False
    return complete


def control_trajectory(root):
    lock=json.loads((root/'trajectory_lock.json').read_text())
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    assert digest(root/'code/scripts/control_recycle_trajectory.py')==lock['code']['scripts/control_recycle_trajectory.py']
    state=dict(complete=False,phase='waiting_for_previous_batch',started_unix=time.time(),jobs={})
    running={};handles=[]
    def save():
        state['observed_unix']=time.time();temporary=root/'controller.tmp'
        temporary.write_text(json.dumps(state,indent=2)+'\n');temporary.replace(root/'controller.json')
    def start(name,command,env):
        handle=(root/f'{name}.log').open('x');handles.append(handle)
        process=subprocess.Popen(command,env=env,stdin=subprocess.DEVNULL,stdout=handle,
                                 stderr=subprocess.STDOUT,start_new_session=True)
        running[name]=process;state['jobs'][name]=dict(pid=process.pid,status='running');save()
    def wait_jobs(deadline):
        while True:
            done=True
            for name,process in running.items():
                code=process.poll()
                if code is None:done=False
                else:
                    state['jobs'][name].update(status='complete' if code==0 else 'failed',exit_code=code)
                    if code:raise RuntimeError(f'{name} failed; no restart')
            save()
            if done:break
            if time.time()>deadline:raise TimeoutError('finite trajectory audit deadline')
            time.sleep(5)
    try:
        for dep in lock['dependencies']:
            assert digest(Path(dep['root'])/dep['lock_file'])==dep['lock_sha256']
        while True:
            complete=preceding_batches_complete(lock['dependencies'])
            save()
            if complete:break
            if time.time()>lock['wait_deadline_unix']:raise TimeoutError('waiting for preceding batch')
            time.sleep(15)
        virtual=lock['virtual_root']
        prefix=[lock['proot'],'-b',lock['bind_source']+':'+lock['bind_target'],lock['python'],'-u']
        env=dict(os.environ,FASTGLYCAN_AUTHORIZED_HIP_0_7='1',LAYERNORM_TYPE='torch',
            PROTENIX_ROOT_DIR=lock['protenix_root_dir'],OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
            PYTHONPATH=virtual+'/code/src:'+virtual+'/code/scripts')
        assert not any(k in env for k in ('CUDA_VISIBLE_DEVICES','ROCR_VISIBLE_DEVICES','HSA_VISIBLE_DEVICES','GPU_DEVICE_ORDINAL'))
        hardware=subprocess.run(['rocm-smi','--showpids','--showbus','--showmeminfo','vram','--showuse','--json'],
                                text=True,capture_output=True,check=True,timeout=30)
        (root/'hardware_preflight.json').write_text(hardware.stdout)
        cards=json.loads(hardware.stdout)
        for pci in ('0000:8e:00.0','0000:93:00.0'):
            card=next(v for v in cards.values() if isinstance(v,dict) and v.get('PCI Bus','').lower()==pci)
            # HIP7 has a documented stuck activity reading; physical/runtime checks
            # and absence of resident workload, not that counter alone, gate use.
            if int(card['VRAM Total Used Memory (B)'])>=512*1024**2:
                raise RuntimeError(f'{pci} has resident work; do not interfere')
        deadline=time.time()+lock['run_seconds'];state['phase']='native_audit'
        for shard,hip in enumerate([6,7]):
            start(f'audit_{shard}',prefix+[virtual+'/code/scripts/run_recycle_trajectory.py',
                '--root',virtual,'--shard',str(shard)],dict(env,HIP_VISIBLE_DEVICES=str(hip)))
        wait_jobs(deadline);running={};state['phase']='coordinate_scoring';save()
        for shard in range(2):
            assert json.loads((root/f'shard_{shard}.json').read_text())['complete']
            start(f'score_{shard}',prefix+[virtual+'/code/scripts/score_recycle_trajectory.py',
                '--root',virtual,'--shard',str(shard)],dict(env,HIP_VISIBLE_DEVICES=''))
        wait_jobs(deadline);running={};state['phase']='summarize';save()
        start('summary',prefix+[virtual+'/code/scripts/summarize_recycle_trajectory.py','--root',virtual],
              dict(env,HIP_VISIBLE_DEVICES=''))
        wait_jobs(deadline)
        assert json.loads((root/'summary.json').read_text())['complete']
        state.update(complete=True,phase='complete')
    except BaseException as error:
        state.update(phase='failed',error=repr(error))
        for process in running.values():
            if process.poll() is None:
                os.killpg(process.pid,signal.SIGTERM)
                try:process.wait(timeout=15)
                except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
        raise
    finally:
        save()
        for handle in handles:handle.close()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    control_trajectory(p.parse_args().root)
