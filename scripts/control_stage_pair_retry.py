"""One fixed-code operational retry, preserving the original absolute deadline."""
import argparse,hashlib,json,os,signal,subprocess,time
from pathlib import Path


def control_stage_retry(root):
    begin=time.monotonic();record=json.loads((root/'runtime_recovery_lock.json').read_text())
    assert json.loads((root/'controller.json').read_text())['phase']=='failed'
    retry=root/'runtime_retry_v1';virtual=Path('/data/user/shuang886/Folding')/root.name
    for name,digest in json.loads((root/'build_lock.json').read_text())['code'].items():
        assert hashlib.sha256((root/'code'/name).read_bytes()).hexdigest()==digest,name
    prefix=['/media/IntelSSD/onestepfold/diamondhill_migration_20261001/tools/proot/usr/bin/proot',
            '-b',str(root.parent)+':/data/user/shuang886/Folding','/home/pc/anaconda3/envs/fold/bin/python','-u']
    env=dict(os.environ,HIP_VISIBLE_DEVICES='0',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
             LAYERNORM_TYPE='torch',FASTGLYCAN_AUTHORIZED_HIP_0_5='1',
             PROTENIX_ROOT_DIR='/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime',
             PYTHONPATH=str(virtual/'code/src')+':'+str(virtual/'code/scripts'),
             FASTGLYCAN_LOCKED_STAGE_SCRIPT=str(virtual/'code/scripts/run_stage_pair_recovery.py'),
             FASTGLYCAN_RUNTIME_STACK_LOG=str(virtual/'runtime_retry_v1/python_stack.log'))
    assert not any(k in env for k in ('CUDA_VISIBLE_DEVICES','ROCR_VISIBLE_DEVICES','HSA_VISIBLE_DEVICES','GPU_DEVICE_ORDINAL'))
    state=dict(complete=False,phase='starting',source_provider=str(retry),jobs={},one_retry_only=True,
               deadline_unix=record['deadline_unix'],recovery_lock_sha256=hashlib.sha256((root/'runtime_recovery_lock.json').read_bytes()).hexdigest())
    def save():
        state['seconds']=time.monotonic()-begin
        p=root/'execution_recovery.tmp';p.write_text(json.dumps(state,indent=2)+'\n');p.replace(root/'execution_recovery.json')
    jobs=[('train',virtual/'verification_code/observe_stage_retry.py'),
          ('score',virtual/'code/scripts/score_stage_pair_recovery.py'),
          ('verify',virtual/'verification_code/verify_stage_pair_recovery.py')]
    try:
        for key,script in jobs:
            state['phase']=key;save()
            with (root/f'operational_retry_{key}.log').open('x') as out:
                p=subprocess.Popen(prefix+[str(script),'--root',str(virtual/'runtime_retry_v1'),'--arm','final','--seed','272003'],
                    env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
                state['jobs'][key]=dict(pid=p.pid,status='running',hip=0);save()
                while p.poll() is None:
                    if time.time()>record['deadline_unix']:
                        os.killpg(p.pid,signal.SIGTERM)
                        try:p.wait(timeout=10)
                        except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
                        raise TimeoutError('original absolute n15 deadline reached')
                    time.sleep(5)
                state['jobs'][key].update(status='complete' if p.returncode==0 else 'failed',exit_code=p.returncode);save()
                if p.returncode:raise RuntimeError(f'operational retry {key} exited {p.returncode}')
        state.update(complete=True,phase='closed')
    except BaseException as error:
        state.update(phase='failed',error=repr(error));raise
    finally:save()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    control_stage_retry(p.parse_args().root)
