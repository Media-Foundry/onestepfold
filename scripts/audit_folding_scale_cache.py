#!/usr/bin/env python3
"""Audit all455 caches and independent GT labels before continuation training."""
import argparse
import json
from pathlib import Path
import subprocess
import time
import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256, write_json


def audit_folding_scale_cache(root, cycle):
    torch.set_num_threads(1); begin=time.monotonic()
    lock=json.loads((root/'lock.json').read_text()); experiment=json.loads((cycle/'lock.json').read_text())
    assert lock['cycle_lock_sha256']==sha256(cycle/'lock.json')
    assert lock['rows']==json.loads((cycle/'selection.json').read_text())
    assert experiment['selection_sha256']==sha256(cycle/'selection.json')
    scheduler=subprocess.check_output(['sacct','-j','662226,662228','-X','-n','-P','--format=JobID,State,ExitCode'],text=True)
    jobs={p[0]:p[1:3] for line in scheduler.splitlines() if (p:=line.split('|')) and p[0]}
    expected_jobs={'662226_0'}|{f'662228_{i}' for i in range(1,8)}
    assert set(jobs)==expected_jobs and all(v==['COMPLETED','0:0'] for v in jobs.values()),jobs
    for name,digest in {**lock['hashes'],**lock['input_hashes'],**lock['weights_sha256']}.items():
        assert sha256(Path(name))==digest,name
    source=Path(lock['source']); seen=set(); counts=dict(pairformer=0,diffusion=0); workers=[]
    train=sum(r['role']=='train' for r in lock['rows']); validation=sum(r['role']=='validation' for r in lock['rows'])
    assert (train,validation)==(experiment['train_count'],experiment['validation_count'])==(423,32)
    files={}; rows=[]; outputs=0; missing=0; observed=0; nbytes=0
    for i,assignment in enumerate(lock['assignments']):
        report=json.loads((root/f'worker_{i}/report.json').read_text())
        assert report['complete'] and report['lock_sha256']==sha256(root/'lock.json')
        assert [r['group_id'] for r in report['rows']]==[r['group_id'] for r in assignment]
        workers.append(dict(index=i,seconds=report['seconds'],device=report['device'],peak_gpu_bytes=report['peak_gpu_bytes']))
        for k in counts: counts[k]+=report['counts'][k]
        for r in report['rows']:
            assert r['group_id'] not in seen;seen.add(r['group_id'])
            assert r==json.loads((root/'examples'/r['group_id']/'report.json').read_text())
    assert len(seen)==len(lock['rows'])==455 and counts==dict(pairformer=4*455,diffusion=7*423)
    for row in lock['rows']:
        g=row['group_id'];folder=root/'examples'/g;report=json.loads((folder/'report.json').read_text())
        expected={'conditioning.pt'}
        if row['role']=='train':expected|={'gt_supervision.pt'}|{f's{s}_seed{k}.npy' for s in (1,2) for k in lock['train_seeds']}
        assert set(report['files'])==expected and {p.name for p in folder.iterdir()}==expected|{'report.json'}
        for name,digest in report['files'].items():
            p=folder/name;assert sha256(p)==digest;files[str(p)]=digest;nbytes+=p.stat().st_size
        cached=torch.load(folder/'conditioning.pt',map_location='cpu',weights_only=False)
        assert cached['role']==row['role'] and cached['group_id']==g and cached['lock_sha256']==sha256(root/'lock.json')
        assert cached['native_sha256']==lock['input_hashes'][str(source/'chemistry'/g/'native.pt')]
        flat=cached['conditioning_flat'];assert flat.dtype==torch.float32 and torch.isfinite(flat).all()
        assert len(cached['shapes'])==len(cached['sizes'])==3 and sum(cached['sizes'])==flat.numel()
        assert all(int(np.prod(s))==n for s,n in zip(cached['shapes'],cached['sizes']))
        pending=[cached['features']]
        while pending:
            x=pending.pop()
            if isinstance(x,dict):pending.extend(x.values())
            elif isinstance(x,(tuple,list)):pending.extend(x)
            elif torch.is_tensor(x) and x.is_floating_point():assert torch.isfinite(x).all()
        m=dict(np.load(source/'chemistry'/g/'mapping.npz'));n=len(m['atom_names'])
        if row['role']=='train':
            assert report['reload_replay'] and report['counts']==dict(pairformer=4,diffusion=7)
            assert {(x['seed'],x['steps']) for x in report['outputs']}=={(s,k) for s in lock['train_seeds'] for k in (1,2)}
            for x in report['outputs']:
                y=np.load(folder/x['name']);assert y.shape==(n,3) and y.dtype==np.float32 and np.isfinite(y).all()
                assert x['sha256']==report['files'][x['name']];outputs+=1
            labels=torch.load(folder/'gt_supervision.pt',map_location='cpu',weights_only=False)
            mask=labels['coordinate_mask'].numpy();assert mask.dtype==np.bool_ and np.array_equal(mask,m['mask'])
            assert np.array_equal(labels['coordinate'].numpy()[mask],m['coordinates'][mask])
            pairs=labels['smooth']['pairs'].numpy();assert mask[pairs].all()
            assert (m['residue_ids'][pairs[:,0]]!=m['residue_ids'][pairs[:,1]]).all()
            d=np.linalg.norm(m['coordinates'][pairs[:,0]].astype(float)-m['coordinates'][pairs[:,1]],axis=1)
            np.testing.assert_allclose(d,labels['smooth']['target_distance'].numpy(),rtol=0,atol=1e-12);assert (d<15).all()
            peratom=np.bincount(pairs.ravel(),minlength=n)
            assert np.array_equal(peratom,labels['smooth']['neighbor_count'].numpy())
            np.testing.assert_array_equal((1/peratom[pairs[:,0]]+1/peratom[pairs[:,1]])/np.count_nonzero(peratom),labels['smooth']['pair_weight'].numpy())
            bonds=labels['bonds'].numpy();assert mask[bonds].all()
            np.testing.assert_allclose(np.linalg.norm(m['coordinates'][bonds[:,0]].astype(float)-m['coordinates'][bonds[:,1]],axis=1),labels['bond_distance'].numpy(),rtol=0,atol=1e-12)
            assert len(labels['radii'])==n and int(labels['atoms'])==n
            observed+=int(mask.sum());missing+=int((~mask).sum());del labels
        else:
            assert not report['reload_replay'] and report['outputs']==[] and report['counts']==dict(pairformer=4,diffusion=0)
        rows.append(dict(group_id=g,role=row['role'],length=len(row['sequence']),atoms=n))
        del cached,flat,m
    assert outputs==4*train
    write_json(root/'execution.json',dict(complete=True,jobs=jobs,workers=workers))
    write_json(root/'artifact_manifest.json',files)
    result=dict(complete=True,lock_sha256=sha256(root/'lock.json'),cycle_lock_sha256=sha256(cycle/'lock.json'),
        execution_sha256=sha256(root/'execution.json'),artifact_manifest_sha256=sha256(root/'artifact_manifest.json'),
        script_sha256=sha256(Path(__file__)),conditioning=455,train=423,validation=32,train_outputs=outputs,
        validation_outputs=0,counts=counts,cache_bytes=nbytes,observed_train_atoms=observed,
        missing_train_atoms=missing,audited=rows,seconds=time.monotonic()-begin,training_started=False)
    write_json(root/'audit.json',result);print(json.dumps({k:v for k,v in result.items() if k!='audited'}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--cycle',type=Path,required=True)
    a=p.parse_args();audit_folding_scale_cache(a.root.resolve(),a.cycle.resolve())
