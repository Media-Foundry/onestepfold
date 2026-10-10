"""One bounded Mini reference-anchor audit; failures are retained, never retried."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def control_reference_anchor_audit(root):
    read=lambda p:json.loads(p.read_text())
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    lock=read(root/'audit_lock.json')
    assert sha(root/'protocol.md')==lock['protocol_sha256']
    for name,digest in lock['code'].items():assert sha(root/'code'/name)==digest,name
    virtual=Path('/data/user/shuang886/Folding')/root.name
    prefix=['/media/IntelSSD/onestepfold/diamondhill_migration_20261001/tools/proot/usr/bin/proot',
        '-b',str(root.parent)+':/data/user/shuang886/Folding','/home/pc/anaconda3/envs/fold/bin/python','-u']
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
        PYTHONDONTWRITEBYTECODE='1',LAYERNORM_TYPE='torch',FASTGLYCAN_AUTHORIZED_HIP_0_5='1',
        PROTENIX_ROOT_DIR='/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime',
        PYTHONPATH=str(virtual/'code/src')+':'+str(virtual/'code/scripts'))
    assert not any(k in env for k in ('CUDA_VISIBLE_DEVICES','ROCR_VISIBLE_DEVICES','HSA_VISIBLE_DEVICES','GPU_DEVICE_ORDINAL'))
    state=dict(complete=False,phase='tests',started_unix=time.time(),lock_sha256=sha(root/'audit_lock.json'))
    def save():
        state['observed_unix']=time.time();p=root/'controller.tmp'
        p.write_text(json.dumps(state,indent=2)+'\n');p.replace(root/'controller.json')
    save();process=None
    try:
        with (root/'tests.log').open('x') as output:
            subprocess.run(prefix+['-m','pytest','-q','-p','no:cacheprovider',
                str(virtual/'code/tests/test_anchored_pair_recovery.py'),
                str(virtual/'code/tests/test_stage_pair_recovery.py')],env=dict(env,HIP_VISIBLE_DEVICES=''),
                stdout=output,stderr=subprocess.STDOUT,check=True,timeout=180)
        with (root/'imports.log').open('x') as output:
            subprocess.run(prefix+['-c','import audit_reference_anchor'],env=dict(env,HIP_VISIBLE_DEVICES=''),
                stdout=output,stderr=subprocess.STDOUT,check=True,timeout=120)
        with (root/'audit.log').open('x') as output:
            process=subprocess.Popen(prefix+[str(virtual/'code/scripts/audit_reference_anchor.py'),
                '--root',str(virtual)],env=dict(env,HIP_VISIBLE_DEVICES='4'),stdin=subprocess.DEVNULL,
                stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
            state.update(phase='audit',pid=process.pid,hip=4,deadline_unix=time.time()+7200);save()
            while process.poll() is None:
                if time.time()>state['deadline_unix']:
                    state['timeout']=True;os.killpg(process.pid,signal.SIGTERM)
                    try:process.wait(timeout=30)
                    except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL)
                    break
                save();time.sleep(5)
            code=process.wait();state['exit_code']=code
        if code!=0:raise RuntimeError('audit failed; preserve this attempt')
        report=read(root/'report.json');assert report['complete'] and report['parameter_updates']==0
        for name,digest in lock['code'].items():assert sha(root/'code'/name)==digest,name
        state.update(complete=True,phase='closed',report_sha256=sha(root/'report.json'))
    except BaseException as error:
        state.update(phase='failed',error=repr(error))
        if process is not None and process.poll() is None:os.killpg(process.pid,signal.SIGTERM)
        raise
    finally:save()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True)
    control_reference_anchor_audit(parser.parse_args().root)
