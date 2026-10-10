"""One finite six-device diagnostic; failed scientific jobs are never retried."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time

from fastglycan.transport_normalization_audit import read_transport_normalization_lock
from fastglycan.paired_teacher_protocol import write_json


def control_transport_normalization(root):
    root=Path(root);lock=read_transport_normalization_lock(root)
    if (root/'controller.json').exists():raise FileExistsError('refuse duplicate controller')
    state=dict(complete=False,phase='preflight',started_unix=time.time(),jobs={})
    processes={};handles=[];deadline=time.monotonic()+lock['run_seconds']
    def save():
        state['observed_unix']=time.time();write_json(root/'controller.json',state)
    def start(name,command,env):
        handle=(root/f'{name}.log').open('x');handles.append(handle)
        p=subprocess.Popen(command,env=env,stdin=subprocess.DEVNULL,stdout=handle,stderr=subprocess.STDOUT,start_new_session=True)
        processes[name]=p;state['jobs'][name]=dict(pid=p.pid,status='running');save()
    def wait():
        while True:
            done=True
            for name,p in processes.items():
                code=p.poll()
                if code is None:done=False
                else:
                    state['jobs'][name].update(status='complete' if code==0 else 'failed',exit_code=code)
                    if code:raise RuntimeError(f'{name} failed; no restart')
            save()
            if done:return
            if time.monotonic()>deadline:raise TimeoutError('finite two-hour diagnostic cap')
            time.sleep(5)
    try:
        virtual=lock['virtual_root']
        env=dict(os.environ,FASTGLYCAN_AUTHORIZED_HIP_0_7='1',LAYERNORM_TYPE='torch',PROTENIX_ROOT_DIR=lock['protenix_root_dir'],
            OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONPATH=virtual+'/code/src:'+virtual+'/code/scripts')
        assert not any(k in env for k in ['CUDA_VISIBLE_DEVICES','ROCR_VISIBLE_DEVICES','HSA_VISIBLE_DEVICES','GPU_DEVICE_ORDINAL'])
        hardware=subprocess.run(['rocm-smi','--showpids','--showbus','--showmeminfo','vram','--showuse','--json'],capture_output=True,text=True,check=True,timeout=30)
        (root/'hardware_preflight.json').write_text(hardware.stdout);cards=json.loads(hardware.stdout)
        for pci in ('0000:32:00.0','0000:35:00.0','0000:11:00.0','0000:14:00.0','0000:ae:00.0','0000:b3:00.0'):
            card=next(v for v in cards.values() if isinstance(v,dict) and v.get('PCI Bus','').lower()==pci)
            if int(card['VRAM Total Used Memory (B)'])>=512*1024**2:raise RuntimeError('GPU has resident workload: '+pci)
        prefix=[lock['proot'],'-b',lock['bind_source']+':'+lock['bind_target'],lock['python'],'-u']
        state['phase']='native_audit'
        for shard in range(6):
            start(f'audit_{shard}',prefix+[virtual+'/code/scripts/run_transport_normalization.py','--root',virtual,'--shard',str(shard)],dict(env,HIP_VISIBLE_DEVICES=str(shard)))
        wait();processes={};state['phase']='scoring';save()
        for shard in range(6):
            start(f'score_{shard}',prefix+[virtual+'/code/scripts/score_transport_normalization.py','--root',virtual,'--shard',str(shard)],dict(env,HIP_VISIBLE_DEVICES=''))
        wait();processes={};state['phase']='summary';save()
        start('summary',prefix+[virtual+'/code/scripts/score_transport_normalization.py','--root',virtual],dict(env,HIP_VISIBLE_DEVICES=''))
        wait();assert json.loads((root/'summary.json').read_text())['complete']
        state.update(complete=True,phase='complete')
    except BaseException as error:
        state.update(phase='failed',error=repr(error))
        for p in processes.values():
            if p.poll() is None:
                os.killpg(p.pid,signal.SIGTERM)
                try:p.wait(timeout=15)
                except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
        raise
    finally:
        save()
        for h in handles:h.close()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    control_transport_normalization(p.parse_args().root)
