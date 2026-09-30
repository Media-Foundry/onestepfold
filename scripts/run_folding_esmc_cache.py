#!/usr/bin/env python3
"""Prepare uniform ESMC features for a later matched folding-interface experiment."""
import argparse
import gc
import gzip
import hashlib
import importlib.metadata
import json
import socket
import time
from pathlib import Path

import torch
from safetensors import safe_open
import build_esmc_cache as builder
from validate_esmc_cache import validate


def run_folding_esmc_cache(root):
    begin=time.monotonic();lock=json.loads((root/'lock.json').read_text())
    for path,digest in lock['input_hashes'].items():assert builder._sha256_file(Path(path))==digest,path
    groups=root/'groups.jsonl.gz';rows=builder._read_groups(groups,None)
    assert len(rows)==455 and len({r['group_id'] for r in rows})==455
    for r in rows:
        assert hashlib.sha256(r['sequence'].encode()).hexdigest()==r['group_id']
        assert len(r['sequence'])==r['sequence_length'] and set(r['sequence'])<=set('ACDEFGHIKLMNPQRSTVWY')
    assert sum(r['role']=='train' for r in rows)==423 and sum(r['role']=='validation' for r in rows)==32
    assert torch.cuda.device_count()==1 and not (root/'features').exists()
    torch.set_num_threads(1);torch.manual_seed(101)
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    runtime=dict(host=socket.gethostname(),torch=torch.__version__,gpu=torch.cuda.get_device_name(),
        packages={n:importlib.metadata.version(n) for n in ['transformers','huggingface_hub','tokenizers','safetensors','regex','psutil']},
        scope='ESMC features only; no folding prediction, GT read or fitting; active ESM2 training unchanged')
    (root/'runtime.json').write_text(json.dumps(runtime,indent=2)+'\n')
    model,tok=builder._load_model(lock['model_id'],lock['hf_revision'],'cuda',True)
    probes=[]
    for g in lock['probe_groups']:
        row=next(r for r in rows if r['group_id']==g);seq=row['sequence']
        first=builder._extract_batch(model,tok,[seq],'cuda','final')[0]['final']
        replay=builder._extract_batch(model,tok,[seq],'cuda','final')[0]['final']
        assert torch.equal(first,replay) and first.shape==(len(seq),1152) and torch.isfinite(first).all()
        probes.append(dict(group_id=g,length=len(seq),exact_repeat=True))
    del model,tok,first,replay;gc.collect();torch.cuda.empty_cache()
    (root/'preflight.json').write_text(json.dumps(dict(complete=True,probes=probes),indent=2)+'\n')
    summary=builder.build_cache(groups,root/'features',model_id=lock['model_id'],hf_revision=lock['hf_revision'],
        code_revision=lock['code_revision'],feature_variant='final',device='cuda',batch_tokens=2048,
        shard_tokens=16384,local_files_only=True)
    audit=validate(root/'features',groups)
    with gzip.open(root/'features/manifest.jsonl.gz','rt') as f:manifest=[json.loads(x) for x in f]
    expected={r['group_id']:r for r in rows};offsets={};finite_rows=0
    for r in manifest:
        assert r['sequence_sha256']==r['group_id'] and r['sequence_length']==expected[r['group_id']]['sequence_length']
        assert r['offset_end']-r['offset_start']==r['sequence_length']
        offsets.setdefault(r['shard'],[]).append((r['offset_start'],r['offset_end']))
        with safe_open(str(root/'features'/r['shard']),framework='pt',device='cpu') as f:
            value=f.get_slice('final')[r['offset_start']:r['offset_end']]
            assert value.dtype==torch.bfloat16 and value.shape==(r['sequence_length'],1152) and torch.isfinite(value).all()
        finite_rows+=1
    for intervals in offsets.values():
        cursor=0
        for start,end in sorted(intervals):assert start==cursor;cursor=end
    result=dict(complete=True,summary=summary,audit=audit,finite_sequence_verified=finite_rows,
        exact_startup_replays=probes,lock_sha256=builder._sha256_file(root/'lock.json'),
        manifest_sha256=builder._sha256_file(root/'features/manifest.jsonl.gz'),
        peak_gpu_bytes=torch.cuda.max_memory_allocated(),seconds=time.monotonic()-begin,
        old_cache_mixed=False,old_cache_numerical_equivalence_established=False,
        folding_comparison_started=False,scope=runtime['scope'])
    (root/'acceptance.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    run_folding_esmc_cache(p.parse_args().root.resolve())
