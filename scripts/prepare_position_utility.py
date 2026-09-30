#!/usr/bin/env python3
"""Lock four TRAIN-only parents and a frozen hard-position utility protocol."""
import argparse
import hashlib
import json
from pathlib import Path
from fastglycan.paired_teacher_protocol import sha256,write_json


def prepare_position_utility(root):
    assert not (root/'lock.json').exists();base=root.parent
    old=base/'diffusion_dense_evaluation_v1_20260930';prior=json.loads((old/'lock.json').read_text())
    eligible=[r for r in prior['rows'] if r['role']=='train' and 80<=len(r['sequence'])<=160]
    rows=sorted(eligible,key=lambda r:hashlib.sha256(('position-utility-v1:20260930:'+r['group_id']).encode()).hexdigest())[:4]
    assert len(rows)==4 and len({r['group_id'] for r in rows})==4
    source=Path(prior['source']);cp=prior['checkpoints']['diffusion_dense']
    assert sha256(Path(cp['path']))==cp['sha256']=='7fc01820269b6f376f8313b79c4ab2bf8fcfd2a0b2a017a432033a51b73fd829'
    inputs={str(old/'lock.json'):sha256(old/'lock.json')}
    for r in rows:
        for name in ['native.pt','mapping.npz']:
            path=source/'chemistry'/r['group_id']/name;assert sha256(path)==prior['input_hashes'][str(path)];inputs[str(path)]=sha256(path)
    write_json(root/'lock.json',dict(rows=rows,eligible_parents=len(eligible),source=str(source),checkpoint=cp,
        selected_names=prior['selected_names']['diffusion_dense'],weights_sha256=prior['weights_sha256'],
        input_hashes=inputs,hashes={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.md','.json']},
        alpha=.001,cycles=4,steps=1,proposal_seed=800011,confirmation_seeds=[800029,800053],
        evaluation_seeds=[800011,800029,800053],random_seed_base=900001,workers=8,
        maximum_hard_predictions=468,training=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);prepare_position_utility(p.parse_args().root.resolve())
