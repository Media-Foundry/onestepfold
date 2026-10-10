"""Two fixed training runs, CPU scores and serial HIP4 tensor verification."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def control_anchor_training(root):
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    lock=json.loads((root/'training_lock.json').read_text())
    assert digest(root/'protocol.md')==lock['protocol_sha256']
    for name,expected in lock['code'].items():assert digest(root/'code'/name)==expected,name
    virtual=Path('/data/user/shuang886/Folding')/root.name
    prefix=['/media/IntelSSD/onestepfold/diamondhill_migration_20261001/tools/proot/usr/bin/proot',
        '-b',str(root.parent)+':/data/user/shuang886/Folding',
        '/home/pc/anaconda3/envs/fold/bin/python','-u']
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
        LAYERNORM_TYPE='torch',FASTGLYCAN_AUTHORIZED_HIP_0_5='1',
        PROTENIX_ROOT_DIR='/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime',
        PYTHONPATH=str(virtual/'code/src')+':'+str(virtual/'code/scripts'))
    assert not any(k in env for k in ('CUDA_VISIBLE_DEVICES','ROCR_VISIBLE_DEVICES','HSA_VISIBLE_DEVICES','GPU_DEVICE_ORDINAL'))
    state=dict(complete=False,phase='tests',started_unix=time.time(),jobs={},lock_sha256=digest(root/'training_lock.json'))
    jobs={}

    def save():
        state['observed_unix']=time.time()
        p=root/'controller.tmp';p.write_text(json.dumps(state,indent=2)+'\n');p.replace(root/'controller.json')

    def launch(kind,seed,hip):
        key=f'{kind}_anchor_{seed}';out=(root/f'{key}.log').open('x')
        script={'train':'run_anchor_training.py','score':'score_stage_fullbatch.py','verify':'verify_anchor_training.py'}[kind]
        command=prefix+[str(virtual/'code/scripts'/script),'--root',str(virtual),'--seed',str(seed)]
        if kind=='score':command+=['--arm','anchor']
        process=subprocess.Popen(command,env=dict(env,HIP_VISIBLE_DEVICES=str(hip)),
            stdin=subprocess.DEVNULL,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
        jobs[key]=(process,out)
        state['jobs'][key]=dict(pid=process.pid,hip=hip,status='running',started_unix=time.time())
        save()

    save()
    try:
        with (root/'preflight_tests.log').open('x') as out:
            tests=['test_stage_pair_recovery.py','test_anchored_pair_recovery.py','test_anchor_training.py','test_stage_fullbatch.py']
            subprocess.run(prefix+['-m','pytest','-q','-p','no:cacheprovider']+[str(virtual/'code/tests'/t) for t in tests],
                env=dict(env,HIP_VISIBLE_DEVICES=''),stdout=out,stderr=subprocess.STDOUT,check=True,timeout=180)
        with (root/'preflight_imports.log').open('x') as out:
            subprocess.run(prefix+['-c','import run_anchor_training, score_stage_fullbatch, verify_anchor_training'],
                env=dict(env,HIP_VISIBLE_DEVICES=''),stdout=out,stderr=subprocess.STDOUT,check=True,timeout=120)
        state['training_deadline_unix']=time.time()+6*3600
        for hip,seed in enumerate(lock['seeds']):launch('train',seed,hip)
        state['phase']='training'
        while True:
            for key,(process,_) in list(jobs.items()):
                code=process.poll();job=state['jobs'][key]
                if code is not None:
                    job.update(status='complete' if code==0 else 'failed',exit_code=code)
                else:
                    deadline=state['training_deadline_unix'] if key.startswith('train_') else job['started_unix']+2*3600
                    if time.time()>deadline:
                        signum=signal.SIGKILL if time.time()-job.get('termination_unix',time.time())>30 else signal.SIGTERM
                        try:os.killpg(process.pid,signum)
                        except ProcessLookupError:pass
                        job.setdefault('termination_unix',time.time());job['timeout']=True
            for seed in lock['seeds']:
                if state['jobs'][f'train_anchor_{seed}']['status']=='complete' and f'score_anchor_{seed}' not in jobs:
                    launch('score',seed,'')
            busy=any(k.startswith('verify_') and p.poll() is None for k,(p,_) in jobs.items())
            if not busy:
                for seed in lock['seeds']:
                    score,verify=f'score_anchor_{seed}',f'verify_anchor_{seed}'
                    if score in jobs and state['jobs'][score]['status']=='complete' and verify not in jobs:
                        launch('verify',seed,4);break
            save()
            if all(p.poll() is not None for p,_ in jobs.values()):break
            time.sleep(5)
        ok=len(jobs)==6 and all(p.returncode==0 for p,_ in jobs.values())
        for name,expected in lock['code'].items():assert digest(root/'code'/name)==expected,name
        state.update(complete=ok,phase='closed' if ok else 'closed_with_failures')
    except BaseException as error:
        state.update(phase='failed',error=repr(error))
        for p,_ in jobs.values():
            if p.poll() is None:
                try:os.killpg(p.pid,signal.SIGTERM)
                except ProcessLookupError:pass
        raise
    finally:
        for _,out in jobs.values():out.close()
        save()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True)
    control_anchor_training(parser.parse_args().root)
