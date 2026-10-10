"""Wait for the existing controller, then export and independently verify once.

This CPU-only follower never starts, stops, resumes, or modifies a training job.
Its source lives outside the frozen training tree and has a separate manifest.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tarfile
import time


def finish_stage_fullbatch(root):
    root = Path(root).resolve()
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    read = lambda path: json.loads(path.read_text())
    lock = read(root / 'postprocess_lock.json')
    assert sha(root / 'training_lock.json') == lock['training_lock_sha256']
    for name, digest in lock['files'].items():
        assert sha(root / 'postprocess_code' / name) == digest, name
    status = dict(complete=False, phase='waiting', started_unix=time.time(),
                  postprocess_lock_sha256=sha(root / 'postprocess_lock.json'))

    def save():
        status['observed_unix'] = time.time()
        path = root / 'postprocess_status.tmp'
        path.write_text(json.dumps(status, indent=2) + '\n')
        path.replace(root / 'postprocess_status.json')

    def load(name):
        path = root / 'postprocess_code' / (name + '.py')
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    save()
    try:
        while True:
            state = read(root / 'controller.json')
            assert state['lock_sha256'] == lock['training_lock_sha256']
            status['controller_phase'] = state['phase']
            save()
            if state['complete']:
                break
            if state['phase'] in ('closed_with_failures', 'failed'):
                raise RuntimeError('scientific controller failed; preserve all attempts, do not restart')
            if time.time() >= lock['wait_deadline_unix']:
                raise TimeoutError('result follower deadline; training state has not been altered')
            time.sleep(30)
        status['phase'] = 'exporting'; save()
        dest = load('export_stage_fullbatch').export_stage_fullbatch(root)
        status['phase'] = 'verifying'; save()
        module = load('fullbatch_results')
        verified = module.verify_fullbatch_results(dest)
        status['phase'] = 'analyzing'; save()
        module.analyze_fullbatch_results(dest)
        audit = dest / 'postprocess_code'
        audit.mkdir()
        for name in lock['files']:
            shutil.copy2(root / 'postprocess_code' / name, audit / name)
        shutil.copy2(root / 'postprocess_lock.json', dest / 'postprocess_lock.json')
        generated = ['manifest.json', 'verification.json', 'optimization_ledger.json',
                     'analysis.json', 'postprocess_lock.json'] + ['postprocess_code/' + n for n in lock['files']]
        (dest / 'postprocess_manifest.json').write_text(json.dumps(dict(
            complete=True, training_source_unchanged=True,
            files={n: sha(dest / n) for n in generated}), indent=2) + '\n')
        archive = root / 'fullbatch_export.tar.gz'
        with tarfile.open(archive, 'x:gz') as tar:
            tar.add(dest, arcname='.')
        status.update(complete=True, phase='complete', checks=verified['checks'],
                      archive=str(archive), archive_sha256=sha(archive),
                      seconds=time.time() - status['started_unix'])
    except BaseException as error:
        status.update(phase='failed', error=repr(error))
        raise
    finally:
        save()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    finish_stage_fullbatch(parser.parse_args().root)
