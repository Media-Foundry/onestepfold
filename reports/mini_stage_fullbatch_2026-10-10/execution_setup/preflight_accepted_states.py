"""CPU checkpoint/log binding only; no model forward, gradient or optimization."""
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import torch

root = Path('/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/stage_fullbatch_v1_20261010')
read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
lock = read(root / 'training_lock.json')
post = read(root / 'postprocess_lock.json')
source = root / 'postprocess_code/fullbatch_results.py'
assert sha(source) == post['files']['fullbatch_results.py']
spec = importlib.util.spec_from_file_location('frozen_result_checks', source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
rows = []
for seed in (272001, 272003):
    folder = root / 'runs/lbfgs' / str(seed)
    report = read(folder / 'report.json')
    assert report['complete'] and report['gradient_passes'] == 128
    assert sha(folder / 'history.jsonl') == report['history_sha256']
    history = [json.loads(x) for x in (folder / 'history.jsonl').read_text().splitlines()]
    gradients = [r for r in history if r['kind'] == 'gradient']
    objectives = []
    for step in lock['checkpoints']:
        ev = read(folder / f'evaluation_{step}.json')
        path = folder / ev['checkpoint']
        assert sha(path) == ev['sha256']
        checkpoint = torch.load(path, map_location='cpu', weights_only=False)
        state = checkpoint['state_dict']
        # Initial equality to the parameter-only training digest verifies this
        # native suffix has no extra state-dict tensors/aliases in this layout.
        assert len(state) == len(checkpoint['optimizer']['param_groups'][0]['params'])
        digest = hashlib.sha256()
        for value in state.values():
            assert value.dtype == torch.float32 and value.device.type == 'cpu'
            digest.update(value.contiguous().numpy().tobytes())
        digest = digest.hexdigest()
        if step == 0:
            assert digest == gradients[0]['parameter_sha256']
        matches = [g for g in gradients if g['parameter_sha256'] == digest]
        assert matches and len({g['raw'] for g in matches}) == 1
        objectives.append(dict(step=step, parameter_sha256=digest, objective=matches[0]['raw']))
        del checkpoint, state
    ledger = module.verify_fullbatch_history(history, lock, report, objectives)
    rows.append(dict(seed=seed, checkpoints=objectives,
                     evaluations=ledger['evaluations'], changed_updates=ledger['changed_updates'],
                     status_counts=ledger['status_counts'],
                     final_accepted_loss=ledger['accepted_states'][-1]['after']))
result = dict(complete=True, observed_unix=time.time(), rows=rows,
              model_forwards=0, model_backwards=0, new_parameter_updates=0,
              checkpoint_bytes_bound_to_log=True, independent_objective_recomputed=False,
              full_tensor_verification_still_required=True,
              result_module_sha256=sha(source), training_lock_sha256=sha(root / 'training_lock.json'))
with (root / 'postprocess_accepted_state_preflight.json').open('x') as f:
    json.dump(result, f, indent=2)
    f.write('\n')
print(json.dumps(result, indent=2))
