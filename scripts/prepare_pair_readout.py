"""Create an immutable readout-diagnostic snapshot from the closed recovery run."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path


def prepare_pair_readout(root, incoming):
    source=root.parent/'pair_recovery_v1b_20261009'
    previous=json.loads((source/'training_lock.json').read_text())
    digest=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
    assert not root.exists()
    assert json.loads((source/'controller.json').read_text())['complete']
    for name,value in previous['code'].items():assert digest(source/'code'/name)==value,name
    root.mkdir()
    shutil.copytree(source/'code',root/'code')
    additions=['src/fastglycan/pair_readout.py','scripts/run_pair_readout.py',
               'scripts/control_pair_readout.py','scripts/score_pair_readout.py',
               'scripts/prepare_pair_readout.py','tests/test_pair_readout.py']
    for name in additions:
        path=root/'code'/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(incoming/name,path)
    shutil.copy2(incoming/'docs/mini_pair_readout_v1.md',root/'protocol.md')
    code={str(p.relative_to(root/'code')):digest(p) for p in sorted((root/'code').rglob('*.py'))}
    configurations={}
    for arm in ('pretrained','random'):
        for seed in (272001,272003):
            folder=source/'runs'/arm/str(seed);ev=json.loads((folder/'evaluation_8208.json').read_text())
            assert ev['complete'] and digest(folder/ev['checkpoint'])==ev['sha256']
            configurations[f'{arm}_{seed}']=dict(path=str(Path(previous['build_root']).parent/source.name/'runs'/arm/str(seed)/ev['checkpoint']),sha256=ev['sha256'])
    lock=dict(version=1,repository_commit='31e3af3c578202d05c56d4f1e0a35480ecf2233c',
              recovery_root=str(Path(previous['build_root']).parent/source.name),source_lock_sha256=digest(source/'training_lock.json'),
              protocol_sha256=digest(root/'protocol.md'),code=code,checkpoints=configurations,
              arms=['pretrained','random'],seeds=[272001,272003],train_sites=previous['train_sites'],
              site_scale_squared=previous['site_scale_squared'],scale_floor=previous['scale_floor'],
              rcond=1e-6,chunk_rows=8192,cpu_threads=4,centered_decoder=False,
              fits=8,planned_s1=14984,planned_feature_forwards=5704,
              no_native_recycle=True,no_new_inputs=True,independent_confirmation=False)
    (root/'readout_lock.json').write_text(json.dumps(lock,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(root=str(root),lock_sha256=digest(root/'readout_lock.json'),checkpoints=configurations),indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--incoming',type=Path,required=True)
    args=parser.parse_args();prepare_pair_readout(args.root,args.incoming)
