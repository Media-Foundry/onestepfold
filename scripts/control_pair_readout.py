"""Run four independent frozen-head diagnostics with bounded CPU scoring."""
import argparse
import json
import os
import signal
import subprocess
import time
from pathlib import Path


def control_pair_readout(root):
    virtual=Path('/data/user/shuang886/Folding')/root.name
    lock=json.loads((root/'readout_lock.json').read_text())
    prefix=['/media/IntelSSD/onestepfold/diamondhill_migration_20261001/tools/proot/usr/bin/proot',
            '-b',str(root.parent)+':/data/user/shuang886/Folding',
            '/home/pc/anaconda3/envs/fold/bin/python','-u']
    env=dict(os.environ,OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',MKL_NUM_THREADS='4',
             LAYERNORM_TYPE='torch',FASTGLYCAN_AUTHORIZED_HIP_0_5='1',
             PROTENIX_ROOT_DIR='/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime',
             PYTHONPATH=str(virtual/'code/src')+':'+str(virtual/'code/scripts'))
    assert not any(k in env for k in ('CUDA_VISIBLE_DEVICES','ROCR_VISIBLE_DEVICES','HSA_VISIBLE_DEVICES','GPU_DEVICE_ORDINAL'))
    configs=[(arm,seed) for seed in lock['seeds'] for arm in lock['arms']]
    jobs={};state=dict(complete=False,jobs={},phase='running');start=time.monotonic()
    try:
        for hip,(arm,seed) in enumerate(configs):
            key=f'fit_{arm}_{seed}';log=(root/f'{key}.log').open('x')
            command=prefix+[str(virtual/'code/scripts/run_pair_readout.py'),'--root',str(virtual),'--arm',arm,'--seed',str(seed)]
            child=subprocess.Popen(command,env=dict(env,HIP_VISIBLE_DEVICES=str(hip)),stdin=subprocess.DEVNULL,
                                   stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            jobs[key]=(child,log);state['jobs'][key]=dict(pid=child.pid,hip=hip,status='running')
        while True:
            for key,(child,_) in list(jobs.items()):
                code=child.poll()
                if code is not None:
                    state['jobs'][key].update(status='complete' if code==0 else 'failed',exit_code=code)
                    if code:raise RuntimeError(f'{key} exited {code}')
            for arm,seed in configs:
                key=f'score_{arm}_{seed}'
                if key in jobs or state['jobs'][f'fit_{arm}_{seed}']['status']!='complete':continue
                log=(root/f'{key}.log').open('x')
                command=prefix+[str(virtual/'code/scripts/score_pair_readout.py'),'--root',str(virtual),'--arm',arm,'--seed',str(seed)]
                child=subprocess.Popen(command,env=dict(env,HIP_VISIBLE_DEVICES='4'),stdin=subprocess.DEVNULL,
                                       stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                jobs[key]=(child,log);state['jobs'][key]=dict(pid=child.pid,status='running',kind='cpu_score')
            state['seconds']=time.monotonic()-start
            if len(jobs)==8 and all(p.poll()==0 for p,_ in jobs.values()):break
            if state['seconds']>6*3600:raise TimeoutError('fixed six-hour limit')
            temp=root/'controller.tmp';temp.write_text(json.dumps(state,indent=2)+'\n');temp.replace(root/'controller.json')
            time.sleep(5)
        for arm,seed in configs:
            assert json.loads((root/'runs'/arm/str(seed)/'summary.json').read_text())['complete']
        state.update(complete=True,phase='closed')
    except BaseException as exc:
        state.update(phase='failed',error=repr(exc))
        for p,_ in jobs.values():
            if p.poll() is None:os.killpg(p.pid,signal.SIGTERM)
        raise
    finally:
        for _,f in jobs.values():f.close()
        state['seconds']=time.monotonic()-start
        (root/'controller.json').write_text(json.dumps(state,indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True)
    control_pair_readout(parser.parse_args().root)
