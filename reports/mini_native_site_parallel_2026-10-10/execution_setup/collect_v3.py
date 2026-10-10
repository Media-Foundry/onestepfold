"""Collect terminal evidence only; never launch or resume computation."""
import hashlib
import json
from pathlib import Path
import tarfile

root = Path('/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/native_site_parallel_v3_20261010')
digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
state = json.loads((root/'controller.json').read_text())
assert state['complete'] and state['phase'] == 'complete'
assert all(job['status']=='complete' and job['exit_code']==0 for job in state['jobs'].values())
lock = json.loads((root/'audit_lock.json').read_text())
assert state['audit_lock_sha256'] == digest(root/'audit_lock.json')
assert state['verification_sha256'] == digest(root/'verification.json')
files = {}
for name in ['audit_lock.json','controller.json','launch.json','controller.log','native.log',
             'protocol.md','preflight.json','preflight.log','hardware_preflight.json',
             'verify.log','verification.json','install.py']:
    files[name] = root/name
for rank in range(6):
    path = root/f'rank_{rank}/report.json'
    report = json.loads(path.read_text()); assert report['complete']
    files[str(path.relative_to(root))] = path
for row in json.loads((root/'rank_0/report.json').read_text())['steps']:
    path = root/row['snapshot']; assert digest(path) == row['sha256']
    files[row['snapshot']] = path
for name, value in lock['code'].items():
    path = root/'code'/name; assert digest(path) == value, name
    files['code/'+name] = path
archive = Path('/tmp/native_parallel_terminal_v3_20261010.tar')
assert not archive.exists(), 'collect once; an existing artifact is not overwritten'
with tarfile.open(archive,'w') as stream:
    for name,path in sorted(files.items()): stream.add(path,arcname=name)
manifest = dict(archive_sha256=digest(archive), bytes=archive.stat().st_size,
                source_root=str(root), files={name:digest(path) for name,path in files.items()})
archive.with_suffix('.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({key:value for key,value in manifest.items() if key!='files'}))
