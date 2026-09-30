import hashlib,json,subprocess,time
from pathlib import Path
import numpy as np
r=Path('/data/user/shuang886/Folding/folding_scale_training_v1_20260930')
lock=json.loads((r/'lock.json').read_text()); folder=r/'train128'
report=json.loads((folder/'report.json').read_text())
state=subprocess.check_output(['sacct','-j','662290','--format=JobID,State,ExitCode,Elapsed','-X','-n','-P'],text=True).strip()
assert state.startswith('662290|COMPLETED|0:0|'),state
assert report['complete'] and report['updates']==2048 and report['exposures']==8192
assert not report['validation_read'] and report['excluded_parameters_unchanged']
hashes={}
for name,expected in [('lock.json',report['lock_sha256']),('train128/history.jsonl',report['history_sha256']),('train128/update_2048.pt',report['terminal_sha256'])]:
 p=r/name
 with p.open('rb') as f: actual=hashlib.file_digest(f,'sha256').hexdigest()
 assert actual==expected
 hashes[str(p)]=actual
expected={(g,s) for g in lock['probe_groups'] for s in lock['training_seeds']}
probes=[];initial=None
case='ac4b0d6e10b5fe5b7e79f7e6e692fff3ae7843963ad19f2f14c95a5f69a9f3cf'
for update in lock['probe_updates']:
 p=folder/f'probe_{update:04d}'/'report.json';a=json.loads(p.read_text())
 with p.open('rb') as f: hashes[str(p)]=hashlib.file_digest(f,'sha256').hexdigest()
 rows={(x['group_id'],x['seed']):x for x in a['records']}
 assert len(rows)==len(a['records'])==64 and set(rows)==expected
 for key,x in rows.items():
  p=p.parent/f'{key[0]}_{key[1]}.npy'
  with p.open('rb') as f: actual=hashlib.file_digest(f,'sha256').hexdigest()
  assert actual==x['sha256'] and np.isfinite(np.load(p)).all()
  hashes[str(p)]=actual
 if initial is None: initial=rows
 paired=[]
 for g in lock['probe_groups']:
  paired.append({'group_id':g,'delta_aa':float(np.mean([rows[g,s]['all_atom_lddt']-initial[g,s]['all_atom_lddt'] for s in lock['training_seeds']])), 'delta_ca':float(np.mean([rows[g,s]['ca_lddt']-initial[g,s]['ca_lddt'] for s in lock['training_seeds']]))})
 out={k:v for k,v in a.items() if k!='records'}
 out['paired_protein_means']=paired
 out['positive_aa_proteins']=sum(x['delta_aa']>0 for x in paired)
 out['mean_aa_drop_below_minus005']=sum(x['delta_aa']<-.05 for x in paired)
 out['new_severe_from_zero']=sum(initial[k]['geometry']['severe_pairs']==0 and x['geometry']['severe_pairs']>0 for k,x in rows.items())
 out['lost_strict_stereo']=sum(initial[k]['geometry']['strict_checked_chirality'] and not x['geometry']['strict_checked_chirality'] for k,x in rows.items())
 out['previously_identified_1mv8']=[{k:v for k,v in x.items() if k in ['group_id','seed','all_atom_lddt','ca_lddt','ca_aligned_rmsd','sha256']}|{'severe_pairs':x['geometry']['severe_pairs'],'strict_checked_chirality':x['geometry']['strict_checked_chirality']} for (g,s),x in rows.items() if g==case]
 probes.append(out)
out={'scope':'Completed TRAIN128 only; saved TRAIN32 probe, no model selection or held-out claim; final joint training audit still pending expanded arm','observed_unix':time.time(),'scheduler':state,'report':{k:v for k,v in report.items() if k not in ['selected_names','probes']},'probes':probes,'hashes':hashes}
print(json.dumps(out,indent=2))
