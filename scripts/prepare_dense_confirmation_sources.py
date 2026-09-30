#!/usr/bin/env python3
"""Fresh32 source selection; no model outputs or training calls."""
import argparse
import concurrent.futures
import hashlib
import json
import multiprocessing
from pathlib import Path
import time
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.sequence_isolation import read_hsps
from prepare_diffusion_training_sources import qualify_adapter_source


def prepare_dense_confirmation_sources(base,root):
    assert not (root/'source_lock.json').exists();start=time.monotonic()
    parent=base/'diffusion_training_sources_v1_20260930'
    audit=json.loads((parent/'audit.json').read_text());oldlock=json.loads((parent/'selection_lock.json').read_text())
    assert audit['verified_sources'] and audit['selection_complete'] and oldlock['complete']
    assert audit['selection_lock_sha256']==sha256(parent/'selection_lock.json')
    assert oldlock['selection_sha256']==sha256(parent/'selection.json')
    for p,d in oldlock['search_hashes'].items():assert sha256(Path(p))==d
    for name in ['prepare_diffusion_training_sources.py','preflight_isolated_chemistry.py']:
        assert sha256(root/'code/scripts'/name)==sha256(parent/'code/scripts'/name)
    source=json.loads((parent/'source_lock.json').read_text());search=json.loads((parent/'search_lock.json').read_text())
    assert sha256(parent/'source_lock.json')==search['source_lock_sha256']
    assert sha256(parent/'pool.json')==search['pool_sha256']
    pool=json.loads((parent/'pool.json').read_text());prior=json.loads((parent/'selection.json').read_text());assert len(prior)==160
    paths=[parent/n for n in ['audit.json','source_lock.json','selection_lock.json','selection.json','pool.json','search_lock.json','references_hsps.tsv','pool_hsps.tsv']]
    hashes={str(p):sha256(p) for p in paths}
    hashes.update({str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.md']})
    (root/'chemistry').mkdir()
    write_json(root/'source_lock.json',dict(parent=str(parent),hashes=hashes,protocol='mini_dense_fresh_confirmation_v1',
        planned=32,bins=[[50,255],[256,1024]],quotas=[16,16],rank_prefix='dense-confirmation-v1:20260930:',
        prior_rows=prior,prior_reference_count=len(source['references']),seeds=[700021,700027],
        candidate_checkpoint_sha256='7fc01820269b6f376f8313b79c4ab2bf8fcfd2a0b2a017a432033a51b73fd829',
        folding_started=False,training_started=False))
    bad={int(h.query[1:]) for h in read_hsps(parent/'references_hsps.tsv') if h.evidence()['excluded']}
    edges={tuple(sorted((int(h.query[1:]),int(h.subject[1:])))) for h in read_hsps(parent/'pool_hsps.tsv') if h.query!=h.subject and h.evidence()['excluded']}
    def conflict(r,other):
        return next((s['group_id'] for s in other if r['group_id']==s['group_id'] or r['pdb_id']==s['pdb_id']
            or set(r['accessions']).intersection(s['accessions']) or tuple(sorted((r['pool_index'],s['pool_index']))) in edges),None)
    prior_conflicts={r['group_id']:conflict(r,prior) for r in pool if r['pool_index'] not in bad}
    eligible=[r for r in pool if r['pool_index'] not in bad and prior_conflicts[r['group_id']] is None]
    ordered=sorted(eligible,key=lambda r:(r['stratum'],hashlib.sha256(('dense-confirmation-v1:20260930:'+r['group_id']).encode()).hexdigest()))
    write_json(root/'candidate_order.json',ordered)
    write_json(root/'isolation_summary.json',dict(reference_bad=sorted(bad),pair_edges=sorted(edges),
        prior_conflicts={g:v for g,v in prior_conflicts.items() if v is not None},eligible=len(eligible)))
    selected=[];outcomes=[];rejected=[];counts=[0,0]
    with concurrent.futures.ProcessPoolExecutor(max_workers=8,mp_context=multiprocessing.get_context('spawn')) as executor:
        for start_index in range(0,len(ordered),16):
            batch=[r for r in ordered[start_index:start_index+16] if counts[r['stratum']]<16]
            if not batch:continue
            results=list(executor.map(qualify_adapter_source,[(r,base,root) for r in batch]));outcomes.extend(results)
            for r,result in zip(batch,results):
                if not result['passed']:
                    rejected.append(dict(group_id=r['group_id'],reason='source_or_native_preflight'));continue
                if counts[r['stratum']]>=16:continue
                match=conflict(r,selected)
                if match:rejected.append(dict(group_id=r['group_id'],reason='new_panel_identity_or_hsp',conflict=match));continue
                selected.append(r|dict(role='validation',confirmation_cohort='dense_v1',source=result['source'],
                    chemistry_packet=result['chemistry_packet'],observed_heavy_fraction=result['observed_heavy_fraction']))
                counts[r['stratum']]+=1
            write_json(root/'preflight.json',outcomes);write_json(root/'selection_provisional.json',selected)
            write_json(root/'progress.json',dict(counts=counts,evaluated=len(outcomes),eligible=len(eligible)))
            if counts==[16,16]:break
    write_json(root/'selection.json',selected);write_json(root/'rejections.json',rejected)
    files={str(p.relative_to(root)):sha256(p) for folder in ['data','chemistry'] for p in (root/folder).rglob('*') if p.is_file()}
    write_json(root/'data_manifest.json',files)
    write_json(root/'selection_lock.json',dict(complete=counts==[16,16],selected=len(selected),stratum_counts=counts,
        selection_sha256=sha256(root/'selection.json'),preflight_sha256=sha256(root/'preflight.json'),
        data_manifest_sha256=sha256(root/'data_manifest.json'),candidate_order_sha256=sha256(root/'candidate_order.json'),
        source_lock_sha256=sha256(root/'source_lock.json'),seconds=time.monotonic()-start,
        folding_started=False,training_started=False))
    print(json.dumps(dict(complete=counts==[16,16],selected=len(selected),counts=counts)),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--root',type=Path,required=True)
    a=p.parse_args();prepare_dense_confirmation_sources(a.base,a.root)
