#!/usr/bin/env python3
"""Matched noise diversity trial around the unchanged folding training loop."""
import argparse
import json
from pathlib import Path
import torch
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.noise_diversity import make_noise_diversity_lock
from fastglycan.global_distance_training import global_distance_training_hooks


def prepare_noise_diversity_training(root,arm):
    plan=json.loads((root/'cache_plan.json').read_text());control=Path(plan['control'])
    assert sha256(control/'lock.json')==plan['control_lock_sha256']
    base=json.loads((control/'lock.json').read_text());cache=root/'cache'
    audit=json.loads((cache/'audit.json').read_text());assert audit['complete'] and audit['teachers']==9038
    files=json.loads((cache/'artifact_manifest.json').read_text())
    hashes=dict(base['hashes']);hashes.update(plan['hashes']);hashes.update(plan['native_files'])
    for p in [root/'cache_plan.json',root/'teacher_execution.json',control/'lock.json',cache/'audit.json']:
        hashes[str(p)]=sha256(p)
    for p,h in files.items():assert sha256(Path(p))==h
    dest=root/arm;dest.mkdir(exist_ok=False);(dest/'code').symlink_to(root/'code',target_is_directory=True)
    lock=make_noise_diversity_lock(base,arm=arm,cache=cache,cache_files=files,
        cache_digests={name:sha256(cache/name) for name in ['lock.json','artifact_manifest.json','audit.json']},
        hashes=hashes,protocol_sha256=sha256(root/'code/docs/mini_noise_diversity_v1.md'),script_sha256=sha256(Path(__file__)))
    write_json(dest/'lock.json',lock)


def run_noise_diversity_training(root,arm,mode):
    import train_folding_scale as trainer
    import fastglycan.adapter_supervision as supervision
    dest=root/arm;lock=json.loads((dest/'lock.json').read_text())
    assert lock['noise_diversity']['arm']==arm
    assert torch.version.hip and str(torch.__version__)==lock['backend']['torch']
    with global_distance_training_hooks(trainer,supervision,lock):
        trainer.run_folding_training(dest,mode,'expanded' if mode=='train' else None)
    if mode=='preflight':
        r=json.loads((dest/'preflight/report.json').read_text());assert r['complete'] and r['parameter_updates']==0
        plan=json.loads((root/'cache_plan.json').read_text());old=json.loads((Path(plan['control'])/'preflight/report.json').read_text())
        assert r['initial_sha256']==old['initial_sha256']
        assert r['selected_tensors']==288 and r['trainable_parameters']==69777841
        write_json(dest/'release.json',dict(lock_sha256=sha256(dest/'lock.json'),preflight_sha256=sha256(dest/'preflight/report.json')))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--arm',choices=['fixed','diverse'],required=True)
    p.add_argument('--mode',choices=['prepare','preflight','train'],required=True);a=p.parse_args()
    if a.mode=='prepare':prepare_noise_diversity_training(a.root,a.arm)
    else:run_noise_diversity_training(a.root,a.arm,a.mode)
