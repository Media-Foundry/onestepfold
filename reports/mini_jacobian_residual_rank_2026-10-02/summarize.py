import json,gzip,csv,sys
from pathlib import Path
import numpy as np
root=Path(sys.argv[1])
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
 outputs.extend(dict(ids,**flatten(o)) for o in site['outputs'])
 ranks.extend(dict(ids,**o) for o in site['ranking'])
for file,rows in [('per_prediction.csv.gz',outputs),('ranking_per_site.csv',ranks)]:
 opener=gzip.open if file.endswith('.gz') else open
 with opener(root/file,'wt') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
extra={};boot=np.random.default_rng(227101).integers(0,10,(10000,10))
for arm,q in r['summary'].items():
 o=[x for x in outputs if x['arm']==arm and not x['is_wt']];rk=[x for x in ranks if x['arm']==arm and x['reference']=='exact' and not x['includes_wt']]
 tails={}
 for s in r['sites']:
  ss=[x for x in s['outputs'] if x['arm']==arm and not x['is_wt'] and x['fidelity']['local_ca_rmsd_global_frame']>1]
  if ss:tails[f'{s["pdb_id"]}:{s["position"]+1}']=dict(count=len(ss),maximum=max(x['fidelity']['local_ca_rmsd_global_frame'] for x in ss))
 extra[arm]=dict(both_noise_top1_sites=sum(all(x['top1_match'] for x in rk if x['parent_index']==s['parent_index'] and x['position']==s['position']) for s in r['sites']) if rk else None,
  tails=tails,local_quantiles=dict(zip(['p50','p90','p95','p99','max'],np.quantile([x['fidelity.local_ca_rmsd_global_frame'] for x in o],[.5,.9,.95,.99,1]).tolist())),
  zero_severe=sum(x['geometry.severe_pairs']==0 for x in o),strict_chirality=sum(x['geometry.checked_chirality_wrong']==0 for x in o))
paired={}
for k in [0,1,2,3,5,8,10,12,15,18]:
 a=np.array(r['summary'][f'balanced_k{k}']['ranking']['exact']['False']['spearman']['per_protein']);b=np.array(r['summary'][f'raw_k{k}']['ranking']['exact']['False']['spearman']['per_protein']);d=a-b
 paired[str(k)]=dict(balanced_minus_raw_rho=float(d.mean()),ci95=np.quantile(d[boot].mean(1),[.025,.975]).tolist(),per_protein=d.tolist())
spectra={}
for metric in ['raw','balanced','s','z']:
 c=np.array([s['evidence']['residual_basis']['spectra'][metric]['cumulative_energy'] for w in r['workers'] for p in w['parents'] for s in p['sites']]);spectra[metric]=dict(mean_cumulative=c.mean(0).tolist(),median_k95=float(np.median((c<.95).sum(1)+1)))
full=[m for w in r['workers'] for p in w['parents'] for s in p['sites'] for m in s['mutants']]
(root/'supplement.json').write_text(json.dumps(dict(arms=extra,paired=paired,spectra=spectra),indent=2)+'\n')
print('rows',len(outputs),len(ranks));print('sample mutant keys',full[0].keys())
try:
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 fig,ax=plt.subplots(2,2,figsize=(11,8));ks=[0,1,2,3,5,8,10,12,15,18]
 control=json.load(open((root.parent/'global_response_rank_v1_20261002')/'summary.json'))['summary']
 for v,source in [('raw residual',r['summary']),('balanced residual',r['summary']),('raw direct',control),('balanced direct',control)]:
  metric=v.split()[0];ss=[source[f'{metric}_k{k}'] for k in ks];rr=[x['ranking']['exact']['False'] for x in ss]
  for a,values in zip(ax.flat,[[x['spearman']['mean'] for x in rr],[x['top1_match']['mean'] for x in rr],[x['local_over_1a'] for x in ss],[x['newly_fails_chemistry'] for x in ss]]):a.plot(ks,values,'o-',label=v,markersize=3)
 for a,title in zip(ax.flat,['19-AA Spearman to Exact','Top-1 agreement to Exact','Local RMSD > 1 A / 1900','New geometry failures vs Exact']):a.set(xlabel='K',title=title);a.grid(alpha=.25)
 ax[0,0].legend(fontsize=8);fig.suptitle('Fixed-WT tangent + full residual PCA vs direct PCA; WT s_inputs\nOracle correction from 19 hard teachers; 50 development sites',fontsize=10);fig.tight_layout();fig.savefig(root/'residual_rank_curves.png',dpi=160);fig.savefig(root/'residual_rank_curves.pdf');plt.close(fig)
except ImportError as e:print('plot unavailable',e)
