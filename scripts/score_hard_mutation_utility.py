#!/usr/bin/env python3
"""All-candidate confirmation endpoints, with CPU coordinate and proposal audit."""
import argparse,json
from pathlib import Path
import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.hybrid_proposals import mutation_proposals
from fastglycan.sequence_gate_metrics import contact_objective
from fastglycan.mutation_utility import utility_decision
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);root=p.parse_args().root.resolve();lock=json.loads((root/'lock.json').read_text());manifest=json.loads((root/'candidates.json').read_text());assert json.loads((root/'exit.json').read_text())['success']
pr=json.loads((root/'proposal/report.json').read_text());assert pr['candidate_sha256']==sha256(root/'candidates.json');assert sha256(root/'proposal/gradient.pt')==pr['gradient_sha256'];g=torch.load(root/'proposal/gradient.pt',map_location='cpu',weights_only=False)
p64=g['p'].double();gp64=g['gp'].double();expected=p64*(gp64-(gp64*p64).sum(-1,keepdim=True));eps=torch.finfo(torch.float32).eps;gamma=24*eps/(1-24*eps);bound=gamma*p64.abs()*(gp64.abs()+(gp64.abs()*p64.abs()).sum(-1,keepdim=True));assert bool(((g['gq']-expected).abs()<=bound+torch.finfo(torch.float32).tiny).all());assert sha256(root/'proposal/chain_audit.json')==pr['chain_audit_sha256']
props=mutation_proposals(lock['sequence'],g['gp'],budget=16,seed=lock['random_proposal_seed'])
for arm in props:
 for o in props[arm]:o['local_substitution_score']=o.pop('predicted_delta')
assert props==manifest['arms']
results={};max_error=0.;count=0;artifacts={'candidates.json':sha256(root/'candidates.json'),'proposal/gradient.pt':sha256(root/'proposal/gradient.pt')}
for worker in range(lock['workers']):
 out=root/f'worker{worker}';wr=json.loads((out/'report.json').read_text());assert wr['complete'] and wr['candidate_sha256']==sha256(root/'candidates.json');artifacts[f'worker{worker}/report.json']=sha256(out/'report.json')
 for row in wr['results']:
  assert row['index'] not in results and manifest['sequences'][row['index']]==row['sequence'];assert sha256(out/row['topology_file'])==row['topology_sha256'];top=torch.load(out/row['topology_file'],map_location='cpu',weights_only=False)
  for seed in lock['evaluation_seeds']:
   value=row['values'][str(seed)];file=out/value['coordinate_file'];assert sha256(file)==value['coordinate_sha256'];packet=np.load(file);assert str(packet['sequence'])==row['sequence'];assert np.array_equal(packet['atom_names'],top['atom_names']);assert np.array_equal(packet['residue_ids'],top['residue_ids']);assert np.array_equal(packet['chain_ids'],top['chain_ids']);x=torch.from_numpy(packet['coordinates'])
   task,task_parts=contact_objective(x,top['ca']);terms,geometry=top['topology'].terms(x);total=task+terms['bond']+2*terms['peptide']+terms['clash']+.2*terms['chirality']
   errors=[abs(float(task)-value['task']),abs(float(total)-value['total'])]+[abs(geometry[k]-value['geometry'][k]) for k in geometry]+[abs(float(terms[k])-value['geometry_terms'][k]) for k in terms]
   error=max(errors);assert error<1e-4,(row['index'],seed,error);max_error=max(max_error,error);count+=1;artifacts[str(file.relative_to(root))]=sha256(file)
  artifacts[str((out/row['topology_file']).relative_to(root))]=sha256(out/row['topology_file']);results[row['index']]=row
assert len(results)==len(manifest['sequences']);byseq={row['sequence']:row for row in results.values()};parent=results[0]
report=dict(complete=True,scope='one-parent development utility; not binder success or population advantage',parent=parent,candidates=[],arms={},model_deployment_accepted=False,unique_hard_predictions=count,proposal_seconds=pr['gradient_seconds'],proposal_elapsed_seconds=pr['elapsed_seconds'],hard_sequence_seconds=sum(r['seconds'] for r in results.values()),artifacts=artifacts)
def distribution(x):
 q=np.quantile(x,[0,.25,.5,.75,1]);return dict(zip(['min','p25','median','p75','max'],map(float,q)))|dict(mean=float(np.mean(x)),values=list(map(float,x)))
for arm,options in manifest['arms'].items():
 rows=[]
 for index,option in enumerate(options):
  hard=byseq[option['sequence']];decisions={str(seed):utility_decision(hard['values'][str(seed)]['task'],parent['values'][str(seed)]['task'],hard['values'][str(seed)]['geometry'],parent['values'][str(seed)]['geometry']) for seed in lock['evaluation_seeds']}
  row=dict(arm=arm,index=index,proposal=option,hard=hard,decisions=decisions,confirmed_utility=all(decisions[str(s)]['task_and_nonregression'] for s in lock['confirmation_seeds']),confirmed_full=all(decisions[str(s)]['full']['accepted'] for s in lock['confirmation_seeds']));rows.append(row);report['candidates'].append(row)
 report['arms'][arm]=dict(count=len(rows),confirmed_utility=sum(r['confirmed_utility'] for r in rows),confirmed_full=sum(r['confirmed_full'] for r in rows),confirmation_mean_task_delta=distribution([np.mean([r['decisions'][str(s)]['task_delta'] for s in lock['confirmation_seeds']]) for r in rows]),per_seed={str(s):dict(task_delta=distribution([r['decisions'][str(s)]['task_delta'] for r in rows]),task_improved=sum(r['decisions'][str(s)]['task_improved'] for r in rows),utility=sum(r['decisions'][str(s)]['task_and_nonregression'] for r in rows),full=sum(r['decisions'][str(s)]['full']['accepted'] for r in rows)) for s in lock['evaluation_seeds']})
write_json(root/'report.json',report);write_json(root/'audit.json',dict(complete=True,coordinate_recomputations=count,max_scalar_error=max_error,proposal_manifest_recomputed=True,chain_rule_recomputed=True,report_sha256=sha256(root/'report.json')))
lines=['# One-parent hard-mutation utility','','No reranking or best-of-noise. Both confirmation noises must pass.','','| Arm | Candidates | Mean confirmation task delta | Median | Task + nonregression both noises | Full acceptance both noises |','|---|---:|---:|---:|---:|---:|']
for arm,v in report['arms'].items():lines.append(f"| {arm} | {v['count']} | {v['confirmation_mean_task_delta']['mean']:.8g} | {v['confirmation_mean_task_delta']['median']:.8g} | {v['confirmed_utility']} | {v['confirmed_full']} |")
(root/'report.md').write_text('\n'.join(lines)+'\n')
