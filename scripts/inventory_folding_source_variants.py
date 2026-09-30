#!/usr/bin/env python3
"""Read-only catalog census of alternate records for failed source representatives."""
import argparse
import collections
import concurrent.futures
import hashlib
import json
from pathlib import Path
import time

from fastglycan.adapter_sources import scan_adapter_sources


def inventory_folding_source_variants(root):
    begin=time.monotonic();base=root.parent
    assert not (root/'inventory.json').exists()
    extension=base/'folding_source_extension_v1_20260930'
    lock=json.loads((extension/'source_lock.json').read_text());parent=Path(lock['parent'])
    paths=[extension/'source_lock.json',extension/'pool.json',extension/'preflight.json',
        extension/'selection.json',extension/'selection_lock.json',extension/'audit.json',
        parent/'origin/old/pool.json',parent/'preflight_all.json',parent/'rejections.json']
    inputs={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    selected=json.loads((extension/'selection.json').read_text())
    selection_lock=json.loads((extension/'selection_lock.json').read_text())
    assert selection_lock['selection_sha256']==inputs[str(extension/'selection.json')]
    assert len(selected)==selection_lock['selected']==455
    attempted=json.loads((parent/'preflight_all.json').read_text())+json.loads((extension/'preflight.json').read_text())
    by_id={r['group_id']:r for r in attempted};assert len(by_id)==len(attempted)
    pool=json.loads((parent/'origin/old/pool.json').read_text())+json.loads((extension/'pool.json').read_text())
    sources={r['group_id']:r for r in pool};assert len(sources)==len(pool) and set(by_id)<=set(sources)
    selected_ids={r['group_id'] for r in selected};failed={g for g,r in by_id.items() if not r['passed']}
    assert not failed&selected_ids
    excluded_pdbs=set(lock['excluded_pdbs'])|{r['pdb_id'].lower() for r in selected}
    excluded_accessions=set(lock['excluded_accessions'])|{a for r in selected for a in r['accessions']}
    shards=sorted((base/'catalog_v1').glob('shard-*.jsonl.gz'));assert len(shards)==256
    for p in shards:assert hashlib.sha256(p.read_bytes()).hexdigest()==lock['catalog_hashes'][str(p)]
    records=0;alternates={}
    with concurrent.futures.ProcessPoolExecutor(max_workers=8) as workers:
        for part in workers.map(scan_adapter_sources,shards):
            records+=len(part)
            for r in part:
                g=r['group_id']
                if g not in failed:continue
                old=sources[g];assert old['sequence']==r['sequence']
                if (r['pdb_id'],r['source_label_asym_id'])==(old['pdb_id'],old['source_label_asym_id']):continue
                key=(g,r['pdb_id'],r['source_label_asym_id'])
                if key not in alternates or r['assembly_id']<alternates[key]['assembly_id']:alternates[key]=r
    rows=sorted(alternates.values(),key=lambda r:(r['group_id'],r['resolution_high_angstrom'],r['pdb_id'],r['source_label_asym_id']))
    filtered=[];excluded=collections.Counter()
    for r in rows:
        if r['pdb_id'].lower() in excluded_pdbs:excluded['known_pdb']+=1
        elif excluded_accessions.intersection(r['accessions']):excluded['known_accession']+=1
        else:filtered.append(r)
    rejection_counts=collections.Counter(r['reason'] for r in json.loads((parent/'rejections.json').read_text()))
    result=dict(complete=True,seconds=time.monotonic()-begin,inputs=inputs,catalog_hashes=lock['catalog_hashes'],
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        source_eligible_records=records,attempted_groups=len(attempted),failed_representatives=len(failed),
        qualified_but_not_selected=sum(r['passed'] and g not in selected_ids for g,r in by_id.items()),
        prior_selection_reasons=dict(rejection_counts),alternative_records=len(rows),
        alternative_groups=len({r['group_id'] for r in rows}),identity_filtered_records=len(filtered),
        identity_filtered_groups=len({r['group_id'] for r in filtered}),identity_exclusions=dict(excluded),
        variants=filtered,
        scope='Metadata census under existing scan rules, one source chain per assembly. No new GT/native preflight, '
            'BLAST isolation, validation selection, prediction or training. Alternate groups are NOT yet qualified independent proteins.')
    (root/'inventory.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    inventory_folding_source_variants(p.parse_args().root.resolve())
