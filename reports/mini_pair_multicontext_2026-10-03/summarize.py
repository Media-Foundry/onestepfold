from pathlib import Path
import csv,gzip,json,shutil
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path('/home/husrcf/Code/onestepfold_runtime/pair_multicontext_v1_20261003')
out=Path('reports/mini_pair_multicontext_2026-10-03');out.mkdir(parents=True,exist_ok=True)
lock=json.loads((root/'evaluation_lock.json').read_text())
with gzip.open(root/'report.json.gz','rt') as f:report=json.load(f)
model={x['arm']:dict(seed=x['job']['seed'],step=x['step'],exposures=x['step']//4) for x in lock['checkpoints']}
rankrows=[];selectionrows=[];crossrows=[];instances=[];latent=report['latent'];geometry=[]
reference_latent=[]
for p in sorted(root.glob('reference_metrics_*.json')):
 packet=json.loads(p.read_text());assert packet['complete'];reference_latent += [dict(x,training_replay_error=None) for x in packet['records']]
assert len(reference_latent)==32
latent=latent+reference_latent
(out/'reference_latent_metrics.json').write_text(json.dumps(reference_latent,indent=2))
for site in report['sites']:
 meta={k:site[k] for k in ['parent_index','pdb_id','position','role']};meta['position']+=1
 for r in site['ranking']:rankrows.append(dict(meta,**r))
 for x in site['selections']:
  for key,values in x['aggregate'].items():selectionrows.append(dict(meta,arm=x['arm'],reference=x['reference'],noise_group=key,**values))
  crossrows.append(dict(meta,arm=x['arm'],reference=x['reference'],**x['cross_noise']))
 for x in site['outputs']:
  z=dict(meta,**{k:x[k] for k in ['arm','aa','noise','is_wt','task','new_failure','recovered']})
  for section in ['geometry','fidelity','compression_fidelity']:
   z.update({section+'_'+k:v for k,v in x[section].items()})
  instances.append(z)
  if not x['is_wt'] and (x['new_failure'] or x['recovered']):geometry.append(dict(meta,arm=x['arm'],aa=x['aa'],noise=x['noise'],new_failure=x['new_failure'],recovered=x['recovered'],geometry=x['geometry'],chirality=x['chirality']))
def writecsv(name,rows):
 with (out/name).open('w') as f:
  w=csv.DictWriter(f,list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
writecsv('per_noise_rankings.csv',rankrows);writecsv('mean_noise_selection.csv',selectionrows);writecsv('cross_noise_selection.csv',crossrows);writecsv('per_candidate_metrics.csv',instances)
writecsv('latent_metrics.csv',[{k:v for k,v in x.items() if k!='nmse'} for x in latent])
with gzip.open(out/'geometry_transitions.json.gz','wt') as f:json.dump(geometry,f)
def proteinmean(rows,key):
 values={}
 for r in rows:
  if r[key] is not None:values.setdefault(r['parent_index'],[]).append(r[key])
 return float(np.mean([np.mean(v) for v in values.values()])) if values else None
summary=[]
for role in ['train','unseen_site','unseen_protein']:
 for arm in lock['arms']:
  for group,seeds in [('old',lock['seeds'][:2]),('new',lock['seeds'][2:]),('all',lock['seeds'])]:
   s=[x for x in selectionrows if x['role']==role and x['arm']==arm and x['reference']=='baseline' and x['noise_group']==group]
   r=[x for x in rankrows if x['role']==role and x['arm']==arm and x['reference']=='baseline' and x['noise'] in seeds]
   c=[x for x in instances if x['role']==role and x['arm']==arm and x['noise'] in seeds and not x['is_wt']]
   l=[x for x in latent if x['role']==role and x['arm']==arm]
   base=dict(role=role,arm=arm,noise_group=group,**model.get(arm,dict(seed=None,step=None,exposures=None)),proteins=len(set(x['parent_index'] for x in s)),sites=len(s),instances=len(c),latent_nmse=proteinmean(l,'mean_nmse'),centered_nmse=proteinmean(l,'centered_nmse'),same_noise_rho=proteinmean(r,'spearman'),aggregate_rho=proteinmean(s,'spearman'),aggregate_regret=proteinmean(s,'top1_regret'),aggregate_mae=proteinmean(s,'task_mae'),aggregate_rmse=proteinmean(s,'task_rmse'),aggregate_bias=proteinmean(s,'task_bias'),aggregate_scale=proteinmean(s,'centered_scale_ratio'),top1_sites=sum(x['top1_match'] for x in s),teacher_best_top3_sites=sum(x['teacher_best_in_top3'] for x in s),teacher_best_top5_sites=sum(x['teacher_best_in_top5'] for x in s),local_mean=float(np.mean([x['compression_fidelity_local_ca_rmsd_global_frame'] for x in c])),local_p95=float(np.quantile([x['compression_fidelity_local_ca_rmsd_global_frame'] for x in c],.95)),local_p99=float(np.quantile([x['compression_fidelity_local_ca_rmsd_global_frame'] for x in c],.99)),local_max=max(x['compression_fidelity_local_ca_rmsd_global_frame'] for x in c),local_over1=sum(x['compression_fidelity_local_ca_rmsd_global_frame']>1 for x in c),new_failures=sum(x['new_failure'] for x in c),recovered=sum(x['recovered'] for x in c),geometry_pass=sum(x['geometry_zero_severe_strict_checked_chirality'] for x in c))
   summary.append(base)
writecsv('group_metrics.csv',summary)
fig,axes=plt.subplots(2,3,figsize=(12,6),layout='constrained')
for col,role in enumerate(['train','unseen_site','unseen_protein']):
 for seed in [231301,231303]:
  points=sorted([x for x in summary if x['role']==role and x['seed']==seed and x['noise_group']=='all'],key=lambda x:x['exposures'])
  xx=[x['exposures'] for x in points]
  axes[0,col].plot(xx,[x['latent_nmse'] for x in points],'o-',label=str(seed))
  axes[1,col].plot(xx,[x['aggregate_rho'] for x in points],'o-',label=str(seed))
 for name,style in [('wt_z','--'),('oracle_r32',':')]:
  y=next(x['aggregate_rho'] for x in summary if x['role']==role and x['arm']==name and x['noise_group']=='all');axes[1,col].axhline(y,ls=style,c='gray',label=name)
 axes[0,col].set(title=role,ylabel='Raw Δz NMSE');axes[1,col].set(ylabel='Spearman of four-noise mean scores',xlabel='Full AA-batch exposures / context')
 for row in range(2):axes[row,col].grid(alpha=.2);axes[row,col].legend(fontsize=7)
fig.savefig(out/'learning_and_transfer.png',dpi=160);plt.close(fig)
for name in ['lock.json','evaluation_lock.json','execution.json','audit_execution.json','summary.json','independent_audit.json','coordinate_manifest.json','report.json.gz']:
 if (root/name).exists():shutil.copy2(root/name,out/name)
for p in (root/'runs').glob('*/report.json'):
 dst=out/'runs'/p.parent.name;dst.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dst/p.name)
for p in root.glob('decoder_*/report.json'):
 dst=out/p.parent.name;dst.mkdir(exist_ok=True);shutil.copy2(p,dst/p.name)
print(json.dumps([x for x in summary if x['step']==32768 or x['arm'] in ['wt_z','oracle_r32','baseline']],indent=2))
