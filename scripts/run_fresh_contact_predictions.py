#!/usr/bin/env python3
"""Reuse the audited C4/S1 raw path for a separately locked fresh panel."""
import argparse
import importlib
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256, write_json
import run_c4_connection_confirmation as native


def prepare_fresh_contact_runtime(root, original):
    assert not (root/'runtime_lock.json').exists()
    runtime=root.parent/'protenix_stage0_pkg/v1_1/runtime'
    assert Path(os.environ['PROTENIX_ROOT_DIR']).resolve()==runtime.resolve()
    selection_lock=json.loads((original/'selection_lock.json').read_text())
    audit=json.loads((original/'audit.json').read_text())
    assert selection_lock['complete'] and audit['verified'] and audit['proteins']==8
    assert audit['selection_lock_sha256']==sha256(original/'selection_lock.json')
    assert selection_lock['selection_sha256']==sha256(original/'selection.json')
    manifest=json.loads((original/'data_manifest.json').read_text())
    assert sha256(original/'data_manifest.json')==selection_lock['manifest_sha256']
    for path,digest in manifest.items():assert sha256(original/path)==digest
    source=root/'source';source.mkdir()
    rows=json.loads((original/'selection.json').read_text());assert len(rows)==8
    for row in rows:
        group=row['group_id'];packet=source/'chemistry'/group
        packet.parent.mkdir(exist_ok=True);packet.symlink_to(original/'chemistry'/group)
        folder=source/'data'/group;folder.mkdir(parents=True)
        for name in ['gt.npz','gt.json','prepared.json']:
            (folder/name).symlink_to(original/'data/examples'/group/name)
        with np.load(packet/'mapping.npz') as mapping:
            assert mapping['mask'].all()
            np.savez_compressed(folder/'inventory.npz',atom_name=mapping['atom_names'],
                residue_id=mapping['residue_ids'],chain_id=mapping['chain_ids'])
    write_json(source/'selection.json',rows)
    code={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.md']}
    for name in ['protenix','esm','runner','configs']:
        folder=Path(inspect.getfile(importlib.import_module(name))).parent
        code.update({str(p):sha256(p) for p in folder.rglob('*.py')})
    inputs={str(source/'selection.json'):sha256(source/'selection.json'),
        str(original/'selection_lock.json'):sha256(original/'selection_lock.json'),
        str(original/'audit.json'):sha256(original/'audit.json')}
    for row in rows:
        for folder in [source/'chemistry'/row['group_id'],source/'data'/row['group_id']]:
            inputs.update({str(p):sha256(p) for p in folder.iterdir() if p.is_file()})
    prior=json.loads((root.parent/'c4_connection_confirmation_v1_20260930/runtime_lock.json').read_text())
    weights=prior['weights_sha256']
    for path,digest in weights.items():assert sha256(Path(path))==digest
    write_json(root/'runtime_lock.json',dict(source=str(source),source_hashes=code,input_hashes=inputs,
        weights_sha256=weights,weight_stats={p:[Path(p).stat().st_size,Path(p).stat().st_mtime_ns] for p in weights},
        seeds=[400009,400031],model='protenix_mini_esm_v0.5.0',dtype='fp32',cycles=4,steps=1,
        source_slots=8,expected_supported=8,raw_timeout=5400,gt_in_model=False,torch_version=torch.__version__,
        runtime_root=str(runtime),
        reused_function='run_c4_connection_confirmation.raw_c4_confirmation; process-local SEEDS from this lock'))
    print('Fresh runtime locked:8 proteins,2 noises,8 GCDs',flush=True)


def run_fresh_contact_predictions(root):
    assert not (root/'raw_controller.json').exists()
    lock=json.loads((root/'runtime_lock.json').read_text())
    write_json(root/'raw_controller.json',dict(pid=os.getpid(),phase='running'))
    jobs=[]
    for i in range(8):
        env=dict(os.environ,ROCR_VISIBLE_DEVICES=str(i),OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
        with (root/f'raw_{i}.log').open('x') as log:
            process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--root',str(root),
                '--mode','raw','--index',str(i)],env=env,stdout=log,stderr=log)
        jobs.append((i,process,time.monotonic()))
    write_json(root/'raw_jobs.json',[dict(index=i,pid=p.pid) for i,p,_ in jobs])
    results=[]
    for i,process,started in jobs:
        try:code=process.wait(timeout=max(.01,lock['raw_timeout']-(time.monotonic()-started)))
        except subprocess.TimeoutExpired:
            process.kill();process.wait();code=124
        results.append(dict(index=i,returncode=code))
    write_json(root/'raw_execution.json',dict(results=results))
    write_json(root/'raw_controller.json',dict(pid=os.getpid(),phase='finished'))
    assert all(r['returncode']==0 for r in results),results
    for path,digest in {**lock['source_hashes'],**lock['input_hashes'],**lock['weights_sha256']}.items():
        assert sha256(Path(path))==digest
    source=Path(lock['source']);rows=json.loads((source/'selection.json').read_text());verified=[]
    for row in rows:
        group=row['group_id'];folder=root/'raw'/group
        report=json.loads((folder/'report.json').read_text())
        assert report['complete'] and report['counts']==dict(pairformer=4,diffusion=3)
        assert report['exact_replay']['bitwise'] and not report['gt_in_model']
        assert report['runtime_lock_sha256']==sha256(root/'runtime_lock.json')
        assert report['identity_sha256']==sha256(folder/'identity.npz')
        with np.load(folder/'identity.npz') as identity,np.load(source/'chemistry'/group/'mapping.npz') as mapping:
            for name in ['atom_names','residue_ids','chain_ids']:assert np.array_equal(identity[name],mapping[name])
            assert str(identity['sequence'])==row['sequence']
            for seed in lock['seeds']:
                entry=report['results'][str(seed)];file=Path(entry['file'])
                assert sha256(file)==entry['sha256'] and entry['diffusion_nfe']==1 and entry['schedule']==[2560.,0.]
                array=np.load(file);assert array.dtype==np.float32 and array.shape==(len(mapping['atom_names']),3) and np.isfinite(array).all()
                verified.append(dict(group_id=group,seed=seed,file=str(file),sha256=entry['sha256']))
    write_json(root/'raw_acceptance.json',dict(complete=True,predictions=verified,proteins=8,
        runtime_lock_sha256=sha256(root/'runtime_lock.json'),extra_replay_nfe=8,repair_started=False))
    print('Verified16 raw predictions and8 exact replays',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--source',type=Path);parser.add_argument('--mode',choices=['prepare','batch','raw'],required=True)
    parser.add_argument('--index',type=int);args=parser.parse_args()
    # Validate before native/config imports can choose the default home cache.
    expected=args.root.parent/'protenix_stage0_pkg/v1_1/runtime'
    assert Path(os.environ['PROTENIX_ROOT_DIR']).resolve()==expected.resolve()
    if args.mode=='prepare':prepare_fresh_contact_runtime(args.root,args.source)
    elif args.mode=='batch':run_fresh_contact_predictions(args.root)
    else:
        lock=json.loads((args.root/'runtime_lock.json').read_text());assert lock['seeds']==[400009,400031]
        native.SEEDS=list(lock['seeds'])
        native.raw_c4_confirmation(args.root,args.index)
