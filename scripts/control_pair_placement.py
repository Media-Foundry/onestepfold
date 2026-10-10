"""Own the fixed four-run comparison after an independent parallel gate."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def control_pair_placement(root):
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    lock=json.loads((root/'training_lock.json').read_text())
    for name,value in lock['code'].items():assert digest(root/'code'/name)==value,name
    assert digest(root/'protocol.md')==lock['protocol_sha256']
    virtual=lock['virtual_root'];prefix=[lock['proot'],'-b',lock['bind_source']+':'+lock['bind_target'],lock['python']]
    env=dict(os.environ,HIP_VISIBLE_DEVICES='0,1,2,3,4,5',FASTGLYCAN_AUTHORIZED_HIP_0_5='1',LAYERNORM_TYPE='torch',
        PROTENIX_ROOT_DIR=lock['protenix_root_dir'],PYTHONPATH=virtual+'/code/src:'+virtual+'/code/scripts',
        OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',GLOO_SOCKET_IFNAME='lo',PYTHONUNBUFFERED='1')
    assert not any(k in env for k in ('CUDA_VISIBLE_DEVICES','ROCR_VISIBLE_DEVICES','HSA_VISIBLE_DEVICES','GPU_DEVICE_ORDINAL'))
    state=dict(complete=False,phase='tests',started_unix=time.time(),jobs={},lock_sha256=digest(root/'training_lock.json'))
    jobs={};deadline=time.time()+1800

    def save():
        state['observed_unix']=time.time();p=root/'controller.tmp'
        p.write_text(json.dumps(state,indent=2)+'\n');p.replace(root/'controller.json')

    def launch(name,command,environment):
        out=(root/(name+'.log')).open('x')
        process=subprocess.Popen(command,env=environment,cwd=root/'code',stdin=subprocess.DEVNULL,
            stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
        jobs[name]=(process,out);state['jobs'][name]=dict(pid=process.pid,status='running',started_unix=time.time());save()

    def wait(names):
        while True:
            for name,(process,_) in jobs.items():
                code=process.poll()
                if code is not None:
                    state['jobs'][name].update(exit_code=code,status='complete' if code==0 else 'failed')
                    if code:raise RuntimeError(f'{name} failed; no restart')
            save()
            if all(jobs[name][0].poll() is not None for name in names):return
            if time.time()>deadline:raise TimeoutError('finite placement budget expired')
            time.sleep(5)

    def native(mode,arm,seed):
        return prefix+['-m','torch.distributed.run','--standalone','--nproc-per-node=6','--max-restarts=0',
            virtual+'/code/scripts/run_pair_placement.py','--root',virtual,'--mode',mode,'--arm',arm,'--seed',str(seed)]

    try:
        tests=['test_early_pair_recovery.py','test_anchored_pair_recovery.py','test_stage_pair_recovery.py','test_anchor_training.py','test_site_parallel.py','test_native_parallel_audit.py','test_pair_placement.py']
        launch('tests',prefix+['-m','pytest','-q','-p','no:cacheprovider']+[virtual+'/code/tests/'+t for t in tests],dict(env,HIP_VISIBLE_DEVICES=''))
        wait(['tests']);state['phase']='parallel_gate'
        launch('parallel_gate',native('audit','early',272001),env);wait(['parallel_gate'])
        command='from fastglycan.placement_verification import verify_parallel_gate; verify_parallel_gate('+repr(virtual)+')'
        launch('gate_verification',prefix+['-c',command],dict(env,HIP_VISIBLE_DEVICES=''));wait(['gate_verification'])
        state['training_started_unix']=time.time();deadline=time.time()+6*3600
        state['training_deadline_unix']=deadline
        for arm,seed in lock['run_order']:
            name=f'train_{arm}_{seed}';state['phase']=name
            launch(name,native('train',arm,seed),env);wait([name])
            score=f'score_{arm}_{seed}'
            launch(score,prefix+[virtual+'/code/scripts/score_stage_fullbatch.py','--root',virtual,'--arm',arm,'--seed',str(seed)],dict(env,HIP_VISIBLE_DEVICES=''))
        state['phase']='scoring';wait(list(jobs))
        command='from fastglycan.placement_verification import verify_training_ledger; verify_training_ledger('+repr(virtual)+')'
        launch('ledger_verification',prefix+['-c',command],dict(env,HIP_VISIBLE_DEVICES=''));wait(['ledger_verification'])
        state.update(complete=True,phase='complete',native_checkpoint_replay_pending=True)
    except BaseException as error:
        state.update(phase='failed',error=repr(error))
        for process,_ in jobs.values():
            if process.poll() is None:
                os.killpg(process.pid,signal.SIGTERM)
                try:process.wait(timeout=20)
                except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
        raise
    finally:
        for _,out in jobs.values():out.close()
        save()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    control_pair_placement(p.parse_args().root)
