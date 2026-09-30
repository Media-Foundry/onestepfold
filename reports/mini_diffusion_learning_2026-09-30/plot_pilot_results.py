from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
r=Path('reports/mini_diffusion_learning_2026-09-30');a=json.loads((r/'terminal/training_audit.json').read_text());s=json.loads((r/'evaluation/summary.json').read_text())['summary']['validation']['models']
fig,axes=plt.subplots(1,3,figsize=(14,4),layout='constrained')
for arm,style in [('gt','-'),('gt_s2','--')]:
 for odd,color,seed in [(True,'#2878a5',600001),(False,'#c45f20',600011)]:
  e=[x for x in a['summary'][arm]['epochs'] if (x['epoch']%2==1)==odd]
  axes[0].plot([x['epoch'] for x in e],[x['mean_loss'] for x in e],style,color=color,label=f'{arm}, noise {seed}')
axes[0].set(xlabel='Epoch',ylabel='Training objective',title='A. Compare within fixed noise')
axes[0].legend(fontsize=7)
labels=['Native S1','Native S2','GT S1','GT+S2 S1'];models=['native_s1','native_s2','gt','gt_s2'];colors=['#777777','#58a45c','#2878a5','#925dad']
v=[s[x]['quality_protein_means']['all_atom_lddt']['mean'] for x in models]
axes[1].scatter(range(4),v,c=colors,s=60);axes[1].set_xticks(range(4),labels);axes[1].set(ylim=(.825,.841),ylabel='All-atom lDDT',title='B. Held-out 32 proteins, two noises')
for i,y in enumerate(v):axes[1].text(i,y+.0003,f'{y:.6f}',ha='center',fontsize=8)
counts=[s[x]['zero_and_strict_instances'] for x in models]
axes[2].bar(labels,counts,color=colors);axes[2].set(ylim=(0,64),ylabel='Instances / 64',title='C. Zero severe clash + checked stereo')
for i,y in enumerate(counts):axes[2].text(i,y+1,str(y),ha='center',fontsize=9)
for ax in axes[1:]:ax.tick_params(axis='x',rotation=25)
fig.savefig(r/'pilot_results.png',dpi=160)
