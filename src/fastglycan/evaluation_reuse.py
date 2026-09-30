"""Explicit prediction reuse and matching NFE accounting for fixed comparisons."""
from pathlib import Path


def evaluation_prediction_source(lock, row, model, seed):
    if row['role'] not in {'train', 'validation'}:
        raise ValueError('unknown evaluation role')
    reuse = lock.get('reuse_models', {}).get(model)
    if reuse is not None:
        roles = reuse.get('roles', ['train'])
        if not isinstance(roles, list) or not set(roles) <= {'train', 'validation'}:
            raise ValueError('invalid explicit reuse roles')
        if row['role'] in roles:
            return Path(reuse['root']) / row['group_id'] / f'{reuse["model"]}_seed{seed}.npy'
    if row['role']=='train' and model in {'native_s1', 'native_s2'}:
        steps = 2 if model=='native_s2' else 1
        return Path(lock['cache']) / 'examples' / row['group_id'] / f's{steps}_seed{seed}.npy'
    return None


def expected_evaluation_calls(lock, rows):
    models = lock['models']
    if len(models)!=len(set(models)):
        raise ValueError('duplicate model names')
    calls = dict(native=0, **{arm:0 for arm in lock['checkpoints']})
    for row in rows:
        seeds = lock['train_seeds'] if row['role']=='train' else lock['validation_seeds']
        if len(seeds)!=len(set(seeds)):
            raise ValueError('duplicate evaluation noises')
        for seed in seeds:
            for model in models:
                if evaluation_prediction_source(lock,row,model,seed) is not None:
                    continue
                key = 'native' if model in {'native_s1','native_s2'} else model
                if key not in calls:
                    raise ValueError('model needs a checkpoint or an applicable reuse source: '+model)
                calls[key] += 2 if model=='native_s2' else 1
    return calls
