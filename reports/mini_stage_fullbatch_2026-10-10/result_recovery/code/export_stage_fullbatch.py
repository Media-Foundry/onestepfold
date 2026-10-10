"""Export a fully closed batch without changing its frozen scientific source."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

from fastglycan.fullbatch_recovery import verify_fullbatch_completion


def export_stage_fullbatch(root):
    root = Path(root).resolve()
    read = lambda path: json.loads(path.read_text())
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    lock = read(root / 'training_lock.json')
    controller = read(root / 'controller.json')
    recovered = verify_fullbatch_completion(root)
    assert controller['lock_sha256'] == sha(root / 'training_lock.json')
    assert lock['arms'] == ['adamw', 'lbfgs'] and lock['seeds'] == [272001, 272003]
    assert lock['checkpoints'] == [0, 32, 128] and lock['gradient_budget'] == 128
    assert sha(root / 'protocol.md') == lock['protocol_sha256']
    assert sha(root / 'source_selection.json') == lock['source_selection_sha256']
    for name, digest in lock['code'].items():
        assert sha(root / 'code' / name) == digest, name

    # Runtime paths are virtualized by proot; all sources are siblings here.
    stage = root.parent / Path(lock['stage_root']).name
    assert sha(stage / 'stage_manifest.json') == lock['stage_manifest_sha256']
    assert sha(stage / 'n15/training_lock.json') == lock['source_training_lock_sha256']
    wanted = {name: root / name for name in (
        'training_lock.json', 'protocol.md', 'source_selection.json',
        'controller.json', 'controller.log', 'preflight_tests.log', 'prelock_tests.log')}
    wanted.update({p.name: p for p in root.glob('*.log') if not p.name.startswith('postprocess')})
    if recovered:
        recovery = root / 'verification_recovery'
        recovery_lock = read(recovery / 'lock.json')
        wanted.update({n: root / n for n in recovery_lock['protected_files']})
        wanted.update({str(p.relative_to(root)): p for p in recovery.rglob('*') if p.is_file()})
    wanted['source_stage_manifest.json'] = stage / 'stage_manifest.json'
    wanted['source_training_lock.json'] = stage / 'n15/training_lock.json'
    wanted['controls/scores_8208.json.gz'] = stage / 'n15/runs/final/272001/scores_8208.json.gz'
    selected = read(root / 'source_selection.json')['overlay'] + [
        'src/fastglycan/models/stage_pair_recovery.py',
        'src/fastglycan/reference_editor_metrics.py',
        'src/fastglycan/response_moments.py', 'scripts/verify_stage_pair_recovery.py']
    for name in selected:
        if recovered and name == 'scripts/verify_stage_pair_recovery.py':
            wanted['scientific_code/' + name] = root / 'verification_recovery/code/verify_stage_pair_recovery.py'
        else:
            wanted['scientific_code/' + name] = root / 'code' / name
    for arm in lock['arms']:
        for seed in lock['seeds']:
            relative = Path('runs') / arm / str(seed)
            folder = root / relative
            report = read(folder / 'report.json')
            assert report['complete'] and report['checkpoints'] == lock['checkpoints']
            assert report['gradient_passes'] == 128
            assert report['training_lock_sha256'] == controller['lock_sha256']
            assert read(folder / 'score_complete.json')['complete']
            tensor = read(folder / 'tensor_verification.json')
            assert tensor['complete'] and tensor['feature_forwards'] == 2736
            assert len(tensor['checks']) == 144
            for name in ('report.json', 'history.jsonl', 'score_complete.json', 'tensor_verification.json'):
                wanted[str(relative / name)] = folder / name
            for step in lock['checkpoints']:
                for name in (f'evaluation_{step}.json', f'summary_{step}.json', f'scores_{step}.json.gz'):
                    wanted[str(relative / name)] = folder / name
                ev = read(folder / f'evaluation_{step}.json')
                assert ev['complete'] and ev['gradient_passes'] == step
                assert sha(folder / ev['checkpoint']) == ev['sha256']
                for prediction in ev['predictions']:
                    assert sha(folder / prediction['path']) == prediction['sha256']
                summary = read(folder / f'summary_{step}.json')
                assert summary['complete'] and summary['step'] == step
                assert summary['evaluation_sha256'] == sha(folder / f'evaluation_{step}.json')
    # Validate everything before creating a success-looking export directory.
    digests = {name: sha(path) for name, path in wanted.items()}
    dest, partial = root / 'export', root / 'export.partial'
    if dest.exists() or partial.exists():
        raise FileExistsError('preserve existing export; no automatic replacement')
    partial.mkdir()
    for name, path in wanted.items():
        target = partial / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        assert sha(target) == digests[name]
    manifest = dict(source=str(root), files=digests, scientific_experiment_complete=True,
                    source_snapshot_verified=len(lock['code']), operational_recovery=recovered,
                    exporter_sha256=sha(Path(__file__)), bulk_tensors_exported=False)
    (partial / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    partial.rename(dest)
    print(json.dumps(dict(files=len(digests), bytes=sum((dest / n).stat().st_size for n in digests))))
    return dest


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    export_stage_fullbatch(parser.parse_args().root)
