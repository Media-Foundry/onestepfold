"""Preflight -> two fixed seeds -> independent CPU audit -> serial GPU replay."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def control_compensation(root):
    lock=json.loads((root/'compensation_lock.json').read_text())
    for p,digest in lock['code'].items():
        assert hashlib.sha256((root/'audit_code'/p).read_bytes()).hexdigest()==digest,p
    virtual='/data/user/shuang886/Folding/'+root.name
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
             LAYERNORM_TYPE='torch',PROTENIX_ROOT_DIR='/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime',
             PYTHONPATH=virtual+'/audit_code/src:'+virtual+'/audit_code/scripts')
    assert not any(k in env for k in ['CUDA_VISIBLE_DEVICES','ROCR_VISIBLE_DEVICES','GPU_DEVICE_ORDINAL','HSA_VISIBLE_DEVICES','HIP_VISIBLE_DEVICES'])
    prefix=['/media/IntelSSD/onestepfold/diamondhill_migration_20261001/tools/proot/usr/bin/proot',
            '-b',str(root.parent)+':/data/user/shuang886/Folding','/home/pc/anaconda3/envs/fold/bin/python','-u']
    started=time.monotonic();jobs={};state=dict(complete=False,phase='preflight',jobs=jobs)

    def save():
        state['seconds']=time.monotonic()-started
        p=root/'controller.tmp';p.write_text(json.dumps(state,indent=2)+'\n');p.replace(root/'controller.json')

    def launch(name,script,args,hip=None):
        target=prefix+[virtual+'/audit_code/scripts/'+script,'--root',virtual]+args
        log=(root/(name+'.log')).open('w')
        p=subprocess.Popen(target,env=env if hip is None else dict(env,HIP_VISIBLE_DEVICES=str(hip)),
                           stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        jobs[name]=dict(pid=p.pid,status='running',hip=hip)
        save();return p,log,time.monotonic()

    def finish(name,job,limit):
        p,log,t=job;code=p.poll()
        if code is None and time.monotonic()-t>limit:
            os.killpg(p.pid,signal.SIGTERM)
            try:p.wait(timeout=15)
            except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
            code=124
        if code is None:return None
        log.close();jobs[name].update(exit_code=code,status='complete' if code==0 else 'failed',seconds=time.monotonic()-t)
        save();return code

    job=launch('prepare','run_compensated_recycle.py',['--mode','preflight'],0)
    while (code:=finish('prepare',job,5400)) is None:time.sleep(5)
    if code:
        state['phase']='closed_preflight_failure';save();return
    assert json.loads((root/'compensation_preflight.json').read_text())['complete']
    state['phase']='training_and_scoring'
    active={}
    for hip,seed in enumerate(lock['seeds']):
        name=f'train_{seed}'
        active[name]=(launch(name,'run_compensated_recycle.py',['--mode','train','--seed',str(seed)],hip),'train',seed)
    while active:
        for name,(job,phase,seed) in list(active.items()):
            code=finish(name,job,21600 if phase=='train' else 7200)
            if code is None:continue
            del active[name]
            if code==0 and phase=='train':
                new=f'score_{seed}'
                active[new]=(launch(new,'audit_compensated_recycle.py',['--mode','score','--seed',str(seed)]),'score',seed)
        if active:time.sleep(5)
    if any(j['status']=='failed' for j in jobs.values()):
        state['phase']='closed_run_failure';save();return
    state['phase']='serial_replay_timing';save()
    for seed in lock['seeds']:
        name=f'replay_{seed}'
        job=launch(name,'audit_compensated_recycle.py',['--mode','replay','--seed',str(seed)],0)
        while (code:=finish(name,job,1800)) is None:time.sleep(5)
        if code:
            state['phase']='closed_replay_failure';save();return
    state.update(phase='closed',complete=True);save()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    control_compensation(p.parse_args().root)
