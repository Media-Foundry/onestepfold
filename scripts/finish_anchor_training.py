"""Read-only follower: export and verify when all six existing jobs succeed."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
import time

from export_anchor_training import export_anchor_training
from fastglycan.anchor_results import analyze_anchor_results, verify_anchor_results


def finish_anchor_training(root):
    root=Path(root).resolve();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    lock=json.loads((root/'postprocess_lock.json').read_text())
    assert sha(root/'training_lock.json')==lock['training_lock_sha256']
    for name,digest in lock['files'].items():assert sha(root/'postprocess_code'/name)==digest,name
    status=dict(complete=False,phase='waiting',started_unix=time.time(),postprocess_lock_sha256=sha(root/'postprocess_lock.json'))
    def save():
        status['observed_unix']=time.time()
        p=root/'postprocess_status.tmp';p.write_text(json.dumps(status,indent=2)+'\n');p.replace(root/'postprocess_status.json')
    save()
    try:
        while True:
            state=json.loads((root/'controller.json').read_text())
            assert state['lock_sha256']==lock['training_lock_sha256']
            status['controller_phase']=state['phase'];save()
            if state['complete']:break
            if state['phase'] in ('closed_with_failures','failed'):
                raise RuntimeError('scientific controller failed; no restart or modification')
            if time.time()>lock['wait_deadline_unix']:raise TimeoutError('result wait budget expired')
            time.sleep(30)
        status['phase']='exporting';save();dest=export_anchor_training(root)
        status['phase']='verifying';save();verified=verify_anchor_results(dest)
        status['phase']='analyzing';save();analyze_anchor_results(dest)
        for name in lock['files']:
            p=dest/'postprocess_code'/name;p.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(root/'postprocess_code'/name,p)
        shutil.copy2(root/'postprocess_lock.json',dest/'postprocess_lock.json')
        generated=['manifest.json','verification.json','optimization_ledger.json','analysis.json','postprocess_lock.json']+[
            'postprocess_code/'+n for n in lock['files']]
        (dest/'postprocess_manifest.json').write_text(json.dumps(dict(complete=True,
            training_source_unchanged=True,files={n:sha(dest/n) for n in generated}),indent=2)+'\n')
        archive=root/'reference_anchor_training_export.tar.gz'
        with tarfile.open(archive,'x:gz') as tar:tar.add(dest,arcname='.')
        status.update(complete=True,phase='complete',checks=verified['checks'],archive_sha256=sha(archive),
            seconds=time.time()-status['started_unix'])
    except BaseException as error:
        status.update(phase='failed',error=repr(error));raise
    finally:save()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True)
    finish_anchor_training(parser.parse_args().root)
