#!/usr/bin/env python3
"""Read-only paired comparison after independent audits; no candidate selection."""
import argparse,json
from pathlib import Path
import numpy as np
from fastglycan.paired_teacher_protocol import sha256,write_json
p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--new',type=Path,required=True);a=p.parse_args()
roots=[a.baseline,a.new];reports=[];locks=[]
for root in roots:
 r=json.loads((root/'report.json').read_text());au=json.loads((root/'audit.json').read_text());l=json.loads((root/'lock.json').read_text())
 assert r['complete'] and au['complete'] and au['report_sha256']==sha256(root/'report.json') and r['lock_sha256']==sha256(root/'lock.json')
 reports.append(r);locks.append(l)
assert locks[0]['cases']==locks[1]['cases'] and locks[1]['objective']=='tail'
for key in ['reference_sha256','variants_sha256','topology_sha256']:assert locks[0][key]==locks[1][key]
for name in ['anchored_geometry.py','articulated_output.py','articulated_reference.py','hybrid_geometry.py']:
 hashes=[next(v for k,v in l['source_hashes'].items() if Path(k).name==name) for l in locks];assert hashes[0]==hashes[1]
rows=[]
for before,after in zip(reports[0]['cases'],reports[1]['cases']):
 assert (before['case'],before['arm'],before['seed'])==(after['case'],after['arm'],after['seed'])
 row=dict(case=before['case'],arm=before['arm'],seed=before['seed'],both_success=before['success'] and after['success'])
 if row['both_success']:
  arrays=[]
  for root,r in zip(roots,[before,after]):
   f=root/'cases'/f"{r['case']:02d}"/'coordinates.npz';assert sha256(f)==r['coordinates_sha256'];arrays.append(np.load(f))
  assert np.array_equal(arrays[0]['raw'],arrays[1]['raw']) and np.array_equal(arrays[0]['initial'],arrays[1]['initial'])
  assert before['cis_connections']==after['cis_connections']
  row['same_initial_coordinates_exact']=True
  for label,r in [('mean',before),('tail',after)]:
   m=r['metrics']['final'];row[label]=dict(joint_pass=m['joint_pass'],geometry=m['geometry'],preservation=m['preservation'],
     connection_pass=m['connection_pass'],connection_max=m['connection_max'],sidechain_wrong=m['sidechain_wrong'],
     parameter_changes=r['parameter_changes'],seconds=r['solver_seconds'],closures=sum(h['calls'] for h in r['history']))
 rows.append(row)
write_json(a.new/'comparison.json',dict(source_sha256=sha256(Path(__file__)),baseline_report_sha256=sha256(a.baseline/'report.json'),new_report_sha256=sha256(a.new/'report.json'),
 scope='same-parent development contrast; matched iteration caps, not equal compute or independent-target evidence',cases=rows))
