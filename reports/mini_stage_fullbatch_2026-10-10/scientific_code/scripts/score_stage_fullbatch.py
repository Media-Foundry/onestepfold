"""Same coordinate metrics; the final budget is full-gradient passes128."""
import argparse
import json
from pathlib import Path
from score_pair_recovery import score_pair_recovery
from fastglycan.paired_teacher_protocol import write_json


def score_stage_fullbatch(root, arm, seed):
    lock = json.loads((root/'training_lock.json').read_text())
    for step in lock['checkpoints']:
        score_pair_recovery(root, arm, seed, step, terminal_step=lock['gradient_budget'])
    write_json(root/'runs'/arm/str(seed)/'score_complete.json', dict(complete=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--arm', required=True)
    parser.add_argument('--seed', type=int, required=True)
    args = parser.parse_args()
    score_stage_fullbatch(args.root, args.arm, args.seed)
