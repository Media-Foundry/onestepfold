"""Finite boundary/identity preparation; never start training on a failed gate."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def control_pair_placement_gate(root):
    lock=json.loads((root/'training_lock.json').read_text())
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    for name,value in lock['code'].items():assert digest(root/'code'/name)==value,name
    assert digest(root/'protocol.md')==lock['protocol_sha256']
    virtual=lock['virtual_root'];prefix=[lock['proot'],'-b',lock['bind_source']+':'+lock['bind_target'],lock['python'],'-u']
    env=dict(os.environ,FASTGLYCAN_AUTHORIZED_HIP_0_5='1',LAYERNORM_TYPE='torch',
        PROTENIX_ROOT_DIR=lock['protenix_root_dir'],PYTHONPATH=virtual+'/code/src:'+virtual+'/code/scripts',
        OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    assert not any(k in env for k in ('CUDA_VISIBLE_DEVICES','ROCR_VISIBLE_DEVICES','HSA_VISIBLE_DEVICES','GPU_DEVICE_ORDINAL'))
    state=dict(complete=False,phase='reference',started_unix=time.time(),jobs={},lock_sha256=digest(root/'training_lock.json'))
    deadline=state['started_unix']+1800;jobs={}

    def save():
        state['observed_unix']=time.time();p=root/'controller.tmp'
        p.write_text(json.dumps(state,indent=2)+'\n');p.replace(root/'controller.json')

    def launch(shard,hip):
        out=(root/f'gate_{shard}.log').open('x')
        command=prefix+[virtual+'/code/scripts/build_pair_placement.py','--root',virtual,'--shard',str(shard)]
        process=subprocess.Popen(command,env=dict(env,HIP_VISIBLE_DEVICES=str(hip)),stdin=subprocess.DEVNULL,
            stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
        jobs[shard]=(process,out);state['jobs'][str(shard)]=dict(pid=process.pid,hip=hip,status='running');save()

    def wait(shards):
        while True:
            for shard in shards:
                code=jobs[shard][0].poll()
                if code is not None:
                    state['jobs'][str(shard)].update(status='complete' if code==0 else 'failed',exit_code=code)
                    if code:raise RuntimeError(f'gate {shard} failed; no restart')
            save()
            if all(jobs[s][0].poll() is not None for s in shards):return
            if time.time()>deadline:raise TimeoutError('finite gate expired')
            time.sleep(5)

    try:
        launch(-1,0);wait([-1]);state['phase']='candidates'
        for shard in range(6):launch(shard,shard)
        wait(range(6))
        reports=[json.loads((root/f'boundary_gate_{s}/report.json').read_text()) for s in range(6)]
        ref=json.loads((root/'reference_gate/report.json').read_text())
        assert ref['complete'] and all(r['complete'] for r in reports)
        candidates=[r for report in reports for r in report['records']]
        assert len(candidates)==len({r['label'] for r in candidates})==912
        assert all(r['initial_hashes']==ref['initial_hashes'] and r['frozen_digest']==ref['frozen_digest'] for r in reports)
        for record in candidates+ref['records']:assert digest(root/record['path'])==record['sha256']
        manifest=dict(complete=True,candidates=candidates,references=ref['records'],
            initial_hashes=ref['initial_hashes'],frozen_digest=ref['frozen_digest'],native_recycles=936,
            candidate_identities=3648,reference_identities=192,training_started=False,
            lock_sha256=digest(root/'training_lock.json'))
        (root/'boundary_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        state.update(complete=True,phase='complete',manifest_sha256=digest(root/'boundary_manifest.json'))
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
    control_pair_placement_gate(p.parse_args().root)
