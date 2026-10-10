import hashlib,json,shutil,tarfile,time
from pathlib import Path

parent=Path('/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding')
source=parent/'stage_pair_recovery_v1_20261010'
root=parent/'stage_update_audit_v1_20261010'
assert not root.exists(), 'Do not overwrite an existing diagnostic attempt'
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=json.loads((source/'build_lock.json').read_text())
for rel,expected in old['code'].items():assert digest(source/'code'/rel)==expected,rel
selection=json.loads(Path('/tmp/stage_update_selection.json').read_text())
for tag,path in selection['sources'].items():
    origin=Path(path);arm,seed=tag.split('_')
    assert digest(origin/'training_lock.json')==selection['training_locks'][tag]
    for step in (0,4104,8208):
        cp=origin/'runs'/arm/seed/'checkpoints'/f'{step}.pt'
        assert digest(cp)==selection['checkpoints_sha256'][f'{tag}_{step}']
root.mkdir()
shutil.copytree(source/'code',root/'code',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
with tarfile.open('/tmp/stage_update_code.tgz') as archive:
    for member in archive.getmembers():
        assert member.isfile() and not Path(member.name).is_absolute() and '..' not in Path(member.name).parts
        assert not (root/'code'/member.name).exists(), member.name
        p=root/'code'/member.name;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes(archive.extractfile(member).read())
for rel,expected in old['code'].items():assert digest(root/'code'/rel)==expected,rel
shutil.copy2(root/'code/docs/mini_stage_update_audit_v1.md',root/'protocol.md')
code={str(p.relative_to(root/'code')):digest(p) for p in sorted((root/'code').rglob('*')) if p.is_file()}
virtual_parent='/data/user/shuang886/Folding'
selection['sources']={tag:str(Path(virtual_parent)/Path(path).relative_to(parent)) for tag,path in selection['sources'].items()}
selection.update(code=code,protocol_sha256=digest(root/'protocol.md'),checkpoints=[0,4104,8208],
    fractions=[0.1,1.0],created_unix=time.time(),deadline_unix=time.time()+6*3600,
    source_build_lock_sha256=digest(source/'build_lock.json'),source_scientific_files=len(old['code']),
    selection_sha256=digest(Path('/tmp/stage_update_selection.json')),
    accepted_training_updates=0,planned_candidate_forwards=56052,planned_backwards=6804,
    planned_virtual_adam_steps=660,no_held_labels=True,no_native_or_decoder_calls=True)
(root/'audit_lock.json').write_text(json.dumps(selection,indent=2)+'\n')
(root/'source_selection.json').write_bytes(Path('/tmp/stage_update_selection.json').read_bytes())
print(json.dumps(dict(root=str(root),lock_sha256=digest(root/'audit_lock.json'),code_files=len(code),
                     verified_checkpoints=12,deadline_unix=selection['deadline_unix'])))
