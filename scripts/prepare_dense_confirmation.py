#!/usr/bin/env python3
"""Fresh source release, conditioning-only cache audit and fixed candidate evaluation."""
import argparse
import json
from pathlib import Path
import shutil
import torch
from fastglycan.paired_teacher_protocol import sha256, write_json


def prepare_confirmation_cache(root):
    assert not (root/'lock.json').exists();base=root.parent
    source=base/'diffusion_dense_fresh_sources_v1_20260930'
    audit=json.loads((source/'audit.json').read_text());selection=json.loads((source/'selection_lock.json').read_text())
    assert audit['verified_sources'] and audit['selection_complete'] and selection['complete']
    assert audit['selection_lock_sha256']==sha256(source/'selection_lock.json')
    assert selection['selection_sha256']==sha256(source/'selection.json') and selection['data_manifest_sha256']==sha256(source/'data_manifest.json')
    rows=json.loads((source/'selection.json').read_text());assert len(rows)==32 and all(r['role']=='validation' for r in rows)
    inputs={str(source/n):sha256(source/n) for n in ['selection.json','selection_lock.json','data_manifest.json','audit.json','source_lock.json']}
    manifest=json.loads((source/'data_manifest.json').read_text())
    for r in rows:
        for folder in ['chemistry','data/examples']:
            for p in (source/folder/r['group_id']).iterdir():
                if p.is_file():assert sha256(p)==manifest[str(p.relative_to(source))];inputs[str(p)]=sha256(p)
    prior=base/'diffusion_learning_cache_v1_20260930';old=json.loads((prior/'lock.json').read_text())
    for p,d in old['weights_sha256'].items():assert sha256(Path(p))==d
    for file in ['differentiable_mini.py','soft_sequence_chart.py','soft_esm.py']:
        assert sha256(root/'code/src/fastglycan/models'/file)==sha256(prior/'code/src/fastglycan/models'/file)
    assert sha256(root/'code/scripts/cache_diffusion_learning.py')==sha256(prior/'code/scripts/cache_diffusion_learning.py')
    assert shutil.disk_usage(root).free>30*1024**3
    assignments=[[] for _ in range(8)];loads=[0]*8
    for r in sorted(rows,key=lambda x:(-len(x['sequence']),x['group_id'])):
        i=min(range(8),key=lambda j:(loads[j],j));assignments[i].append(r);loads[i]+=len(r['sequence'])**2
    write_json(root/'lock.json',dict(source=str(source),rows=rows,assignments=assignments,estimated_loads=loads,
        input_hashes=inputs,weights_sha256=old['weights_sha256'],weight_stats=old['weight_stats'],
        hashes={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.md']},
        train_seeds=[600001,600011],validation_seeds=[700021,700027],dtype='fp32',cycles=4,
        validation_predictions=False,training_started=False,planned_conditioning=32,planned_train_outputs=0))


def audit_confirmation_cache(root):
    lock=json.loads((root/'lock.json').read_text());execution=json.loads((root/'execution.json').read_text())
    assert execution['complete'] and all(w['exit_code']==0 for w in execution['workers'])
    for p,d in {**lock['input_hashes'],**lock['hashes']}.items():assert sha256(Path(p))==d
    all_rows=[];totals=dict(pairformer=0,diffusion=0);checked=[]
    for i,assigned in enumerate(lock['assignments']):
        report=json.loads((root/f'worker_{i}/report.json').read_text())
        assert report['complete'] and report['lock_sha256']==sha256(root/'lock.json')
        assert [r['group_id'] for r in report['rows']]==[r['group_id'] for r in assigned]
        for k in totals:totals[k]+=report['counts'][k]
        for r in report['rows']:
            g=r['group_id'];assert r['role']=='validation' and r['outputs']==[] and r['counts']==dict(pairformer=4,diffusion=0)
            data=root/'examples'/g;assert set(r['files'])=={'conditioning.pt'}
            assert sha256(data/'conditioning.pt')==r['files']['conditioning.pt']
            c=torch.load(data/'conditioning.pt',map_location='cpu',weights_only=False)
            assert c['role']=='validation' and c['group_id']==g and c['lock_sha256']==sha256(root/'lock.json')
            assert c['conditioning_flat'].dtype==torch.float32 and torch.isfinite(c['conditioning_flat']).all()
            assert sum(c['sizes'])==c['conditioning_flat'].numel() and len(c['shapes'])==3
            parts=[x.reshape(s) for x,s in zip(c['conditioning_flat'].split(c['sizes']),c['shapes'])]
            assert torch.equal(torch.cat([x.flatten() for x in parts]),c['conditioning_flat'])
            assert c['native_sha256']==lock['input_hashes'][str(Path(lock['source'])/'chemistry'/g/'native.pt')]
            row=next(x for x in assigned if x['group_id']==g);length=len(row['sequence'])
            assert all(x.shape[0]==length for x in parts) and parts[2].shape[1]==length
            assert c['features']['esm_token_embedding'].shape[0]==length
            all_rows.append(g);checked.append(dict(group_id=g,length=length,bytes=(data/'conditioning.pt').stat().st_size))
            del c,parts
    assert len(all_rows)==len(set(all_rows))==32 and totals==dict(pairformer=128,diffusion=0)
    write_json(root/'audit.json',dict(complete=True,conditioning=32,validation_outputs=0,training_started=False,
        rows=checked,counts=totals,lock_sha256=sha256(root/'lock.json'),script_sha256=sha256(Path(__file__))))


def prepare_confirmation_evaluation(root):
    assert not (root/'lock.json').exists();base=root.parent
    cache=base/'diffusion_dense_fresh_cache_v1_20260930';cl=json.loads((cache/'lock.json').read_text())
    audit=json.loads((cache/'audit.json').read_text());assert audit['complete'] and audit['lock_sha256']==sha256(cache/'lock.json')
    assert audit['validation_outputs']==0 and audit['conditioning']==32
    train=base/'diffusion_dense_learning_v1_20260930';tl=json.loads((train/'lock.json').read_text())
    ta=json.loads((train/'training_audit.json').read_text());assert ta['complete'] and ta['lock_sha256']==sha256(train/'lock.json')
    checkpoint=ta['checkpoints']['diffusion_dense']
    assert sha256(Path(checkpoint['path']))==checkpoint['sha256']=='7fc01820269b6f376f8313b79c4ab2bf8fcfd2a0b2a017a432033a51b73fd829'
    inputs=dict(cl['input_hashes'])
    for r in cl['rows']:
        path=cache/'examples'/r['group_id']/'conditioning.pt';report=json.loads((path.parent/'report.json').read_text())
        assert report['outputs']==[] and sha256(path)==report['files']['conditioning.pt'];inputs[str(path)]=sha256(path)
    for p in [cache/'audit.json',cache/'lock.json',train/'training_audit.json',train/'lock.json']:inputs[str(p)]=sha256(p)
    prior=base/'diffusion_dense_evaluation_v1_20260930';old=json.loads((prior/'lock.json').read_text())
    probe=old['probe'];pc=Path(old['cache']);ps=Path(old['source'])
    assert probe['role']=='train' and probe['group_id'] not in {r['group_id'] for r in cl['rows']}
    for p in [pc/'examples'/probe['group_id']/'conditioning.pt',pc/'examples'/probe['group_id']/f's1_seed{old["train_seeds"][0]}.npy',ps/'chemistry'/probe['group_id']/'native.pt']:
        inputs[str(p)]=sha256(p)
    hashes={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.md']}
    bands=root/'code/docs/connection_reference_bands.json';hashes[str(bands)]=sha256(bands)
    write_json(root/'lock.json',dict(train=str(train),training_lock_sha256=sha256(train/'lock.json'),
        cache=str(cache),source=cl['source'],rows=cl['rows'],assignments=cl['assignments'],
        checkpoints=dict(diffusion_dense=checkpoint),selected_names=dict(diffusion_dense=tl['preflights']['diffusion_dense']['selected_names']),
        models=['native_s1','native_s2','diffusion_dense'],probe=probe,probe_cache=str(pc),probe_source=str(ps),
        train_seeds=old['train_seeds'],validation_seeds=[700021,700027],weights_sha256=cl['weights_sha256'],weight_stats=cl['weight_stats'],
        input_hashes=inputs,hashes=hashes,contrasts=[['diffusion_dense','native_s1'],['diffusion_dense','native_s2'],['native_s2','native_s1']],
        bootstrap=dict(replicates=10000,seed=20260930,unit='protein after mean over two noises'),
        expected_outputs=192,expected_new_predictions=192,expected_probe_nfe=32,
        primary='Fresh32 confirmation: frozen full diffusion S1 minus public S1 AA-lDDT; chemistry and CA remain separate'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--mode',choices=['cache','audit-cache','evaluation'],required=True);a=p.parse_args();torch.set_num_threads(1)
    if a.mode=='cache':prepare_confirmation_cache(a.root)
    elif a.mode=='audit-cache':audit_confirmation_cache(a.root)
    else:prepare_confirmation_evaluation(a.root)
