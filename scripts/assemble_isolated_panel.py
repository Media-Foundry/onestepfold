#!/usr/bin/env python3
"""Assemble source-qualified provisional panel; never chooses by model scores."""
import argparse
import hashlib
import json
from pathlib import Path

p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--pool',type=Path,required=True);a=p.parse_args()
r=a.root
assert not (r/'qualified_panel.json').exists()
cal=json.loads((r/'calibration_report.json').read_text());assert cal['passed']
bad=json.loads((r/'candidate_exclusions.json').read_text());selection=json.loads((r/'selection_report.json').read_text())
edges={tuple(e) for e in selection['pair_edges']};chem={};sources={}
for folder in ['chemistry','chemistry_remaining']:
    path=r/folder/'report.json';report=json.loads(path.read_text());assert report['complete']
    sources[folder]=hashlib.sha256(path.read_bytes()).hexdigest()
    for row in report['rows']:
        assert row['group_id'] not in chem
        chem[row['group_id']]=dict(row,packet_dir=str(r/folder/row['group_id']))
pool=json.loads(a.pool.read_text());assert set(chem)=={x['group_id'] for x in pool if x['group_id'] not in bad}
chosen=[];pair_rejections=[]
for b in range(4):
    count=0
    for row in pool:
        g=row['group_id']
        if row['stratum']!=b or g in bad or not chem[g]['passed']:continue
        conflict=next((s['group_id'] for s in chosen if set(s['accessions']) & set(row['accessions']) or tuple(sorted((g,s['group_id']))) in edges),None)
        if conflict:pair_rejections.append(dict(group_id=g,conflict=conflict));continue
        chosen.append(dict(row,chemistry=chem[g]));count+=1
        if count==8:break
(r/'qualified_panel.json').write_text(json.dumps(chosen,indent=2)+'\n')
(r/'qualified_panel_report.json').write_text(json.dumps(dict(
    source_chemistry_sha256=sources,calibration_sha256=hashlib.sha256((r/'calibration_report.json').read_bytes()).hexdigest(),
    panel_sha256=hashlib.sha256((r/'qualified_panel.json').read_bytes()).hexdigest(),
    script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    pool_sha256=hashlib.sha256(a.pool.read_bytes()).hexdigest(),
    qualified_candidates=sum(x['passed'] for x in chem.values()),
    scope_exclusions=[x for x in chem.values() if not x['passed']],
    selected=len(chosen),strata_counts=[sum(x['stratum']==b for x in chosen) for b in range(4)],
    pair_rejections=pair_rejections,original_32_size_met=len(chosen)==32,
    status='provisional source-qualified panel; original32 protocol not satisfied; no folding started'),indent=2)+'\n')
print(len(chosen))
