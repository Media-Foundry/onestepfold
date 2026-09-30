from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
r=Path(__file__).resolve().parent
new=json.loads((r/'training_training_audit.json').read_text())['summary']
old=json.loads((r.parent/'mini_diffusion_learning_2026-09-30/terminal/training_audit.json').read_text())['summary']['gt_s2']
curves=dict(old_low=old,**new)
colors=dict(old_low='#777777',old_high='#c65536',calibrated_low='#2878a5',calibrated_high='#7e52a0')
fig,axes=plt.subplots(2,3,figsize=(13,7),layout='constrained')
for ax,component in zip(axes.flat,['coordinate','smooth_lddt','bond','chirality','clash','teacher']):
 for arm,data in curves.items():
  for parity,style in [(1,'-'),(0,'--')]:
   epochs=[x for x in data['epochs'] if x['epoch']%2==parity]
   ax.plot([x['epoch'] for x in epochs],[x['parts'][component] for x in epochs],style,color=colors[arm],lw=1.5)
 ax.set(title=component,xlabel='Epoch',ylabel='Raw component mean (unweighted)')
handles=[Line2D([],[],color=color,label=arm) for arm,color in colors.items()]
handles += [Line2D([],[],color='black',ls=style,label=f'Noise {seed}') for seed,style in [(600001,'-'),(600011,'--')]]
fig.legend(handles=handles,loc='outside upper center',ncol=6,fontsize=8)
fig.savefig(r/'training_components.png',dpi=160)
