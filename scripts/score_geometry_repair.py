#!/usr/bin/env python3
"""Independent CPU re-evaluation of saved repaired coordinates and paired endpoints."""
import argparse,json
from pathlib import Path
import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.hybrid_geometry import GeometryRules
from fastglycan.mutation_utility import utility_decision
from fastglycan.sequence_gate_metrics import contact_objective
from fastglycan.geometry_repair import preservation
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);out=p.parse_args().out.resolve()
lock=json.loads((out/'lock.json').read_text());source=Path(lock['input'])
assert sha256(source/'report.json')==lock['original_report_sha256']
original=json.loads((source/'report.json').read_text());results={};r=GeometryRules();audit_count=0;max_error=0.
def absolute(g):
 return (g['bond_rmse']<=r.bond_rmse_max and g['peptide_mae']<=r.peptide_mae_max and
 g['chirality_fraction']>=r.chirality_fraction_min and g['severe_pairs_per_atom']<=r.severe_pairs_per_atom_max and g['max_penetration']<=r.max_penetration_max)
for i,item in enumerate(lock['cases']):
 folder=out/'cases'/f'{i:03d}';row=json.loads((folder/'report.json').read_text());assert row['lock_sha256']==sha256(out/'lock.json')
 if row['success']:
  assert sha256(folder/'coordinates.npz')==row['coordinate_sha256'];assert sha256(Path(item['topology']))==item['topology_sha256']
  packet=np.load(folder/'coordinates.npz');top=torch.load(item['topology'],map_location='cpu',weights_only=False)
  for phase in ['raw','repaired']:
   x=torch.tensor(packet[phase],dtype=torch.float32);task,_=contact_objective(x.unsqueeze(0),top['ca']);terms,g=top['topology'].terms(x)
   total=float(task+terms['bond']+2*terms['peptide']+terms['clash']+.2*terms['chirality'])
   err=max([abs(float(task)-row[phase]['task']),abs(total-row[phase]['total'])]+[abs(g[k]-row[phase]['geometry'][k]) for k in g]);assert err<1e-6;max_error=max(err,max_error)
  assert preservation(packet['raw'],packet['repaired'],top['ca'].numpy())==row['preservation'];audit_count+=1
  row['absolute_geometry']=absolute(row['repaired']['geometry'])
 results[item['index'],str(item['seed'])]=row
summary=dict(complete=True,scope='seen development/regression structures; no binder or differentiable oracle claim',
 model_deployment_accepted=False,structures=len(results),success=sum(x['success'] for x in results.values()),
 absolute_geometry=sum(x['success'] and x['absolute_geometry'] for x in results.values()),
 preserved=sum(x['success'] and x['preservation']['accepted'] for x in results.values()),
 joint_geometry_preservation=sum(x['success'] and x['absolute_geometry'] and x['preservation']['accepted'] for x in results.values()),
 raw_absolute_geometry=sum(absolute(c['raw_geometry']) for c in lock['cases']),arms={},candidates=[],
 audit=dict(coordinate_recomputations=audit_count,max_scalar_error=max_error),lock_sha256=sha256(out/'lock.json'))
for arm in ['gradient','random']:
 rows=[]
 for c in original['candidates']:
  if c['arm']!=arm:continue
  decisions={}
  for seed in ['211','200003','200009']:
   h=results[c['hard']['index'],seed];parent=results[0,seed]
   if not h['success'] or not parent['success']:
    decisions[seed]=dict(failed_repair=True,utility=False,full=False,preserved=False);continue
   d=utility_decision(h['repaired']['task'],parent['repaired']['task'],h['repaired']['geometry'],parent['repaired']['geometry'])
   decisions[seed]=dict(failed_repair=False,utility=d['task_and_nonregression'],full=d['full']['accepted'],
      preserved=h['preservation']['accepted'] and parent['preservation']['accepted'],task_delta=d['task_delta'],details=d)
  confirms=[decisions[str(s)] for s in lock['confirmation_seeds']]
  item=dict(arm=arm,proposal=c['proposal'],decisions=decisions,
    confirmed_utility=all(d['utility'] for d in confirms),confirmed_full=all(d['full'] for d in confirms),
    confirmed_full_preserved=all(d['full'] and d['preserved'] for d in confirms))
  rows.append(item);summary['candidates'].append(item)
 summary['arms'][arm]=dict(count=len(rows),**{k:sum(x[k] for x in rows) for k in ['confirmed_utility','confirmed_full','confirmed_full_preserved']})
summary['parent']={s:results[0,s] for s in ['211','200003','200009']}
summary['cases']=[dict(case=i,index=x['index'],seed=x['seed'],success=results[x['index'],str(x['seed'])]['success'],report_sha256=sha256(out/'cases'/f'{i:03d}'/'report.json')) for i,x in enumerate(lock['cases'])]
write_json(out/'report.json',summary)
