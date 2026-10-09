"""Snapshot the unchanged model and lock a fresh single-site fitting diagnostic."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path


def prepare_candidate_fit(root, incoming):
    source = root.parent / 'pair_recovery_v1b_20261009'
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    old = json.loads((source / 'training_lock.json').read_text())
    assert json.loads((source / 'controller.json').read_text())['complete']
    for name, value in old['code'].items():
        assert digest(source / 'code' / name) == value, name
    assert not root.exists()
    root.mkdir()
    shutil.copytree(source / 'code', root / 'code')
    additions = [
        'src/fastglycan/pair_candidate_fit.py', 'scripts/run_pair_candidate_fit.py',
        'scripts/prepare_pair_candidate_fit.py', 'scripts/control_pair_candidate_fit.py',
        'scripts/score_pair_candidate_fit.py', 'scripts/score_pair_recovery.py',
        'scripts/export_pair_candidate_fit.py', 'scripts/verify_pair_candidate_fit_remote.py',
        'tests/test_pair_candidate_fit.py', 'tests/test_pair_recovery.py', 'tests/test_response_moments.py',
    ]
    for name in additions:
        dest = root / 'code' / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(incoming / name, dest)
    shutil.copy2(incoming / 'docs/mini_pair_candidate_fit_v1.md', root / 'protocol.md')
    assert digest(root / 'code/src/fastglycan/models/pair_recovery.py') == digest(
        incoming / 'src/fastglycan/models/pair_recovery.py')
    lock = dict(old)
    virtual_source = str(Path(old['build_root']).parent / source.name)
    lock.update(version='candidate_fit_v1b', repository_commit='4625c230f2ff9a09d95b30324409b38621cc8324',
                source_training_root=virtual_source, source_lock_sha256=digest(source / 'training_lock.json'),
                train_sites=['p3_s37'], checkpoints=[0, 304, 1216, 4104, 8208],
                exposure_per_candidate=[0, 32, 128, 432, 864],
                code={str(p.relative_to(root / 'code')): digest(p) for p in sorted((root / 'code').rglob('*.py'))},
                protocol_sha256=digest(root / 'protocol.md'),
                planned_s1=912, planned_updates=32832, planned_training_forwards=65664,
                independent_confirmation=False, no_native_recycle=True, no_new_inputs=True)
    assert lock['updates'] == 8208 and lock['lr'] == 1e-4
    assert lock['arms'] == ['pretrained', 'random'] and lock['seeds'] == [272001, 272003]
    (root / 'training_lock.json').write_text(json.dumps(lock, indent=2, sort_keys=True) + '\n')
    print(json.dumps(dict(root=str(root), lock_sha256=digest(root / 'training_lock.json'))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--incoming', type=Path, required=True)
    args = parser.parse_args()
    prepare_candidate_fit(args.root, args.incoming)
