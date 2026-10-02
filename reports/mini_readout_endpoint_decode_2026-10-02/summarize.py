from pathlib import Path
import json,gzip,csv,shutil,hashlib
import numpy as np
from scipy.stats import spearmanr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
r=Path('/home/husrcf/Code/onestepfold_runtime/readout_endpoint_decode_v1_20261002');out=Path('reports/mini_readout_endpoint_decode_2026-10-02');out.mkdir(parents=True,exist_ok=True)
l=json.loads((r/'lock.json').read_text());s=json.loads((r/'summary.json').read_text())['summary']
with gzip.open(r/'functional/endpoints/report.json.gz','rt') as f:site=json.load(f)['sites'][0]
rows=[]
for c in l['checkpoints']:
 j=c['job'];x=s[j['id']];b=x['baseline'];e=x['exact'];tr=x['geometry_transitions']
 rows.append(dict(id=j['id'],architecture=j['architecture'],label=j['label'],seed=j['seed'],raw_nmse=c['terminal']['raw_nmse'],label_nmse=c['terminal']['label_nmse'],baseline_spearman=b['mean_spearman'],exact_spearman=e['mean_spearman'],baseline_top1=b['top1'],exact_top1=e['top1'],baseline_regret=b['mean_regret'],exact_regret=e['mean_regret'],top3_recall=np.mean([q['top3_recall'] for q in b['ranking']]),top5_recall=np.mean([q['top5_recall'] for q in b['ranking']]),local_mean=b['local_rmsd']['mean'],local_p95=b['local_rmsd']['p95'],local_p99=b['local_rmsd']['p99'],local_max=b['local_rmsd']['max'],local_over1=b['local_rmsd']['over1'],all_atom_lddt=b['all_atom_lddt'],ca_lddt=b['ca_lddt'],geometry_pass=x['geometry_pass'],new_failures=len(tr['pass_to_fail']),recovered=len(tr['fail_to_pass']),severe_pairs=x['severe_pairs_total'],chirality_wrong=x['checked_chirality_wrong_total']))
def csvwrite(path,rows):
 with path.open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
csvwrite(out/'terminal_functional.csv',rows)
rankrows=[]
for arm,x in s.items():
 for ref in ['exact','baseline']:rankrows+=x[ref]['ranking']
csvwrite(out/'per_noise_rankings.csv',rankrows)
metricrows=[]
for x in site['outputs']:
 row={k:x[k] for k in ['arm','aa','noise','is_wt','task']}
 for section in ['geometry','fidelity','compression_fidelity']:
  for k,v in x[section].items():
   if isinstance(v,(float,int,str,bool)):row[section+'_'+k]=v
 metricrows.append(row)
csvwrite(out/'per_candidate_metrics.csv',metricrows)
assoc={k:float(spearmanr([x['raw_nmse'] for x in rows],[x[k] for x in rows]).statistic) for k in ['baseline_spearman','baseline_regret','local_mean','new_failures']}
(out/'descriptive_association.json').write_text(json.dumps(dict(n=12,independent=False,interpretation='same site, correlated training seeds/labels; descriptive only',spearman_raw_nmse_vs=assoc),indent=2))
for name in ['lock.json','summary.json','execution.json','replay_audit.json','score_audit.json','coordinate_manifest.json','reference_score_audit.json']:
 if (r/name).exists():shutil.copy2(r/name,out/name)
shutil.copy2(r/'functional/endpoints/report.json.gz',out/'functional_report.json.gz')
shutil.copy2(r/'functional/endpoints/worker_0/report.json',out/'decoder_execution.json')
shutil.copy2(r/'launch_endpoint_audit.py',out/'executed_controller.py')
fig,ax=plt.subplots(1,3,figsize=(12,3.5),layout='constrained')
colors={'free_hidden':'#1873ad','pair':'#dd7a22','channel':'#279464'}
for x in rows:
 for a,key in zip(ax,['baseline_spearman','local_mean','new_failures']):a.scatter(x['raw_nmse'],x[key],color=colors[x['architecture']],marker='o' if x['label']=='raw' else '^',s=45)
for a,y in zip(ax,['19-AA Spearman vs Baseline','Mean local CA RMSD (Å)','New geometry failures / 38']):a.set(xlabel='Raw Δz NMSE',ylabel=y);a.grid(alpha=.2)
ax[0].axhline(s['wt_z']['baseline']['mean_spearman'],ls='--',color='gray',label='WT-z reference');ax[0].legend(fontsize=8)
from matplotlib.lines import Line2D
handles=[Line2D([],[],marker='o',linestyle='',color=c,label=k) for k,c in colors.items()]
fig.legend(handles=handles,loc='outside upper center',ncol=3,frameon=False);fig.savefig(out/'latent_functional.png',dpi=160);plt.close(fig)
print(json.dumps(dict(rows=rows,association=assoc),indent=2))
