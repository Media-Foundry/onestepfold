#!/usr/bin/env python3
"""Audit every hard candidate and compare equal allocated proposal budgets."""
import argparse,json
from pathlib import Path
import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.hybrid_geometry import GeometryTopology,GeometryRules,hard_accept
from fastglycan.models.soft_sequence_chart import native_sequence_features
from fastglycan.sequence_gate_metrics import contact_objective

p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();root=a.root;lock=json.load(open(root/'lock.json'));results=[]
workers=json.load(open(root/'status.json'))
if len(workers)!=8 or any(w['exit_code']!=0 for w in workers):raise ValueError('batch incomplete or failed')
for worker in workers:
 name=f'{worker["case"]}_s{worker["steps"]}';folder=root/name;report=json.load(open(folder/'report.json'))
 if not report['complete'] or report['lock_sha256']!=sha256(root/'lock.json'):raise ValueError('incomplete or wrong protocol')
 result=dict(name=name,panel=report['case']['panel'],segments={k:v['passed'] for k,v in report['segments'].items()},report_sha256=sha256(folder/'report.json'))
 if report['steps']==2:
  if report['candidates']:raise ValueError('derivative-only reference unexpectedly proposes mutations')
  results.append(result);continue
 if len(report['candidates'])!=2*lock['candidate_budget']:raise ValueError('unmatched candidate budget')
 audited={};geometry_cache={};artifact_hashes={}
 def verify_hard(sequence,hard):
  if sequence in audited:return
  native,atoms=native_sequence_features(sequence);topology=GeometryTopology(atoms,native['ref_pos'].numpy());ca=torch.tensor(np.flatnonzero(atoms.atom_name=='CA'))
  for seed,observation in hard['values'].items():
   path=folder/observation['coordinate_file']
   if sha256(path)!=observation['coordinate_sha256']:raise ValueError('changed coordinate artifact')
   with np.load(path) as d:
    if str(d['sequence'])!=sequence or not np.array_equal(atoms.atom_name,d['atom_names']) or not np.array_equal(atoms.chain_id,d['chain_ids']):raise ValueError('hard sequence/atom mismatch')
    x=torch.tensor(d['coordinates']);task=float(contact_objective(x,ca)[0]);_,geometry=topology.terms(x)
   if abs(task-observation['task'])>2e-5:raise ValueError('task replay disagreement')
   for key,value in geometry.items():
    if abs(value-observation['geometry'][key])>2e-4:raise ValueError('geometry replay disagreement '+key)
   artifact_hashes[path.name]=sha256(path);geometry_cache[sequence,seed]=geometry
  audited[sequence]=True
 verify_hard(report['case']['sequence'],report['baseline'])
 for row in report['candidates']:
  option=row['proposal'];sequence=option['sequence'];original=report['case']['sequence']
  if sum(x!=y for x,y in zip(original,sequence))!=1 or len(sequence)!=len(original):raise ValueError('not a single substitution')
  verify_hard(sequence,row['hard'])
  for seed in ('211','223'):
   b=report['baseline']['values'][seed];c=row['hard']['values'][seed]
   decision=hard_accept(c['task'],b['task'],c['geometry'],b['geometry'])
   if decision!=row['decisions'][seed]:raise ValueError('acceptance policy drift')
 summaries={}
 for arm in ('gradient','random'):
  rows=[r for r in report['candidates'] if r['arm']==arm]
  if len(rows)!=lock['candidate_budget'] or len({r['proposal']['sequence'] for r in rows})!=len(rows):raise ValueError('candidate set mismatch')
  accepted=[r for r in rows if r['decisions']['211']['accepted']]
  chosen=min(accepted,key=lambda r:r['hard']['values']['211']['task']) if accepted else None
  summaries[arm]=dict(proposals=len(rows),accepted_on_selection_noise=len(accepted),retained_on_confirmation_noise=sum(r['decisions']['223']['accepted'] for r in accepted),selected_index=chosen['index'] if chosen else None,selected_confirmed=chosen['decisions']['223']['accepted'] if chosen else False)
 if summaries!=report['arm_summary']:raise ValueError('summary disagreement')
 result.update(arms=summaries,baseline_geometry={seed:hard_accept(-1,0,b['geometry'],b['geometry']) for seed,b in report['baseline']['values'].items()},
               proposal_derivative_gate_passed=report['segments']['sequence_new']['passed'],
               proposal_seconds=report['proposal_seconds'],unique_hard_sequences=len(audited),coordinate_sha256=artifact_hashes)
 results.append(result)
a.out.mkdir(exist_ok=False);write_json(a.out/'report.json',dict(complete=True,lock_sha256=sha256(root/'lock.json'),runs=results,scientific_acceptance=False))
write_json(a.out/'acceptance.json',dict(artifacts_complete=True,report_sha256=sha256(a.out/'report.json')))
