"""Export closed stage-aligned trials, without bulk conditioning or coordinates."""
import argparse,hashlib,json,shutil
from pathlib import Path


def export_stage_recovery(root):
    assert json.loads((root/'controller.json').read_text())['complete']
    dest=root/'export';dest.mkdir(exist_ok=False);files={}
    def copy(path,name):
        target=dest/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
        digest=hashlib.sha256(path.read_bytes()).hexdigest();assert hashlib.sha256(target.read_bytes()).hexdigest()==digest
        files[name]=digest
    for name in ('build_lock.json','protocol.md','controller.json','controller.log','preflight_tests.log','stage_manifest.json'):
        copy(root/name,name)
    for shard in range(4):copy(root/f'cache_{shard}.json',f'cache_{shard}.json')
    for path in sorted(root.glob('*.log')):
        if path.name not in files:copy(path,path.name)
    for path in sorted((root/'verification_code').glob('*.py')):
        copy(path,'verification_code/'+path.name)
    for cohort in ('n1','n15'):
        lock=json.loads((root/cohort/'training_lock.json').read_text())
        copy(root/cohort/'training_lock.json',f'{cohort}/training_lock.json')
        for arm in lock['arms']:
            for seed in lock['seeds']:
                relative=Path(cohort)/'runs'/arm/str(seed);folder=root/relative
                assert json.loads((folder/'tensor_verification.json').read_text())['complete']
                for name in ('report.json','history.jsonl','score_complete.json','tensor_verification.json'):
                    copy(folder/name,str(relative/name))
                for step in lock['checkpoints']:
                    for name in (f'evaluation_{step}.json',f'summary_{step}.json',f'scores_{step}.json.gz'):
                        copy(folder/name,str(relative/name))
    (dest/'manifest.json').write_text(json.dumps(dict(source=str(root),files=files),indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(files=len(files),bytes=sum((dest/n).stat().st_size for n in files))))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    export_stage_recovery(p.parse_args().root)
