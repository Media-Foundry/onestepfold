#!/usr/bin/env python3
"""Verify identical raw inputs and initial coordinates for all96 paired repairs."""
import argparse,json
from pathlib import Path
import numpy as np
from fastglycan.paired_teacher_protocol import sha256,write_json

p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=a.root
panel=json.loads((r/'panel32.json').read_text());rows=[];missing=[]
for protein in panel:
 g=protein['group_id'];folder=r/'proteins'/g;locks={};reports={}
 for m in ['mean','tail']:
  lp=folder/m/'lock.json';rp=folder/m/'report.json'
  if lp.exists() and rp.exists():locks[m]=json.loads(lp.read_text());reports[m]=json.loads(rp.read_text())
 if len(locks)!=2:missing.append(dict(group_id=g,reason='paired repair locks/reports absent'));continue
 for k in ['reference','reference_sha256','variants','variants_sha256','topology','topology_sha256','cases']:
  assert locks['mean'][k]==locks['tail'][k],('paired input mismatch',g,k)
 for seed in [300007,300017,300023]:
  cases={m:next((x for x in reports[m]['cases'] if x.get('seed')==seed and x.get('success')),None) for m in ['mean','tail']}
  if any(x is None for x in cases.values()):missing.append(dict(group_id=g,seed=seed,reason='paired successful output absent'));continue
  arrays={}
  for m,x in cases.items():
   assert x['lock_sha256']==sha256(folder/m/'lock.json')
   path=folder/m/'cases'/f"{x['case']:02d}"/'coordinates.npz';assert sha256(path)==x['coordinates_sha256']
   with np.load(path) as f:arrays[m]={k:f[k] for k in ['raw','initial','atom_names','residue_ids','chain_ids']}
  for k in arrays['mean']:assert np.array_equal(arrays['mean'][k],arrays['tail'][k]),('paired arrays differ',g,seed,k)
  rows.append(dict(group_id=g,pdb_id=protein['pdb_id'],seed=seed,raw_exact=True,initial_exact=True,identity_exact=True))
write_json(a.out,dict(complete=len(rows)==96 and not missing,checked_pairs=len(rows),expected_pairs=96,missing=missing,rows=rows,script_sha256=sha256(Path(__file__)),scope='exact paired inputs/initial arrays; final outputs are allowed to differ'))
print('checked paired repairs',len(rows),'missing',len(missing))
