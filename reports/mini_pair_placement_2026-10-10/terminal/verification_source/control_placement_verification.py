"""Wait for the original finite comparison, then replay its saved checkpoints."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def control_placement_verification(root):
    lock=json.loads((root/'verification_lock.json').read_text())
    training=Path(lock['training_root']);digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    assert digest(training/'training_lock.json')==lock['training_lock_sha256']
    assert digest(root/'verify_pair_placement.py')==lock['verifier_sha256']
    source=json.loads((training/'training_lock.json').read_text())
    virtual='/data/user/shuang886/Folding/'+root.name
    env=dict(os.environ,HIP_VISIBLE_DEVICES='0',FASTGLYCAN_AUTHORIZED_HIP_0_5='1',LAYERNORM_TYPE='torch',
        PROTENIX_ROOT_DIR=source['protenix_root_dir'],OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
        PYTHONPATH=source['virtual_root']+'/code/src:'+source['virtual_root']+'/code/scripts')
    assert not any(k in env for k in ('CUDA_VISIBLE_DEVICES','ROCR_VISIBLE_DEVICES','HSA_VISIBLE_DEVICES','GPU_DEVICE_ORDINAL'))
    prefix=[source['proot'],'-b',source['bind_source']+':'+source['bind_target'],source['python'],'-u']
    state=dict(complete=False,phase='waiting_for_original_training',started_unix=time.time(),jobs={})
    deadline=state['started_unix']+8*3600;process=None

    def save():
        state['observed_unix']=time.time();p=root/'controller.tmp'
        p.write_text(json.dumps(state,indent=2)+'\n');p.replace(root/'controller.json')

    try:
        while True:
            original=json.loads((training/'controller.json').read_text());save()
            if original['phase']=='failed':raise RuntimeError('original comparison failed; no verification or restart')
            if original['complete']:break
            if time.time()>deadline:raise TimeoutError('original comparison waiting deadline')
            time.sleep(15)
        assert json.loads((training/'ledger_verification.json').read_text())['complete']
        deadline=time.time()+2*3600
        for arm,seed in source['run_order']:
            name=f'{arm}_{seed}';state['phase']=name
            hardware=subprocess.run(['rocm-smi','--showuse','--showmeminfo','vram','--showbus','--json'],capture_output=True,text=True,check=True)
            (root/f'{name}_hardware.json').write_text(hardware.stdout)
            card=next(v for v in json.loads(hardware.stdout).values() if v['PCI Bus'].lower()==source['pci_buses'][0].lower())
            if int(card['GPU use (%)']) or int(card['VRAM Total Used Memory (B)'])>=512*1024**2:
                raise RuntimeError('HIP0 is occupied; do not interfere with other work')
            command=prefix+[virtual+'/verify_pair_placement.py','--root',source['virtual_root'],
                '--arm',arm,'--seed',str(seed),'--output',virtual+'/'+name]
            with (root/(name+'.log')).open('x') as out:
                process=subprocess.Popen(command,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
                state['jobs'][name]=dict(pid=process.pid,status='running');save()
                while process.poll() is None:
                    if time.time()>deadline:raise TimeoutError('finite verification deadline')
                    save();time.sleep(5)
                state['jobs'][name].update(exit_code=process.returncode,status='complete' if process.returncode==0 else 'failed')
                if process.returncode:raise RuntimeError(f'{name} verifier failed; no restart')
            assert json.loads((root/name/'tensor_verification.json').read_text())['complete']
        assert digest(root/'verify_pair_placement.py')==lock['verifier_sha256']
        state.update(complete=True,phase='complete')
    except BaseException as error:
        state.update(phase='failed',error=repr(error))
        if process is not None and process.poll() is None:
            os.killpg(process.pid,signal.SIGTERM)
            try:process.wait(timeout=20)
            except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
        raise
    finally:save()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    control_placement_verification(p.parse_args().root)
