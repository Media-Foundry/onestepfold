"""Bounded HIP-only single-worker Mini reference-editor pilot."""
import argparse
import os
import signal
import subprocess
import time
import json
from pathlib import Path


def control_reference_editor(root):
    virtual=Path('/data/user/shuang886/Folding')/root.name
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
             HIP_VISIBLE_DEVICES='0',LAYERNORM_TYPE='torch',PROTENIX_ROOT_DIR='/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime',
             PYTHONPATH=f'{virtual}/code/src:{virtual}/code/scripts')
    if any(k in env for k in ('CUDA_VISIBLE_DEVICES','ROCR_VISIBLE_DEVICES','GPU_DEVICE_ORDINAL','HSA_VISIBLE_DEVICES')):
        raise RuntimeError('conflicting inherited device selector')
    cmd=['/media/IntelSSD/onestepfold/diamondhill_migration_20261001/tools/proot/usr/bin/proot',
         '-b',str(root.parent)+':/data/user/shuang886/Folding',
         '/home/pc/anaconda3/envs/fold/bin/python','-u',str(virtual/'code/scripts/run_reference_editor.py'),'--root',str(virtual)]
    started=time.monotonic()
    with (root/'worker.log').open('w') as log:
        process=subprocess.Popen(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try: code=process.wait(timeout=2700)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGTERM)
            try: process.wait(timeout=15)
            except subprocess.TimeoutExpired: os.killpg(process.pid,signal.SIGKILL);process.wait()
            code=124
    (root/'controller.json').write_text(json.dumps(dict(complete=code==0,exit_code=code,seconds=time.monotonic()-started),indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    control_reference_editor(p.parse_args().root)
