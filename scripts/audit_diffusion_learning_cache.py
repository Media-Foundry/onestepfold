#!/usr/bin/env python3
"""Read every frozen cache artifact before allowing parameter training."""
import argparse
import json
from pathlib import Path
import time

import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256, write_json


def audit_adapter_cache(root):
    start=time.monotonic();lock=json.loads((root/'lock.json').read_text())
    execution=json.loads((root/'execution.json').read_text())
    assert execution['complete'] and all(w['exit_code']==0 for w in execution['workers'])
    for path,digest in lock['hashes'].items():assert sha256(Path(path))==digest
    for path,digest in lock['input_hashes'].items():assert sha256(Path(path))==digest
    source=Path(lock['source']);rows=lock['rows'];seen=set();counts=dict(pairformer=0,diffusion=0)
    for i,assignment in enumerate(lock['assignments']):
        report=json.loads((root/f'worker_{i}/report.json').read_text())
        assert report['complete'] and report['lock_sha256']==sha256(root/'lock.json')
        assert [r['group_id'] for r in report['rows']]==[r['group_id'] for r in assignment]
        for name in counts:counts[name]+=report['counts'][name]
        for row in report['rows']:
            g=row['group_id'];assert g not in seen;seen.add(g)
            assert row==json.loads((root/'examples'/g/'report.json').read_text())
    assert counts==dict(pairformer=640,diffusion=896) and len(seen)==160
    total_bytes=0;outputs=0;observed=0;missing=0;audited=[]
    for row in rows:
        g=row['group_id'];folder=root/'examples'/g
        report=json.loads((folder/'report.json').read_text())
        expected={'conditioning.pt'}
        if row['role']=='train':
            expected|={'gt_supervision.pt'}|{f's{s}_seed{k}.npy' for s in [1,2] for k in lock['train_seeds']}
        assert set(report['files'])==expected
        assert {p.name for p in folder.iterdir()}==expected|{'report.json'}
        for name,digest in report['files'].items():
            file=folder/name;assert sha256(file)==digest;total_bytes+=file.stat().st_size
        cache=torch.load(folder/'conditioning.pt',map_location='cpu',weights_only=False)
        assert cache['role']==row['role'] and cache['group_id']==g
        assert cache['lock_sha256']==sha256(root/'lock.json')
        assert cache['native_sha256']==lock['input_hashes'][str(source/'chemistry'/g/'native.pt')]
        flat=cache['conditioning_flat'];assert flat.dtype==torch.float32 and torch.isfinite(flat).all()
        assert len(cache['shapes'])==len(cache['sizes'])==3 and sum(cache['sizes'])==flat.numel()
        assert all(int(np.prod(s))==n for s,n in zip(cache['shapes'],cache['sizes']))
        tensors=[cache['features']]
        while tensors:
            item=tensors.pop()
            if isinstance(item,dict):tensors.extend(item.values())
            elif isinstance(item,(list,tuple)):tensors.extend(item)
            elif torch.is_tensor(item) and item.is_floating_point():assert torch.isfinite(item).all()
        mapping=dict(np.load(source/'chemistry'/g/'mapping.npz'));n=len(mapping['atom_names'])
        if row['role']=='train':
            assert report['reload_replay'] and report['counts']==dict(pairformer=4,diffusion=7)
            assert len(report['outputs'])==4
            for output in report['outputs']:
                x=np.load(folder/output['name']);assert x.shape==(n,3) and x.dtype==np.float32 and np.isfinite(x).all()
                assert output['sha256']==report['files'][output['name']];outputs+=1
            labels=torch.load(folder/'gt_supervision.pt',map_location='cpu',weights_only=False)
            mask=labels['coordinate_mask'].numpy();assert mask.dtype==np.bool_ and np.array_equal(mask,mapping['mask'])
            assert np.array_equal(labels['coordinate'].numpy()[mask],mapping['coordinates'][mask])
            pairs=labels['smooth']['pairs'].numpy();assert mask[pairs].all()
            assert (mapping['residue_ids'][pairs[:,0]]!=mapping['residue_ids'][pairs[:,1]]).all()
            distances=np.linalg.norm(mapping['coordinates'][pairs[:,0]].astype(float)-mapping['coordinates'][pairs[:,1]],axis=1)
            np.testing.assert_allclose(distances,labels['smooth']['target_distance'].numpy(),rtol=0,atol=1e-12)
            assert (distances<15).all()
            counts_per_atom=np.bincount(pairs.ravel(),minlength=n)
            assert np.array_equal(counts_per_atom,labels['smooth']['neighbor_count'].numpy())
            weights=(1/counts_per_atom[pairs[:,0]]+1/counts_per_atom[pairs[:,1]])/np.count_nonzero(counts_per_atom)
            np.testing.assert_array_equal(weights,labels['smooth']['pair_weight'].numpy())
            bonds=labels['bonds'].numpy();assert mask[bonds].all()
            np.testing.assert_allclose(np.linalg.norm(mapping['coordinates'][bonds[:,0]].astype(float)-mapping['coordinates'][bonds[:,1]],axis=1),labels['bond_distance'].numpy(),rtol=0,atol=1e-12)
            assert len(labels['radii'])==n and int(labels['atoms'])==n
            observed+=int(mask.sum());missing+=int((~mask).sum())
            del labels
        else:
            assert not report['reload_replay'] and report['outputs']==[] and report['counts']==dict(pairformer=4,diffusion=0)
        audited.append(dict(group_id=g,role=row['role'],atoms=n,length=len(row['sequence'])))
        del cache,flat,mapping
    assert outputs==512 and (observed,missing)==(268933,560)
    write_json(root/'audit.json',dict(complete=True,lock_sha256=sha256(root/'lock.json'),
        execution_sha256=sha256(root/'execution.json'),audited=audited,counts=counts,
        cache_bytes=total_bytes,conditioning=160,train_outputs=outputs,validation_outputs=0,
        observed_train_atoms=observed,missing_train_atoms=missing,seconds=time.monotonic()-start,
        scope='CPU full artifact/hash/mask/label checks; GPU replay evidence is per-worker, not a new inference'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args()
    torch.set_num_threads(1);audit_adapter_cache(a.root)
