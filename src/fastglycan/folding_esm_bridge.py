"""TRAIN-only paired-feature access for a separately fitted C4 ESMC interface."""
import hashlib
from pathlib import Path

import torch
from safetensors import safe_open


def select_folding_bridge_train(pairs, rows, expected_train=423):
    """Reject membership/role drift before opening any feature file."""
    indexed = {p['group_id']: p for p in pairs}
    source = {r['group_id']: r for r in rows}
    if len(indexed) != len(pairs) or len(source) != len(rows) or set(indexed) != set(source):
        raise ValueError('Duplicate or mismatched paired feature membership')
    for group, row in source.items():
        pair = indexed[group]
        if row['role'] not in ('train', 'validation') or pair['role'] != row['role']:
            raise ValueError('Paired feature role mismatch')
        if hashlib.sha256(row['sequence'].encode()).hexdigest() != group or len(row['sequence']) != pair['length']:
            raise ValueError('Paired sequence mismatch')
    selected = [indexed[g] for g in sorted(source) if source[g]['role'] == 'train']
    if len(selected) != expected_train:
        raise ValueError('Unexpected TRAIN denominator')
    return selected


def load_folding_bridge_pair(pair, feature_root, cache_lock_sha256):
    """Load only a TRAIN pair; use mmap to avoid unrelated conditioning tensors."""
    if pair['role'] != 'train':
        raise ValueError('Validation features are excluded from this fit')
    group, length = pair['group_id'], pair['length']
    saved = torch.load(pair['esm2_path'], map_location='cpu', weights_only=False, mmap=True)
    if saved['group_id'] != group or saved['role'] != 'train' or saved['lock_sha256'] != cache_lock_sha256:
        raise ValueError('Native feature cache provenance mismatch')
    features = saved['features']
    if not torch.equal(features['token_index'], torch.arange(length)) or not torch.equal(features['residue_index'], torch.arange(1, length+1)):
        raise ValueError('Residue layout mismatch')
    e = features['esm_token_embedding']
    entry = pair['esmc_entry']
    if entry['sequence_sha256'] != group or entry['sequence_length'] != length or entry['offset_end']-entry['offset_start'] != length:
        raise ValueError('ESMC manifest identity mismatch')
    with safe_open(str(Path(feature_root)/entry['shard']), framework='pt', device='cpu') as f:
        x = f.get_slice('final')[entry['offset_start']:entry['offset_end']]
    if e.shape != (length, 2560) or e.dtype != torch.float32 or x.shape != (length, 1152) or x.dtype != torch.bfloat16:
        raise ValueError('Feature shape/dtype mismatch')
    if not torch.isfinite(e).all() or not torch.isfinite(x).all():
        raise ValueError('Nonfinite features')
    if hashlib.sha256(e.contiguous().numpy().tobytes()).hexdigest() != pair['esm2_feature_sha256']:
        raise ValueError('ESM2 tensor hash mismatch')
    if hashlib.sha256(x.contiguous().view(torch.uint16).numpy().tobytes()).hexdigest() != pair['esmc_feature_sha256']:
        raise ValueError('ESMC tensor hash mismatch')
    return x, e
