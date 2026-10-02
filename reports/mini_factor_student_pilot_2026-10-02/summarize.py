import csv,gzip,json,sys
from pathlib import Path
import numpy as np
root=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
with gzip.open(root/'evaluation/report.json.gz','rt') as f:r=json.load(f)
lock=json.load(open(root/'teacher_lock.json'));student=json.load(open(root/'student_lock.json'));meta={x['index']:x for x in lock['rows']};extra={};latent={};timing=[]
for role in ['train','validation']:
 extra[role]={};latent[role]={}
 for arm in ['baseline','wt_z','oracle_r32','student_0','student_1']:
  sets=[s for s in r['sites'] if meta[s['parent_index']]['role']==role]
  extra[role][arm]=dict(both_noise_top1_sites=sum(all(x['top1_match'] for x in s['ranking'] if x['arm']==arm and x['reference']=='exact' and not x['includes_wt']) for s in sets),sites=len(sets))
  transitions=dict(recovered=0,new_failure=0)
  for site in sets:
   base={(x['aa'],x['noise']):x['geometry']['zero_severe_strict_checked_chirality'] for x in site['outputs'] if x['arm']=='baseline' and not x['is_wt']}
   for x in site['outputs']:
    if x['arm']==arm and not x['is_wt']:
     b=base[x['aa'],x['noise']];g=x['geometry']['zero_severe_strict_checked_chirality'];transitions['recovered']+=not b and g;transitions['new_failure']+=b and not g
  extra[role][arm].update(transitions)
 for i,name in enumerate(['wt_z','oracle_r32','student_0','student_1']):
  vals=[(p['parent_index'],m['latent_nmse'][i]) for w in r['workers'] for p in w['parents'] if meta[p['parent_index']]['role']==role for s in p['sites'] for m in s['mutants']]
  latent[role][name]=dict(mean=float(np.mean([x[1] for x in vals])),per_protein={str(pi):float(np.mean([v for p,v in vals if p==pi])) for pi in sorted({p for p,_ in vals})})
for w in r['workers']:
 for p in w['parents']:
  for site in p['sites']:
   timing.append(dict(parent_index=p['parent_index'],position=site['position'],length=len(meta[p['parent_index']]['sequence']),factor20_seconds=site['factor20_seconds'],batch_max_error=site['batch_max_error'],expand19_nonwt_seconds=[sum(m['expand_seconds'][i] for m in site['mutants']) for i in range(2)]))
training=[]
for i in range(2):
 tr=json.load(open(root/f'train_{i}/report.json'));losses=tr['losses'];training.append(dict(seed=tr['seed'],seconds=tr['seconds'],parameters=tr['parameters'],counts=tr['counts'],peak_allocated_bytes=tr['peak_allocated_bytes'],unique_train_endpoints=len({(x['parent_index'],x['position'],x['aa']) for x in losses}),latent_first64=float(np.mean([x['latent'] for x in losses[:64]])),latent_last128=float(np.mean([x['latent'] for x in losses[-128:]]))))
(out/'supplement.json').write_text(json.dumps(dict(roles=extra,latent=latent,timing=timing,training=training),indent=2)+'\n')
lines=['# Factor-only student pilot: exact target s remains oracle','','TRAIN rows evaluate four predeclared fit-probe parents; validation rows evaluate all eight held-out parents.','','|Role|Arm|Latent NMSE|rho|Top1|regret|Local mean A|>1A|Geometry pass|New fail vs Baseline|','|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
for role in ['train','validation']:
 for arm in ['baseline','wt_z','oracle_r32','student_0','student_1']:
  d=r['summary'][role][arm];q=d['ranking']['exact'];n=4*int(d['proteins']);nmse=0 if arm=='baseline' else latent[role][arm]['mean']
  lines.append(f'|{role}|{arm}|{nmse:.4f}|{q["spearman"]["mean"]:.6f}|{round(q["top1_match"]["mean"]*n)}/{n}|{q["top1_regret"]["mean"]:.6f}|{d["local_mean"]["mean"]:.4f}|{d["local_over_1a"]}/{d["instances"]}|{d["geometry_pass"]}/{d["instances"]}|{d["new_geometry_vs_baseline"]}|')
(out/'report.md').write_text('\n'.join(lines)+'\n');print('\n'.join(lines));print(json.dumps(training,indent=2))
rows=[dict(parent_index=s['parent_index'],role=meta[s['parent_index']]['role'],position=s['position'],**x) for s in r['sites'] for x in s['ranking']]
with open(out/'ranking_per_site.csv','w') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig,axes=plt.subplots(1,3,figsize=(12,3.8));arms=['wt_z','oracle_r32','student_0','student_1'];x=np.arange(4)
for j,role in enumerate(['train','validation']):
 d=[r['summary'][role][a] for a in arms]
 for ax,y in zip(axes,[[t['ranking']['exact']['spearman']['mean'] for t in d],[t['ranking']['exact']['top1_match']['mean'] for t in d],[t['new_geometry_vs_baseline']/t['instances'] for t in d]]):ax.bar(x+(j-.5)*.36,y,width=.36,label='TRAIN probe (4)' if role=='train' else 'validation (8)')
for ax,title in zip(axes,['19-AA Spearman','Top1 agreement','New geometry failure fraction']):ax.set_xticks(x,arms,rotation=15);ax.set_title(title)
axes[0].legend();fig.suptitle('Factor-only predictor + oracle s; trained on 16 parents, evaluated on 4 TRAIN probes + 8 validation parents');fig.tight_layout();fig.savefig(out/'pilot_comparison.png',dpi=160);fig.savefig(out/'pilot_comparison.pdf');plt.close(fig)
