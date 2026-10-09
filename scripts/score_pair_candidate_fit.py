"""Reuse unchanged coordinate metrics, without one-protein bootstrap intervals."""
import argparse
import json
from pathlib import Path
from score_pair_recovery import score_pair_recovery


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--arm', choices=['pretrained', 'random'], required=True)
    parser.add_argument('--seed', type=int, required=True)
    args = parser.parse_args()
    lock = json.loads((args.root / 'training_lock.json').read_text())
    for step in lock['checkpoints']:
        score_pair_recovery(args.root, args.arm, args.seed, step,
                            site_keys=lock['train_sites'], paired_intervals=False)
    (args.root / 'runs' / args.arm / str(args.seed) / 'score_complete.json').write_text(
        json.dumps(dict(complete=True, steps=lock['checkpoints'])) + '\n')
