#!/usr/bin/env python3
"""Read-only paired ESM2/ESMC feature readiness; no fit, GT or model inference."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import time

import torch
from safetensors import safe_open


def audit_folding_esm_pairs(training, esmc, output):
    assert not output.exists(), 'preserve prior audit'
    torch.set_num_threads(1)
    begin = time.monotonic()
    training_bytes = (training / 'lock.json').read_bytes()
    train = json.loads(training_bytes)
    cache = Path(train['cache'])
    cache_bytes = (cache / 'lock.json').read_bytes()
    cache_sha = hashlib.sha256(cache_bytes).hexdigest()
    assert cache_sha == train['cache_lock_sha256']
    lock = json.loads(cache_bytes)
    acceptance = json.loads((esmc / 'acceptance.json').read_text())
    assert acceptance['complete'] and acceptance['finite_sequence_verified'] == 455
    manifest_path = esmc / 'features/manifest.jsonl.gz'
    manifest_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    assert manifest_sha == acceptance['manifest_sha256']
    with gzip.open(manifest_path, 'rt') as f:
        manifest = [json.loads(line) for line in f]
    rows = {r['group_id']: r for r in lock['rows']}
    entries = {r['group_id']: r for r in manifest}
    assert len(rows) == len(lock['rows']) == len(entries) == len(manifest) == 455
    assert set(rows) == set(entries)
    shard_hashes = {}
    for entry in manifest:
        shard = esmc / 'features' / entry['shard']
        if str(shard) not in shard_hashes:
            with shard.open('rb') as f:
                shard_hashes[str(shard)] = hashlib.file_digest(f, 'sha256').hexdigest()
        assert shard_hashes[str(shard)] == entry['shard_sha256']
    pairs = []
    for group, row in rows.items():
        sequence = row['sequence']
        length = len(sequence)
        entry = entries[group]
        assert hashlib.sha256(sequence.encode()).hexdigest() == group == entry['sequence_sha256']
        assert entry['sequence_length'] == length == entry['offset_end'] - entry['offset_start']
        path = cache / 'examples' / group / 'conditioning.pt'
        cached = torch.load(path, map_location='cpu', weights_only=False, mmap=True)
        assert cached['group_id'] == group and cached['role'] == row['role']
        assert cached['lock_sha256'] == cache_sha
        native_path = str(Path(lock['source']) / 'chemistry' / group / 'native.pt')
        assert cached['native_sha256'] == lock['input_hashes'][native_path]
        features = cached['features']
        assert torch.equal(features['token_index'], torch.arange(length))
        assert torch.equal(features['residue_index'], torch.arange(1, length + 1))
        assert features['asym_id'].unique().numel() == 1
        esm2 = features['esm_token_embedding']
        assert esm2.shape == (length, 2560) and esm2.dtype == torch.float32
        assert torch.isfinite(esm2).all()
        with safe_open(str(esmc / 'features' / entry['shard']), framework='pt', device='cpu') as f:
            value = f.get_slice('final')[entry['offset_start']:entry['offset_end']]
        assert value.shape == (length, 1152) and value.dtype == torch.bfloat16
        assert torch.isfinite(value).all()
        pairs.append(dict(group_id=group, length=length, role=row['role'],
            cohort='new_validation' if row['role']=='validation' else ('original_train' if group in train['original_train_ids'] else 'added_train'),
            esm2_path=str(path), esm2_feature_sha256=hashlib.sha256(esm2.contiguous().numpy().tobytes()).hexdigest(),
            esm2_container_previously_audited_sha256=train['cache_files'][str(path)],
            esmc_entry=entry,
            esmc_feature_sha256=hashlib.sha256(value.contiguous().view(torch.uint16).numpy().tobytes()).hexdigest()))
        del cached, features, esm2, value
    assert (training / 'lock.json').read_bytes() == training_bytes
    counts = {name:sum(p['cohort']==name for p in pairs) for name in ['original_train','added_train','new_validation']}
    assert counts == dict(original_train=128, added_train=295, new_validation=32)
    result = dict(complete=True, counts=counts, residues=sum(p['length'] for p in pairs), pairs=pairs,
        training_lock_sha256=hashlib.sha256(training_bytes).hexdigest(),
        cache_lock_sha256=cache_sha, esmc_manifest_sha256=manifest_sha, shard_hashes=shard_hashes,
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), seconds=time.monotonic()-begin,
        scope='Feature readiness only; no GT read, forward, optimization, interface fit, or quality claim.',
        provenance_limit='ESM2 tensor bytes checked now; complete conditioning container hashes inherited from completed cache audit, not recomputed here. Sequence alignment follows locked extraction provenance and token/residue layout, not independent model re-extraction.',
        compute_dtype_limit='ESMC storage is BF16; extraction model compute dtype was not separately recorded.')
    output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['pairs','shard_hashes']}, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--training', type=Path, required=True)
    p.add_argument('--esmc', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    audit_folding_esm_pairs(a.training.resolve(), a.esmc.resolve(), a.output.resolve())
