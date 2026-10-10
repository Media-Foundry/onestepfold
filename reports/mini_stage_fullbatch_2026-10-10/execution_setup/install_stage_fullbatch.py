import hashlib
import json
from pathlib import Path
import tarfile

parent = Path('/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding')
source = parent/'stage_pair_recovery_v1_20261010'
root = parent/'stage_fullbatch_v1_20261010'
assert not root.exists()
old = json.loads((source/'build_lock.json').read_text())
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
root.mkdir(); (root/'code').mkdir()
for rel, expected in old['code'].items():
    origin = source/'code'/rel
    assert digest(origin) == expected, rel
    target = root/'code'/rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(origin.read_bytes())
overlay = []; replacements = {}
with tarfile.open('/tmp/stage_fullbatch_code.tgz') as archive:
    for member in archive.getmembers():
        assert member.isfile() and not Path(member.name).is_absolute() and '..' not in Path(member.name).parts
        target = root/'code'/member.name
        if target.exists():
            assert member.name == 'scripts/score_pair_recovery.py'
            replacements[member.name] = dict(before=digest(target))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(archive.extractfile(member).read())
        if member.name in replacements:
            replacements[member.name]['after'] = digest(target)
        overlay.append(member.name)
selection = dict(base_source=str(source), source_build_lock_sha256=digest(source/'build_lock.json'),
                 original_files=len(old['code']), overlay=overlay, replacements=replacements,
                 copied_files=sorted(set(old['code'])|set(overlay)), scientific_training_started=False)
(root/'source_selection.json').write_text(json.dumps(selection, indent=2)+'\n')
print(json.dumps(dict(root=str(root), files=len(selection['copied_files']), replacements=replacements)))
