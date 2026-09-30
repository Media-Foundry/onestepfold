#!/usr/bin/env python3
"""Bounded CPU-only source expansion; no source rule relaxation or model calls."""
import argparse,concurrent.futures,hashlib,json,multiprocessing,shutil,time,os
from pathlib import Path
import torch
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.sequence_isolation import read_hsps
from prepare_diffusion_training_sources import qualify_adapter_source


def initialize_expanded_source_worker(root):
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    assert torch.get_num_threads()==torch.get_num_interop_threads()==1 and not torch.cuda.is_available()
    write_json(Path(root)/'worker_threads'/f'{os.getpid()}.json',dict(pid=os.getpid(),torch_threads=torch.get_num_threads(),interop_threads=torch.get_num_interop_threads(),gpu_visible=False))


def prepare_expanded_diffusion_sources(base,root):
    assert not (root/'source_lock.json').exists();begin=time.monotonic()
    old=base/'diffusion_training_sources_v1_20260930';fresh=base/'diffusion_dense_fresh_sources_v1_20260930'
    prior=json.loads((old/'selection.json').read_text());hold=json.loads((fresh/'selection.json').read_text());assert len(prior)==160 and len(hold)==32
    inherited=[r for r in prior if r['role']=='train'];assert len(inherited)==128
    for folder in [old,fresh]:
        audit=json.loads((folder/'audit.json').read_text());selection=json.loads((folder/'selection_lock.json').read_text())
        assert audit['verified_sources'] and audit['selection_complete'] and audit['selection_lock_sha256']==sha256(folder/'selection_lock.json')
        assert selection['selection_sha256']==sha256(folder/'selection.json') and selection['data_manifest_sha256']==sha256(folder/'data_manifest.json')
    for name in ['prepare_diffusion_training_sources.py','preflight_isolated_chemistry.py']:
        assert sha256(root/'code/scripts'/name)==sha256(old/'code/scripts'/name)
    pool=json.loads((old/'pool.json').read_text());search=json.loads((old/'search_lock.json').read_text())
    assert sha256(old/'pool.json')==search['pool_sha256']
    old_selection=json.loads((old/'selection_lock.json').read_text())
    for path,d in old_selection['search_hashes'].items():assert sha256(Path(path))==d
    paths=[f/n for f in [old,fresh] for n in ['selection.json','selection_lock.json','audit.json','data_manifest.json','source_lock.json']]+[old/n for n in ['pool.json','search_lock.json','references_hsps.tsv','pool_hsps.tsv']]
    hashes={str(p):sha256(p) for p in paths};hashes.update({str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.md']})
    (root/'chemistry').mkdir();(root/'data/examples').mkdir(parents=True)
    write_json(root/'source_lock.json',dict(protocol='mini_diffusion_training_expansion_v1',hashes=hashes,parent=str(old),fresh=str(fresh),
        planned=512,inherited=128,additional=384,workers=192,threads=1,rank_prefix='diffusion-expand512-v1:20260930:',
        prior_rows=prior+hold,folding_started=False,training_started=False))
    bad={int(h.query[1:]) for h in read_hsps(old/'references_hsps.tsv') if h.evidence()['excluded']}
    edges={tuple(sorted((int(h.query[1:]),int(h.subject[1:])))) for h in read_hsps(old/'pool_hsps.tsv') if h.query!=h.subject and h.evidence()['excluded']}
    def conflict(row,others):
        return next((p['group_id'] for p in others if row['group_id']==p['group_id'] or row['pdb_id']==p['pdb_id'] or set(row['accessions']).intersection(p['accessions']) or tuple(sorted((row['pool_index'],p['pool_index']))) in edges),None)
    prior_conflicts={r['group_id']:conflict(r,prior+hold) for r in pool if r['pool_index'] not in bad}
    ordered=sorted([r for r in pool if r['pool_index'] not in bad and prior_conflicts[r['group_id']] is None],key=lambda r:hashlib.sha256(('diffusion-expand512-v1:20260930:'+r['group_id']).encode()).hexdigest())
    write_json(root/'candidate_order.json',ordered);write_json(root/'isolation_summary.json',dict(reference_bad=sorted(bad),pair_edges=sorted(edges),prior_conflicts=prior_conflicts))
    original_manifest=json.loads((old/'data_manifest.json').read_text());selected=[];inherited_hashes={}
    for r in inherited:
        g=r['group_id']
        for folder in ['data/examples','chemistry']:
            source=old/folder/g;dest=root/folder/g;shutil.copytree(source,dest)
            for p in source.rglob('*'):
                if p.is_file():
                    rel=str(p.relative_to(old));assert sha256(p)==original_manifest[rel];assert sha256(root/rel)==original_manifest[rel];inherited_hashes[rel]=original_manifest[rel]
        selected.append(r|dict(inherited=True,source=str(root/'data/examples'/g),chemistry_packet=str(root/'chemistry'/g)))
    write_json(root/'inherited_manifest.json',inherited_hashes)
    extra=[];outcomes=[];rejected=[]
    (root/'worker_threads').mkdir()
    with concurrent.futures.ProcessPoolExecutor(max_workers=192,mp_context=multiprocessing.get_context('spawn'),initializer=initialize_expanded_source_worker,initargs=(str(root),)) as executor:
        for offset in range(0,len(ordered),192):
            batch=[]
            for r in ordered[offset:offset+192]:
                match=conflict(r,extra)
                if match:rejected.append(dict(group_id=r['group_id'],reason='new_train_conflict',conflict=match))
                else:batch.append(r)
            values=list(executor.map(qualify_adapter_source,[(r,base,root) for r in batch]));outcomes.extend(values)
            for r,result in zip(batch,values):
                if not result['passed']:rejected.append(dict(group_id=r['group_id'],reason='native_source_preflight'));continue
                if len(extra)>=384:continue
                match=conflict(r,extra)
                if match:rejected.append(dict(group_id=r['group_id'],reason='new_train_conflict',conflict=match));continue
                extra.append(r|dict(role='train',inherited=False,expansion_cohort='full512_v1',source=result['source'],chemistry_packet=result['chemistry_packet'],observed_heavy_fraction=result['observed_heavy_fraction']))
            write_json(root/'preflight.json',outcomes);write_json(root/'selection_provisional.json',selected+extra);write_json(root/'progress.json',dict(additional=len(extra),evaluated=len(outcomes),candidate_pool=len(ordered),seconds=time.monotonic()-begin))
            if len(extra)==384:break
    write_json(root/'selection.json',selected+extra);write_json(root/'rejections.json',rejected)
    files={str(p.relative_to(root)):sha256(p) for folder in ['data','chemistry'] for p in (root/folder).rglob('*') if p.is_file()}
    write_json(root/'data_manifest.json',files)
    write_json(root/'selection_lock.json',dict(complete=len(extra)==384,inherited=128,additional=len(extra),selected=128+len(extra),
        source_lock_sha256=sha256(root/'source_lock.json'),selection_sha256=sha256(root/'selection.json'),preflight_sha256=sha256(root/'preflight.json'),candidate_order_sha256=sha256(root/'candidate_order.json'),
        data_manifest_sha256=sha256(root/'data_manifest.json'),inherited_manifest_sha256=sha256(root/'inherited_manifest.json'),seconds=time.monotonic()-begin,folding_started=False,training_started=False))
    print(json.dumps(dict(complete=len(extra)==384,selected=128+len(extra),additional=len(extra),preflights=len(outcomes))))


if __name__=='__main__':
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--root',type=Path,required=True);a=p.parse_args();assert not torch.cuda.is_available();prepare_expanded_diffusion_sources(a.base,a.root)
