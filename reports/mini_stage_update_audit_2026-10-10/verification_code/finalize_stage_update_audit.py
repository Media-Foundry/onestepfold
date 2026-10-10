import hashlib,json,os,subprocess,tarfile,time
from pathlib import Path

root=Path('/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/stage_update_audit_v1_20261010_integrity1')
lock=json.loads((root/'audit_lock.json').read_text())
controller_pid=json.loads((root/'launch.json').read_text())['pid']
state=dict(complete=False,phase='waiting',controller_pid=controller_pid,started_unix=time.time())
def save():
    p=root/'postprocess.tmp';p.write_text(json.dumps(state,indent=2)+'\n');p.replace(root/'postprocess.json')
save()
try:
    while True:
        status=json.loads((root/'controller.json').read_text())
        if status.get('complete'):break
        if status['phase']=='failed':raise RuntimeError('Audit controller failed; no final export allowed')
        if not Path('/proc',str(controller_pid)).exists():raise RuntimeError('Controller disappeared without verified completion')
        if time.time()>lock['deadline_unix']:raise TimeoutError('Original audit deadline reached')
        time.sleep(5)
    env=dict(os.environ,HIP_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
             PYTHONPATH=str(root/'code/src'))
    assert not any(k in env for k in ('CUDA_VISIBLE_DEVICES','ROCR_VISIBLE_DEVICES','HSA_VISIBLE_DEVICES','GPU_DEVICE_ORDINAL'))
    phases=[('verification',root/'code/scripts/verify_stage_update_audit.py'),
            ('export',root/'analysis_code/export_stage_update_audit.py')]
    for name,script in phases:
        with (root/(name+'.log')).open('x') as log:
            process=subprocess.Popen(['/home/pc/anaconda3/envs/fold/bin/python','-u',str(script),'--root',str(root)],
                env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
            state.update(phase=name,pid=process.pid);save()
            while process.poll() is None:
                if time.time()>lock['deadline_unix']:
                    process.terminate();process.wait(timeout=10);raise TimeoutError('Original deadline reached during postprocessing')
                time.sleep(5)
            if process.returncode:raise RuntimeError(f'{name} exited {process.returncode}')
    path=root/'final_export.tar.gz'
    with tarfile.open(path,'w:gz') as archive:archive.add(root/'export',arcname='export')
    info=dict(archive=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size)
    (root/'archive.json').write_text(json.dumps(info,indent=2)+'\n')
    state.update(complete=True,phase='closed',archive=info);save()
except BaseException as error:
    state.update(phase='failed',error=repr(error));save();raise
