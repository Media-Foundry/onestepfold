#!/usr/bin/env python3
"""Descriptive anatomy of already-audited severe pairs; no new structures."""
import argparse,json
from collections import Counter
from pathlib import Path
from fastglycan.paired_teacher_protocol import sha256,write_json
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
r=json.loads(a.source.read_text());assert r['complete'] and r['structures']==99
backbone={'N','CA','C','O','OXT'}
def category(pair):
 return '-'.join(sorted('backbone' if pair[k]['name'] in backbone else 'sidechain' for k in ['a','b']))
result=dict(scope='posthoc descriptive anatomy of same-parent selected33 sequences, not independent proteins',source_sha256=sha256(a.source),script_sha256=sha256(Path(__file__)),seeds={})
for seed in ['211','200003','200009']:
 counts=Counter();with_backbone=0;parent=None
 for row in r['cases']:
  pairs=[p for p in row['values'][seed]['pairs'] if p['severe']]
  c=Counter(category(p) for p in pairs);counts.update(c);with_backbone+=c['backbone-backbone']>0
  if row['index']==0:parent=dict(counts=dict(c),backbone_pairs=[p for p in pairs if category(p)=='backbone-backbone'])
 result['seeds'][seed]=dict(all_pair_counts=dict(counts),structures_with_backbone_overlap=with_backbone,structures=33,parent=parent)
write_json(a.out,result)
