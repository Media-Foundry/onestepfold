"""Independently reconstruct full-field residual statistics from saved tensors."""
import argparse
import json
import math
from pathlib import Path
import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.pair_recovery_data import PairRecoveryData


def verify_saved_pair_fit(root):
    torch.set_num_threads(2)
    lock = json.loads((root / 'training_lock.json').read_text())
    data = PairRecoveryData(lock['build_root'], lock['cache_manifest_sha256'])
    checked = []
    for arm in lock['arms']:
        for seed in lock['seeds']:
            folder = root / 'runs' / arm / str(seed)
            for step in lock['checkpoints']:
                ev = json.loads((folder / f'evaluation_{step}.json').read_text())
                assert sha256(folder / ev['residual_file']) == ev['residual_sha256']
                residuals = torch.load(folder / ev['residual_file'], map_location='cpu', weights_only=False)
                predictions, targets = [], []
                for aa, p in residuals.items():
                    label = f'p3_s37_{aa}'
                    rec = data.records[label]
                    bp = data.root / rec['path']; tp = Path(rec['target_path'])
                    assert sha256(bp) == rec['sha256'] and sha256(tp) == rec['target_sha256']
                    base = torch.load(bp, map_location='cpu', weights_only=False)['base'][2]
                    target = torch.load(tp, map_location='cpu', weights_only=False)['conditioning'][2]
                    predictions.append(p.double()); targets.append((target - base).double())
                p, t = torch.stack(predictions), torch.stack(targets)
                components = {'raw': (p, t), 'common': (p.mean(0, keepdim=True), t.mean(0, keepdim=True)),
                              'centered': (p - p.mean(0), t - t.mean(0))}
                for kind, (x, y) in components.items():
                    n = len(x)
                    pp, tt = float(x.square().sum()) / n, float(y.square().sum()) / n
                    err, dot = float((x - y).square().sum()) / n, float((x * y).sum()) / n
                    actual = dict(target_energy=tt, predicted_energy=pp, error_energy=err,
                                  nmse=err/tt, energy_ratio=pp/tt,
                                  cosine=dot/math.sqrt(pp*tt) if pp > 1e-24 else None)
                    recorded = ev['latent'][0]['moments'][kind]
                    for key, value in actual.items():
                        if value is None: assert recorded[key] is None
                        else: assert math.isclose(value, recorded[key], rel_tol=2e-8, abs_tol=1e-8), (arm, seed, step, kind, key)
                checked.append(dict(arm=arm, seed=seed, step=step, candidates=19, shape=list(p.shape)))
    write_json(root / 'tensor_verification.json', dict(complete=True, checked=checked, full_field=True,
                                                     method='FP64 direct stacked subtraction, independent of ResponseMoments'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--root', type=Path, required=True)
    verify_saved_pair_fit(parser.parse_args().root)
