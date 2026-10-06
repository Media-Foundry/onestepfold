"""Single-worker bounded controller for the native execution audit."""
import argparse,json,os,signal,subprocess,time
from pathlib import Path


def control_execution_profile(root):
    virtual=Path('/data/user/shuang886/Folding')/root.name
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',LAYERNORM_TYPE='torch',HIP_VISIBLE_DEVICES='0',
        PROTENIX_ROOT_DIR='/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime',PYTHONPATH=f'{virtual}/code/src:{virtual}/code/scripts')
    for k in ['CUDA_VISIBLE_DEVICES','ROCR_VISIBLE_DEVICES','GPU_DEVICE_ORDINAL','HSA_VISIBLE_DEVICES']:env.pop(k,None)
    cmd=['/media/IntelSSD/onestepfold/diamondhill_migration_20261001/tools/proot/usr/bin/proot','-b',str(root.parent)+':/data/user/shuang886/Folding',
         '/home/pc/anaconda3/envs/fold/bin/python','-u',str(virtual/'code/scripts/profile_native_execution.py'),'--root',str(virtual)]
    start=time.monotonic()
    with (root/'profile.log').open('w') as log:
        proc=subprocess.Popen(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:code=proc.wait(timeout=1800);reason=None
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGTERM)
            try:proc.wait(timeout=30)
            except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
            code=124;reason='timeout1800s'
    (root/'controller.json').write_text(json.dumps(dict(complete=code==0,exit_code=code,error=reason,seconds=time.monotonic()-start),indent=2)+'\n')
    if code:raise RuntimeError(f'profile exit{code}')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);control_execution_profile(p.parse_args().root)
