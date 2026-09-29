#!/usr/bin/env python3
"""Final descriptive anatomy from already-computed repairs, without new inference."""
import argparse,json
from collections import Counter
from pathlib import Path
import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.repair_outcomes import absolute_failures,chirality_transitions


def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--partial',action='store_true');a=p.parse_args();root=a.root.resolve()
 lock=json.loads((root/'lock.json').read_text());final_file=root/'report.json';final=None
 if not a.partial:
  final=json.loads(final_file.read_text());assert final['complete'] and final['structures']==len(lock['cases'])
 r=dict(complete=not a.partial,scope='same-parent development batch; no independent-protein prevalence',
        expected=len(lock['cases']),lock_sha256=sha256(root/'lock.json'),source_sha256=sha256(Path(__file__)),
        classifier_sha256=sha256(Path(__import__('fastglycan.repair_outcomes',fromlist=['x']).__file__)),cases=[],arms={} if final is None else final['arms'])
 if final:r['final_report_sha256']=sha256(final_file)
 for i,item in enumerate(lock['cases']):
  folder=root/'cases'/f'{i:03d}';f=folder/'report.json'
  if not f.exists():
   assert a.partial;continue
  old=json.loads(f.read_text());assert old['lock_sha256']==r['lock_sha256']
  row=dict(case=i,index=item['index'],seed=item['seed'],success=old['success'],report_sha256=sha256(f))
  if old['success']:
   assert sha256(folder/'coordinates.npz')==old['coordinate_sha256'];assert sha256(Path(item['topology']))==item['topology_sha256']
   data=np.load(folder/'coordinates.npz');top=torch.load(item['topology'],map_location='cpu',weights_only=False);t=top['topology']
   assert np.array_equal(data['repaired'],data['full'][old['audit']['original_indices']])
   chi=chirality_transitions(data['raw'],data['repaired'],t.centres.numpy(),t.volumes.numpy(),top['residue_ids'],top['chain_ids'],item['sequence'])
   # Float32 gate and float64 volume signs must agree on the classified outcomes.
   for phase in ['raw','repaired']:
    fraction=1-chi[phase+'_wrong']/chi['centres']
    assert abs(fraction-old[phase]['geometry']['chirality_fraction'])<1e-12
   def key(pair):return tuple(sorted((x['chain'],x['residue'],x['name']) for x in [pair['a'],pair['b']]))
   pairs={phase:{key(x) for x in old['pairs'][phase] if x['severe']} for phase in ['raw','repaired']}
   row.update(raw_geometry=old['raw']['geometry'],repaired_geometry=old['repaired']['geometry'],
      raw_absolute_failures=absolute_failures(old['raw']['geometry']),absolute_failures=absolute_failures(old['repaired']['geometry']),
      preservation=old['preservation'],task_change_from_own_raw=old['repaired']['task']-old['raw']['task'],chirality=chi,
      collision_pairs=dict(raw=len(pairs['raw']),repaired=len(pairs['repaired']),shared=len(pairs['raw']&pairs['repaired'])),
      force_rms_vector=(old['audit']['force_rms_vector'] if 'force_rms_vector' in old['audit'] else old['audit']['force_rms']),
      force_diagnostic_met=(old['audit']['force_vector_rms_le_10'] if 'force_vector_rms_le_10' in old['audit'] else old['audit']['force_tolerance_met']),seconds=old['seconds'])
   # Legacy archives stored vector RMS only. Preserve its diagnostic meaning.
   row['force_rms_component']=float(old['audit'].get('force_rms_component',row['force_rms_vector']/np.sqrt(3)))
   row['force_component_rms_le_10']=row['force_rms_component']<=10.
   row['force_component_source']='recorded' if 'force_rms_component' in old['audit'] else 'derived_from_archived_vector_rms'
  else:row['error']=old.get('error')
  r['cases'].append(row)
 ok=[x for x in r['cases'] if x['success']]
 r.update(processed=len(r['cases']),successful=len(ok),pending=r['expected']-len(r['cases']),
   absolute_pass=sum(not x['absolute_failures'] for x in ok),
   preserved=sum(x['preservation']['accepted'] for x in ok),
   joint_pass=sum(not x['absolute_failures'] and x['preservation']['accepted'] for x in ok),
   zero_severe=sum(x['collision_pairs']['repaired']==0 for x in ok),
   structures_with_new_CA_flip=sum(any(y['kind']=='new_flip' for y in x['chirality']['rows']) for x in ok),
   failure_counts=dict(Counter(v for x in ok for v in x['absolute_failures'])),
   chirality_transition_counts=dict(Counter(v['kind'] for x in ok for v in x['chirality']['rows'])),
   new_flip_residue_counts=dict(Counter(f"{v['chain']}:{v['residue']}:{v['amino_acid']}" for x in ok for v in x['chirality']['rows'] if v['kind']=='new_flip')))
 if final:
  assert r['absolute_pass']==final['absolute_geometry'] and r['joint_pass']==final['joint_geometry_preservation']
  r['task_distributions']={}
  for arm in final['arms']:
   candidates=[x for x in final['candidates'] if x['arm']==arm]
   values=[float(np.mean([x['decisions'][str(s)]['task_delta'] for s in lock['confirmation_seeds']])) for x in candidates if all(not x['decisions'][str(s)]['failed_repair'] for s in lock['confirmation_seeds'])]
   r['task_distributions'][arm]=dict(evaluable=len(values),missing=len(candidates)-len(values),values=values,
       mean=float(np.mean(values)) if values else None,median=float(np.median(values)) if values else None)
 suffix='.partial' if a.partial else ''
 write_json(root/f'outcome_analysis{suffix}.json',r)
 lines=['# Geometry repair outcomes','','Development/regression batch only; unchanged thresholds; not a design validation.','',
        f"Processed {r['processed']}/{r['expected']}; finite successful repairs {r['successful']}; pending {r['pending']}.",
        f"Zero severe collisions: {r['zero_severe']}; absolute geometry pass: {r['absolute_pass']}; preserved: {r['preserved']}; joint: {r['joint_pass']}.",
        f"Structures with newly inverted archived CA centres: {r['structures_with_new_CA_flip']}.",
        '','Failures: '+json.dumps(r['failure_counts']), 'CA transitions: '+json.dumps(r['chirality_transition_counts']),
        '', 'All counts concern repeated mutations/noises of one parent, not independent proteins.',
        'Finite output does not establish minimizer convergence; force RMS is vector magnitude per atom.',
        'CA signed-volume checks do not cover every stereocentre.']
 if final:
  lines+=['','| Arm | Candidates | Utility both noises | Full both | Full + preservation both |','|---|---:|---:|---:|---:|']
  for arm,v in r['arms'].items():lines.append(f"| {arm} | {v['count']} | {v['confirmed_utility']} | {v['confirmed_full']} | {v['confirmed_full_preserved']} |")
 (root/f'outcome_analysis{suffix}.md').write_text('\n'.join(lines)+'\n')
if __name__=='__main__':main()
