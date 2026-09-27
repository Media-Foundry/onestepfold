#!/usr/bin/env python3
"""Accept every reused/new structure packet; never launch a model training job."""
import argparse,json,hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4<<20),b''):h.update(b)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();r=a.root
    selection=json.loads((r/'selection.json').read_text());report=json.loads((r/'selection_report.json').read_text())
    assert sha(r/'selection.json')==report['selection_sha256'] and len(selection)==29897
    oldroot=r.parent/'scratch_structure_inputs_v1_20260927'
    assert sha(oldroot/'acceptance.json')==report['old_acceptance_sha256']
    prior=json.loads((oldroot/'acceptance.json').read_text());expected=dict(prior['prepared_sha256']);assert len(expected)==8320
    source=json.loads((r/'code_v1/source_manifest.json').read_text())
    for n,h in source['files'].items():assert sha(r/'code_v1'/n)==h
    rows=json.loads((r/'new/selection.json').read_text());assert sha(r/'new/selection.json')==report['new_selection_sha256']
    for i in range(16):
        d=json.loads((r/'new'/f'worker_{i}.json').read_text());assert d['complete'] and d['source_manifest_sha256']==sha(r/'code_v1/source_manifest.json')
        assert d['selection_sha256']==report['new_selection_sha256']
        assert [x['group_id'] for x in d['examples']]==[x['group_id'] for x in rows[i::16]]
        for x in d['examples']:
            assert x['group_id'] not in expected;expected[x['group_id']]=x['prepared_sha256']
    assert set(expected)=={x['group_id'] for x in selection}
    def verify(row):
        f=r/'examples'/row['group_id'];assert sha(f/'prepared.json')==expected[row['group_id']]
        d=json.loads((f/'prepared.json').read_text());assert d['complete'] and d['selection']==row
        assert d['mask_independent_exact'] and d['esmc_exact'] and d['projection_independent_exact'] and d['input_provenance']['raw_gt_rebuild_exact']
        for n,h in d['files_sha256'].items():assert sha(f/n)==h,(row['group_id'],n)
        return {'group_id':row['group_id'],'length':len(row['sequence']),'atoms':d['input_provenance']['atom_count'],'missing_residues':d['input_provenance']['missing_residue_count'],'smooth_pairs':d.get('smooth_pair_count'),'reused':row['group_id'] in prior['prepared_sha256']}
    with ThreadPoolExecutor(max_workers=8) as pool:stats=list(pool.map(verify,selection))
    result={'complete':True,'train':29769,'validation':128,'groups':29897,'selection_sha256':report['selection_sha256'],'prepared_sha256':expected,
            'source_manifest_sha256':sha(r/'code_v1/source_manifest.json'),'statistics':stats,'scope':'All selected structure packet file hashes and source-bound sequence/atom/mask/ESMC/raw-GT assertions; no model training',
            'smooth_sidecars_for_reused_packets_complete':False,'dev_primary_prepared':False}
    tmp=r/'acceptance.json.tmp';tmp.write_text(json.dumps(result,indent=2)+'\n');tmp.replace(r/'acceptance.json');print('Accepted 29769 TRAIN +128 historical DEV packets',flush=True)
if __name__=='__main__':main()
