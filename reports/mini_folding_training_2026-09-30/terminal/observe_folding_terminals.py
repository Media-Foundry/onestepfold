import hashlib,json,subprocess,time
from pathlib import Path
import numpy as np
r=Path('/data/user/shuang886/Folding/folding_scale_training_v1_20260930')
audit_bytes=(r/'training_audit.json').read_bytes();audit=json.loads(audit_bytes)
assert audit['complete'] and audit['same_update_exposure_budget'] and audit['initial_probe_replay_exact']
lock=json.loads((r/'lock.json').read_text())
assert hashlib.sha256((r/'lock.json').read_bytes()).hexdigest()==audit['lock_sha256']
scheduler=subprocess.check_output(['sacct','-j','662290,662291,662294','--format=JobID,State,ExitCode,Elapsed','-X','-n','-P'],text=True)
assert len(scheduler.strip().splitlines())==3
assert all('|COMPLETED|0:0|' in x for x in scheduler.strip().splitlines())
expected={(g,s) for g in lock['probe_groups'] for s in lock['training_seeds']}
rows={};hashes={};summaries={}
for arm in ['train128','expanded']:
 for update in [0,2048]:
  p=r/arm/f'probe_{update:04d}/report.json';data=p.read_bytes();a=json.loads(data)
  hashes[str(p)]=hashlib.sha256(data).hexdigest()
  records={(x['group_id'],x['seed']):x for x in a['records']}
  assert len(records)==len(a['records'])==64 and set(records)==expected
  rows[arm,update]=records
  summaries[f'{arm}_{update}']={k:v for k,v in a.items() if k!='records'}
contrasts={}
for name,first,second in [('train128_minus_start',('train128',2048),('train128',0)),('expanded_minus_start',('expanded',2048),('expanded',0)),('expanded_minus_train128',('expanded',2048),('train128',2048))]:
 a=rows[first];b=rows[second];paired=[];instances=[]
 for g in lock['probe_groups']:
  d={k:float(np.mean([a[g,s][k]-b[g,s][k] for s in lock['training_seeds']])) for k in ['all_atom_lddt','ca_lddt']}
  paired.append(dict(group_id=g,**d))
  for s in lock['training_seeds']:
   instances.append(dict(group_id=g,seed=s,delta_aa=a[g,s]['all_atom_lddt']-b[g,s]['all_atom_lddt'],delta_ca=a[g,s]['ca_lddt']-b[g,s]['ca_lddt'],severe_before=b[g,s]['geometry']['severe_pairs'],severe_after=a[g,s]['geometry']['severe_pairs'],strict_before=b[g,s]['geometry']['strict_checked_chirality'],strict_after=a[g,s]['geometry']['strict_checked_chirality']))
 stats={}
 for metric in ['all_atom_lddt','ca_lddt']:
  v=np.array([x[metric] for x in paired]);order=np.sort(v)
  stats[metric]=dict(mean=float(v.mean()),median=float(np.median(v)),p01=float(np.quantile(v,.01)),p05=float(np.quantile(v,.05)),worst5_mean=float(order[:int(np.ceil(.05*len(v)))].mean()),positive=int((v>0).sum()),below_minus005=int((v<-.05).sum()))
 contrasts[name]=dict(stats=stats,protein_means=paired,instances=instances,new_severe_from_zero=sum(x['severe_before']==0 and x['severe_after']>0 for x in instances),lost_strict_stereo=sum(x['strict_before'] and not x['strict_after'] for x in instances))
out=dict(scope='Matched terminal original-TRAIN32 probes only; no held-out quality result or selection',observed_unix=time.time(),scheduler=scheduler,training_audit_sha256=hashlib.sha256(audit_bytes).hexdigest(),training_lock_sha256=audit['lock_sha256'],checkpoints=audit['checkpoints'],summary=summaries,contrasts=contrasts,source_report_hashes=hashes)
print(json.dumps(out,indent=2))
