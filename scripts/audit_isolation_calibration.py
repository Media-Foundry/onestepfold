#!/usr/bin/env python3
"""Independent scalar TSV decisions and archived control/selection hash audit."""
import argparse
import hashlib
import json
from pathlib import Path

p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();r=a.root
read=lambda n:json.loads((r/n).read_text())
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
aliases=read('id_aliases.json');lock=read('lock.json');cal=read('calibration_report.json')
assert digest(r/'lock.json')==cal['lock_sha256'] and digest(r/'calibration.tsv')==cal['tsv_sha256']
assert digest(r/'id_aliases.json')==lock['id_aliases_sha256'] and digest(r/'queries.json')==lock['queries_sha256']
for name,v in lock['tools'].items():assert v['sha256']==read('download_provenance.json')['binaries'][name]


def decisions(filename):
    result={}
    for line in (r/filename).read_text().splitlines():
        q,s,ql,sl,e,qa,sa=line.split('\t')
        assert len(qa)==len(sa)
        pairs=[(x,y) for x,y in zip(qa,sa) if x!='-' and y!='-'];n=len(pairs)
        near=(float(e)<=.001 and sum(x==y for x,y in pairs)/max(1,n)>=.3 and n/min(int(ql),int(sl))>=.7)
        if n>=50 and (float(e)<=1e-5 or near):
            result.setdefault(aliases.get(q,q),set()).add(aliases.get(s,s))
    return result


hits=decisions('calibration.tsv')
for row in cal['rows']:
    assert row['intended_recovered']==(row['intended'] in hits.get(row['id'],set()))
    assert set(row['excluded_references'])==hits.get(row['id'],set())
candidate=decisions('candidates.tsv');archived=read('candidate_exclusions.json')
assert set(candidate)==set(archived)
for q,subjects in candidate.items():assert subjects=={x['subject'] for x in archived[q]}
pairs=decisions('pairs.tsv');edges={tuple(sorted((q,s))) for q,subjects in pairs.items() for s in subjects if q!=s}
assert edges=={tuple(x) for x in read('selection_report.json')['pair_edges']}
panel=read('qualified_panel.json');pr=read('qualified_panel_report.json')
assert digest(r/'qualified_panel.json')==pr['panel_sha256']
for i,x in enumerate(panel):
    assert x['group_id'] not in candidate and x['chemistry']['passed']
    remote=Path(x['chemistry']['packet_dir']);folder=r/remote.parent.name/remote.name
    for name in ['mapping.npz','variants.json']:assert digest(folder/name)==x['chemistry']['files'][name]
    for y in panel[:i]:
        assert tuple(sorted((x['group_id'],y['group_id']))) not in edges
        assert not set(x['accessions']) & set(y['accessions'])
out=r/'independent_audit.json';assert not out.exists()
out.write_text(json.dumps(dict(complete=True,calibration_rows=len(cal['rows']),candidate_rejections=len(candidate),
    qualified_panel=len(panel),all_hsp_decisions_recomputed=True,selected_mapping_hashes_verified=True,
    native_pt_bulk_not_replayed=True,source_sha256=digest(Path(__file__))),indent=2)+'\n')
print(len(cal['rows']),len(candidate),len(panel))
