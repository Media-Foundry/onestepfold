#!/usr/bin/env python3
"""All-candidate utility and proposal-noise selection; no confirmation reselection."""
import argparse
import json
from pathlib import Path
import numpy as np
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.mutation_utility import utility_decision

p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);root=p.parse_args().root.resolve()
lock=json.loads((root/'lock.json').read_text());manifest=json.loads((root/'candidates_lock.json').read_text());execution=json.loads((root/'execution.json').read_text())
assert execution['complete'] and execution['success']
assert manifest['lock_sha256']==sha256(root/'lock.json')
lookup={};hashes={}
for i in range(8):
 folder=root/f'worker_{i}';report=json.loads((folder/'report.json').read_text())
 assert report['complete'] and report['candidate_lock_sha256']==sha256(root/'candidates_lock.json')
 assert [(r['parent_index'],r['sequence_index'],r['sequence']) for r in report['records']]==[(t['parent_index'],t['sequence_index'],t['sequence']) for t in manifest['assignments'][i]]
 hashes[str(folder/'report.json')]=sha256(folder/'report.json')
 for row in report['records']:
  key=(row['parent_index'],row['sequence']);assert key not in lookup;lookup[key]=row
  assert set(map(int,row['values']))==set(lock['evaluation_seeds'])
  assert sha256(folder/row['topology_file'])==row['topology_sha256']
  for value in row['values'].values():assert sha256(folder/value['coordinate_file'])==value['coordinate_sha256']
assert len(lookup)==manifest['total_sequences']
# Select using ONLY proposal-noise values, with the prelocked rule. No confirmation
# field is read in this loop. Candidates failing eligibility are never substituted later.
selected={};dev=str(lock['proposal_seed'])
for proposal in manifest['proposals']:
 pi=proposal['parent_index'];parent=lookup[pi,proposal['parent']]['values'][dev]
 selected[str(pi)]={}
 for arm,options in proposal['arms'].items():
  eligible=[]
  for option in options:
   value=lookup[pi,option['sequence']]['values'][dev];chem=value['chemistry']
   if value['task']<parent['task']-1e-4 and chem['zero_severe'] and chem['strict_checked_chirality']:
    eligible.append((value['total'],option['sequence']))
  selected[str(pi)][arm]=min(eligible)[1] if eligible else None
write_json(root/'hard_selection.json',dict(selections=selected,rule='min dev total among dev task+zero severe+strict checked chirality; lexical sequence tie',lock_sha256=sha256(root/'lock.json')))
results=[];all_candidates=[]
for proposal in manifest['proposals']:
 pi=proposal['parent_index'];baseline=lookup[pi,proposal['parent']];record=dict(parent_index=pi,pdb_id=proposal['pdb_id'],length=len(proposal['parent']),positions=proposal['positions'],arms={},parent={})
 for seed in lock['evaluation_seeds']:
  v=baseline['values'][str(seed)];record['parent'][str(seed)]=dict(task=v['task'],total=v['total'],chemistry=v['chemistry'])
 for arm,options in proposal['arms'].items():
  rows=[]
  for option in options:
   candidate=dict(**option,parent_index=pi,pdb_id=proposal['pdb_id'],arm=arm,noises={})
   for seed in lock['evaluation_seeds']:
    value=lookup[pi,option['sequence']]['values'][str(seed)];parent=baseline['values'][str(seed)];chem=value['chemistry']
    u=utility_decision(value['task'],parent['task'],value['geometry'],parent['geometry'])
    candidate['noises'][str(seed)]=dict(task_delta=value['task']-parent['task'],total_delta=value['total']-parent['total'],
        task_improved=u['task_improved'],task_and_legacy_nonregression=u['task_and_nonregression'],
        legacy_full_accepted=u['full']['accepted'],legacy_reasons=u['full']['reasons'],
        task_zero_severe_strict=u['task_improved'] and chem['zero_severe'] and chem['strict_checked_chirality'],
        severe_pairs=value['geometry']['severe_pairs'],severe_rate=value['geometry']['severe_pairs_per_atom'],
        max_penetration=value['geometry']['max_penetration'],ca_wrong=chem['ca_wrong'],side_wrong=chem['side_wrong'])
   rows.append(candidate);all_candidates.append(candidate)
  confirm=[str(s) for s in lock['confirmation_seeds']]
  delta=np.array([np.mean([c['noises'][s]['task_delta'] for s in confirm]) for c in rows]);chosen=selected[str(pi)][arm]
  record['arms'][arm]=dict(candidates=len(rows),confirmation_task_mean=float(delta.mean()),confirmation_task_median=float(np.median(delta)),
       both_noise_task=sum(all(c['noises'][s]['task_improved'] for s in confirm) for c in rows),
       both_noise_task_legacy_nonregression=sum(all(c['noises'][s]['task_and_legacy_nonregression'] for s in confirm) for c in rows),
       both_noise_task_zero_severe_strict=sum(all(c['noises'][s]['task_zero_severe_strict'] for s in confirm) for c in rows),
       both_noise_legacy_full=sum(all(c['noises'][s]['legacy_full_accepted'] for s in confirm) for c in rows),
       selected_on_development=chosen,selected_result=next((c for c in rows if c['sequence']==chosen),None))
  record['arms'][arm]['selected_both_noise_task_zero_severe_strict']=any(c['sequence']==chosen and all(c['noises'][s]['task_zero_severe_strict'] for s in confirm) for c in rows)
 results.append(record)
summary={}
for arm in ['gradient','random']:
 summary[arm]={k:sum(r['arms'][arm][k] for r in results) for k in ['candidates','both_noise_task','both_noise_task_legacy_nonregression','both_noise_task_zero_severe_strict','both_noise_legacy_full','selected_both_noise_task_zero_severe_strict']}
 summary[arm]['mean_parent_mean_task_delta']=float(np.mean([r['arms'][arm]['confirmation_task_mean'] for r in results]))
 summary[arm]['selected_parents']=sum(r['arms'][arm]['selected_on_development'] is not None for r in results)
write_json(root/'analysis.json',dict(complete=True,parents=4,unique_hard_outputs=3*len(lookup),summary=summary,results=results,script_sha256=sha256(Path(__file__)),input_report_hashes=hashes,lock_sha256=sha256(root/'lock.json'),candidate_lock_sha256=sha256(root/'candidates_lock.json'),limitations='Four TRAIN development parents, monomer proxy, no mutant GT, no full chemical or deployment acceptance'))
write_json(root/'candidate_outcomes.json',all_candidates)
print(json.dumps(summary,indent=2))
