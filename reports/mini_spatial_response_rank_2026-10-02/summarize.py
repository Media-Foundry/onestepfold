"""Reproducible presentation of the locked spatial diagnostic (no model fitting)."""
import json,gzip,csv,sys
from pathlib import Path
import numpy as np
root=Path(sys.argv[1]);ks=[0,4,8,16,32,64,'full'];variants=['channel','shared']
with gzip.open(root/'report.json.gz','rt') as f:r=json.load(f)
def flatten(d,p=''):
 out={}
 for k,v in d.items():
  if isinstance(v,dict):out.update(flatten(v,p+k+'.'))
  else:out[p+k]=v
 return out
outputs=[];ranks=[]
for site in r['sites']:
 ids={k:site[k] for k in ['parent_index','pdb_id','position']}
 outputs.extend(dict(ids,**flatten(o)) for o in site['outputs']);ranks.extend(dict(ids,**o) for o in site['ranking'])
for file,rows in [('per_prediction.csv.gz',outputs),('ranking_per_site.csv',ranks)]:
 with (gzip.open if file.endswith('.gz') else open)(root/file,'wt') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
extra={};boot=np.random.default_rng(227101).integers(0,10,(10000,10))
for arm,q in r['summary'].items():
 o=[x for x in outputs if x['arm']==arm and not x['is_wt']];rk=[x for x in ranks if x['arm']==arm and x['reference']=='exact' and not x['includes_wt']];tails={}
 for s in r['sites']:
  ss=[x for x in s['outputs'] if x['arm']==arm and not x['is_wt'] and x['fidelity']['local_ca_rmsd_global_frame']>1]
  if ss:tails[f'{s["pdb_id"]}:{s["position"]+1}']=dict(count=len(ss),maximum=max(x['fidelity']['local_ca_rmsd_global_frame'] for x in ss))
 extra[arm]=dict(both_noise_top1_sites=sum(all(x['top1_match'] for x in rk if x['parent_index']==s['parent_index'] and x['position']==s['position']) for s in r['sites']) if rk else None,
  tails=tails,local_quantiles=dict(zip(['p50','p90','p95','p99','max'],np.quantile([x['fidelity.local_ca_rmsd_global_frame'] for x in o],[.5,.9,.95,.99,1]).tolist())),
  zero_severe=sum(x['geometry.severe_pairs']==0 for x in o),strict_chirality=sum(x['geometry.checked_chirality_wrong']==0 for x in o))
mutants=[dict(parent_index=p['parent_index'],position=s['position'],**m) for w in r['workers'] for p in w['parents'] for s in p['sites'] for m in s['mutants']]
energy={};latent_rows=[]
for v in variants:
 for k in ks:
  records=[]
  for m in mutants:
   t=next(t for t in m['evidence']['rows'] if t['variant']==v and t['rank']==k)
   records.append(dict(parent_index=m['parent_index'],position=m['position'],aa=m['aa'],length=m['evidence']['shape'][0],**{key:val for key,val in t.items() if key!='channel_energy_retained'}))
  latent_rows+=records
  per_parent=np.array([np.mean([x['energy_retained'] for x in records if x['parent_index']==i]) for i in range(10)])
  ratios=[x['factor_to_dense'] for x in records]
  energy[f'{v}_k{k}']=dict(mean_energy=float(per_parent.mean()),energy_ci95=np.quantile(per_parent[boot].mean(1),[.025,.975]).tolist(),per_protein_energy=per_parent.tolist(),
    energy_quantiles=dict(zip(['min','p10','p50','p90','max'],np.quantile([x['energy_retained'] for x in records],[0,.1,.5,.9,1]).tolist())),
    factor_to_dense_mean=float(np.mean(ratios)),factor_to_dense_range=[min(ratios),max(ratios)])
with open(root/'spatial_energy_per_mutant.csv','w') as f:
 w=csv.DictWriter(f,fieldnames=list(latent_rows[0]),lineterminator='\n');w.writeheader();w.writerows(latent_rows)
paired={}
for k in ks:
 paired[str(k)]={}
 for metric in ['spearman','top1_match','top1_regret']:
  a=np.array(r['summary'][f'shared_k{k}']['ranking']['exact']['False'][metric]['per_protein']);b=np.array(r['summary'][f'channel_k{k}']['ranking']['exact']['False'][metric]['per_protein']);d=a-b
  paired[str(k)][metric]=dict(shared_minus_channel=float(d.mean()),ci95=np.quantile(d[boot].mean(1),[.025,.975]).tolist(),per_protein=d.tolist())
full=[x for m in mutants for x in m['full_rank_checks']]
timings=dict(decomposition_sum_seconds=sum(m['decomposition_seconds'] for m in mutants),decomposition_mean_seconds=float(np.mean([m['decomposition_seconds'] for m in mutants])),decomposition_max_seconds=max(m['decomposition_seconds'] for m in mutants),
 reconstruction_sum_seconds=sum(x['seconds'] for m in mutants for x in m['reconstruction_times']),
 full_checks=len(full),full_input_max=max(x['input_max_error'] for x in full),full_coordinate_max=max(x['coordinate_max_error'] for x in full),
 counts={key:sum(w['counts'][key] for w in r['workers']) for key in r['workers'][0]['counts']},max_allocated_bytes=max(w['peak_allocated_bytes'] for w in r['workers']))
(root/'supplement.json').write_text(json.dumps(dict(arms=extra,paired=paired,spatial=energy,runtime=timings),indent=2)+'\n')
lines=['# Spatial response compression — full locked panel','','Oracle per-mutant factors, exact target s, WT s_inputs, target chemistry. `R=full` is L, not a fixed rank.','',
 '|Variant|R|Delta-z energy|19-AA rho|Top1 /100|Regret|Local mean A|>1 A /1900|Worst A|New geometry vs Exact / Baseline|Factor/dense scalars|',
 '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
for v in variants:
 for k in ks:
  name=f'{v}_k{k}';s=r['summary'][name];q=s['ranking']['exact']['False'];e=energy[name]
  lines.append(f'|{v}|{k}|{e["mean_energy"]:.6f}|{q["spearman"]["mean"]:.6f}|{round(100*q["top1_match"]["mean"])}|{q["top1_regret"]["mean"]:.6f}|{s["fidelity"]["local_ca_rmsd_global_frame"]["mean"]:.6f}|{s["local_over_1a"]}|{s["worst_local_rmsd"]:.4f}|{s["newly_fails_chemistry"]} / {s["new_compression_chemistry_failure"]}|{e["factor_to_dense_mean"]:.4f}|')
(root/'report.md').write_text('\n'.join(lines)+'\n')
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig,axes=plt.subplots(2,3,figsize=(13,8));x=np.arange(len(ks))
for v in variants:
 ss=[r['summary'][f'{v}_k{k}'] for k in ks];qq=[s['ranking']['exact']['False'] for s in ss]
 values=[[energy[f'{v}_k{k}']['mean_energy'] for k in ks],[q['spearman']['mean'] for q in qq],[q['top1_match']['mean'] for q in qq],[s['local_over_1a'] for s in ss],[s['newly_fails_chemistry'] for s in ss],[energy[f'{v}_k{k}']['factor_to_dense_mean'] for k in ks]]
 for ax,y in zip(axes.flat,values):ax.plot(x,y,'o-',label=v)
for ax,title in zip(axes.flat,['Delta-z energy retained','19-AA Spearman to Exact','Top-1 agreement to Exact','Local RMSD > 1 A / 1900','New geometry failures vs Exact','Factor / dense scalar count']):
 ax.set(title=title,xlabel='Spatial R');ax.set_xticks(x,ks);ax.grid(alpha=.25)
axes[0,0].legend();fig.suptitle('Per-mutant spatial compression; exact target s retained\n50 development sites / 10 proteins; no AA-axis compression',fontsize=11);fig.tight_layout();fig.savefig(root/'spatial_rank_curves.png',dpi=160);fig.savefig(root/'spatial_rank_curves.pdf');plt.close(fig)
print('\n'.join(lines));print(json.dumps(timings,indent=2))
