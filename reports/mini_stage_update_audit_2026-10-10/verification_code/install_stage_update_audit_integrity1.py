import hashlib,json,tarfile,time
from pathlib import Path

parent=Path('/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding')
source=parent/'stage_pair_recovery_v1_20261010'
failed=parent/'stage_update_audit_v1_20261010'
root=parent/'stage_update_audit_v1_20261010_integrity1'
assert not root.exists()
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
failure=json.loads((failed/'controller.json').read_text())
assert failure['phase']=='failed'
for job in failure['jobs']:
    assert not Path('/proc',str(job['pid'])).exists()
    log=failed/f"audit_{job['arm']}_{job['seed']}.log"
    assert 'AssertionError: tests/.pytest_cache/v/cache/nodeids' in log.read_text()
assert not (failed/'runs').exists(), 'Failure must precede runtime/model construction'
old=json.loads((source/'build_lock.json').read_text())
selection=json.loads(Path('/tmp/stage_update_selection.json').read_text())
for tag,path in selection['sources'].items():
    origin=Path(path);arm,seed=tag.split('_')
    assert digest(origin/'training_lock.json')==selection['training_locks'][tag]
    for step in (0,4104,8208):
        assert digest(origin/'runs'/arm/seed/'checkpoints'/f'{step}.pt')==selection['checkpoints_sha256'][f'{tag}_{step}']
root.mkdir();(root/'code').mkdir()
# Copy only the825 declared scientific source files, never pytest/bytecode caches.
for rel,expected in old['code'].items():
    src=source/'code'/rel;assert digest(src)==expected
    dst=root/'code'/rel;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(src.read_bytes())
overlay=[]
with tarfile.open('/tmp/stage_update_code.tgz') as archive:
    for member in archive.getmembers():
        assert member.isfile() and not Path(member.name).is_absolute() and '..' not in Path(member.name).parts
        assert not (root/'code'/member.name).exists()
        p=root/'code'/member.name;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes(archive.extractfile(member).read());overlay.append(member.name)
        assert digest(p)==digest(failed/'code'/member.name), 'Audit implementation must remain unchanged'
(root/'protocol.md').write_bytes((root/'code/docs/mini_stage_update_audit_v1.md').read_bytes())
code={rel:digest(root/'code'/rel) for rel in sorted(list(old['code'])+overlay)}
assert len(code)==831
selection['sources']={tag:str(Path('/data/user/shuang886/Folding')/Path(path).relative_to(parent)) for tag,path in selection['sources'].items()}
selection.update(code=code,protocol_sha256=digest(root/'protocol.md'),checkpoints=[0,4104,8208],fractions=[0.1,1.0],
    created_unix=time.time(),deadline_unix=failure['deadline_unix'],
    source_build_lock_sha256=digest(source/'build_lock.json'),source_scientific_files=len(old['code']),
    selection_sha256=digest(Path('/tmp/stage_update_selection.json')),accepted_training_updates=0,
    planned_candidate_forwards=56052,planned_backwards=6804,planned_virtual_adam_steps=660,
    no_held_labels=True,no_native_or_decoder_calls=True,
    integrity_failure=dict(root=str(failed),controller_sha256=digest(failed/'controller.json'),
        cause='pytest cache incorrectly included in initial source manifest; test run changed cache',
        model_constructed=False,candidate_forwards=0,backwards=0,virtual_steps=0,
        correction='Copy only original825 declared source files and unchanged6-file overlay; exclude derived caches',
        original_deadline_retained=True))
(root/'audit_lock.json').write_text(json.dumps(selection,indent=2)+'\n')
(root/'source_selection.json').write_bytes(Path('/tmp/stage_update_selection.json').read_bytes())
print(json.dumps(dict(root=str(root),lock_sha256=digest(root/'audit_lock.json'),code_files=len(code),deadline_unix=selection['deadline_unix'])))
