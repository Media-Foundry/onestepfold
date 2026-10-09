"""Immutable source snapshot for native-stage-aligned recovery trials."""
import argparse,hashlib,json,shutil
from pathlib import Path


def prepare_stage_recovery(root,incoming):
    old_root=root.parent/'pair_recovery_v1b_20261009'
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    old=json.loads((old_root/'training_lock.json').read_text())
    assert json.loads((old_root/'controller.json').read_text())['complete'] and not root.exists()
    for name,value in old['code'].items():assert digest(old_root/'code'/name)==value,name
    root.mkdir();shutil.copytree(old_root/'code',root/'code')
    files=['src/fastglycan/models/stage_pair_recovery.py','src/fastglycan/stage_pair_data.py',
           'src/fastglycan/pair_candidate_fit.py','scripts/score_pair_recovery.py',
           'tests/test_stage_pair_recovery.py','tests/test_pair_recovery.py','tests/test_response_moments.py']
    files += [str(p.relative_to(incoming)) for p in (incoming/'scripts').glob('*stage_pair*.py')]
    for name in files:
        dst=root/'code'/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(incoming/name,dst)
    shutil.copy2(incoming/'docs/mini_stage_pair_recovery_v1.md',root/'protocol.md')
    lock=dict(old)
    lock.update(repository_commit='981076f41042685b09ef7ebccf5a2f8aa86e15c7',version='stage_pair_v1',
                source_training_root=str(Path(old['build_root']).parent/old_root.name),
                source_lock_sha256=digest(old_root/'training_lock.json'),
                protocol_sha256=digest(root/'protocol.md'),arms=['final','hint'],cohorts=['n1','n15'],
                code={str(p.relative_to(root/'code')):digest(p) for p in sorted((root/'code').rglob('*.py'))},
                planned_cache_recycles=2964,planned_s1=31920,planned_updates=65664)
    (root/'build_lock.json').write_text(json.dumps(lock,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(root=str(root),lock_sha256=digest(root/'build_lock.json'))))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--incoming',type=Path,required=True)
    a=p.parse_args();prepare_stage_recovery(a.root,a.incoming)
