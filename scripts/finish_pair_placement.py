"""Finite result follower; never restarts or edits the original experiment."""
import argparse
import json
from pathlib import Path
import shutil
import tarfile
import time

from export_pair_placement import export_pair_placement
from fastglycan.fullbatch_results import _json, _sha
from fastglycan.placement_reporting import render_placement_results
from fastglycan.placement_results import analyze_placement_results, verify_placement_export


def finish_pair_placement(root):
    root=Path(root).resolve();lock=_json(root/'analysis_lock.json')
    for name,digest in lock['code'].items():assert _sha(root/'code'/name)==digest,name
    training,verification=Path(lock['training_root']),Path(lock['verification_root'])
    assert _sha(training/'training_lock.json')==lock['training_lock_sha256']
    assert _sha(verification/'verification_lock.json')==lock['verification_lock_sha256']
    status=dict(complete=False,phase='waiting',started_unix=time.time(),analysis_lock_sha256=_sha(root/'analysis_lock.json'))

    def save():
        status['observed_unix']=time.time();p=root/'status.tmp'
        p.write_text(json.dumps(status,indent=2)+'\n');p.replace(root/'status.json')

    save()
    try:
        while True:
            states=[_json(r/'controller.json') for r in (training,verification)]
            status['source_phases']=[s['phase'] for s in states];save()
            if any(s['phase']=='failed' for s in states):raise RuntimeError('original experiment or replay failed; no restart')
            if all(s['complete'] for s in states):break
            if time.time()>lock['wait_deadline_unix']:raise TimeoutError('finite results waiting deadline')
            time.sleep(30)
        status['phase']='exporting';save();dest=export_pair_placement(training,verification,root/'export')
        status['phase']='verifying';save();checked=verify_placement_export(dest)
        status['phase']='analyzing';save();analyze_placement_results(dest)
        status['phase']='rendering';save();render_placement_results(dest,dest/'figures')
        for name in lock['code']:
            path=dest/'analysis_code'/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/'code'/name,path)
        shutil.copy2(root/'analysis_lock.json',dest/'analysis_lock.json')
        generated=['manifest.json','verification.json','optimization_ledger.json','analysis.json','analysis_lock.json']+[
            'analysis_code/'+n for n in lock['code']]+[str(p.relative_to(dest)) for p in (dest/'figures').iterdir() if p.is_file()]
        (dest/'postprocess_manifest.json').write_text(json.dumps(dict(complete=True,
            scientific_source_unchanged=True,files={n:_sha(dest/n) for n in generated}),indent=2)+'\n')
        archive=root/'placement_results.tar.gz'
        with tarfile.open(archive,'x:gz') as tar:tar.add(dest,arcname='export')
        status.update(complete=True,phase='complete',checks=checked['checks'],archive_sha256=_sha(archive),
                      archive_bytes=archive.stat().st_size,seconds=time.time()-status['started_unix'])
    except BaseException as error:
        status.update(phase='failed',error=repr(error));raise
    finally:save()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    finish_pair_placement(p.parse_args().root)
