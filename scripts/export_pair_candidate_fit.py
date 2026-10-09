"""Export compact evidence; checkpoints, full residuals and coordinates stay archived."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path


def export_candidate_fit(root):
    assert json.loads((root / 'controller.json').read_text())['complete']
    assert json.loads((root / 'tensor_verification.json').read_text())['complete']
    destination = root / 'export'; destination.mkdir(exist_ok=False)
    files = {}
    def copy(source, name):
        target = destination / name; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        assert hashlib.sha256(target.read_bytes()).hexdigest() == digest
        files[name] = digest
    for name in ('training_lock.json', 'protocol.md', 'controller.json', 'controller.log',
                 'preflight_tests.log', 'tensor_verification.json'):
        copy(root / name, name)
    for path in sorted(root.glob('train_*.log')) + sorted(root.glob('score_*.log')):
        copy(path, path.name)
    failed = root.parent / 'pair_candidate_fit_v1_20261010'
    for name in ('training_lock.json', 'protocol.md', 'controller.log', 'preflight_tests.log'):
        copy(failed / name, 'failed_preflight/' + name)
    lock = json.loads((root / 'training_lock.json').read_text())
    for arm in lock['arms']:
        for seed in lock['seeds']:
            rel = Path('runs') / arm / str(seed)
            for name in ('report.json', 'history.jsonl', 'score_complete.json'):
                copy(root / rel / name, str(rel / name))
            for step in lock['checkpoints']:
                for name in (f'evaluation_{step}.json', f'summary_{step}.json', f'scores_{step}.json.gz'):
                    copy(root / rel / name, str(rel / name))
    (destination / 'manifest.json').write_text(json.dumps(dict(source=str(root), files=files), indent=2, sort_keys=True) + '\n')
    print(json.dumps(dict(files=len(files), bytes=sum((destination / n).stat().st_size for n in files))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--root', type=Path, required=True)
    export_candidate_fit(parser.parse_args().root)
