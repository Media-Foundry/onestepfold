"""Display every predeclared direction and fraction, without a winner filter."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import SymLogNorm

root=Path(__file__).resolve().parent
analysis=json.loads((root/'analysis.json').read_text())
assert analysis['complete'] and len(analysis['states'])==12
names=[('mean_clipped_adam','Mean clipped AdamW'),('mean_unclipped_adam','Mean unclipped AdamW'),
       ('full_gradient_adam','Full-gradient AdamW'),('negative_full_gradient','Equal-norm negative gradient')]
matrix=np.array([[100*state['directions'][name]['fractions'][f]['relative_loss_change']
                  for state in analysis['states']] for name,_ in names for f in (0,1)])
extent=max(abs(matrix.min()),abs(matrix.max()))
fig,ax=plt.subplots(figsize=(15,6.5))
im=ax.imshow(matrix,cmap='RdBu_r',norm=SymLogNorm(linthresh=.05,vmin=-extent,vmax=extent),aspect='auto')
ax.set_xticks(range(12),[f"{s['arm'].title()} / {s['seed']}\nstep {s['step']}" for s in analysis['states']],rotation=45,ha='right',fontsize=9)
ax.set_yticks(range(8),[f'{label}, fraction {f:g}' for _,label in names for f in (.1,1)],fontsize=10)
for i in range(8):
    for j in range(12):
        color='white' if abs(matrix[i,j])>3 else 'black'
        ax.text(j,i,f'{matrix[i,j]:+.3g}',ha='center',va='center',fontsize=8,color=color)
for boundary in (2.5,5.5,8.5):ax.axvline(boundary,color='black',lw=1)
for boundary in (1.5,3.5,5.5):ax.axhline(boundary,color='black',lw=.7)
ax.set_title('Full TRAIN objective change (%) at all fixed states\nBlue: lower loss; red: higher loss. Symmetric-log color scale; exact values annotated.',fontsize=12)
bar=fig.colorbar(im,ax=ax,pad=.02,ticks=[-1000,-10,-.1,0,.1,10,1000])
bar.set_label('100 × (J after − J before) / J before')
fig.text(.01,.015,'Independent frozen-state probes, not a continued optimizer trajectory. No held-protein or S1 evaluation.',fontsize=9)
fig.tight_layout(rect=(0,.05,1,1))
fig.savefig(root/'finite_step_changes.png',dpi=170)
fig.savefig(root/'finite_step_changes.pdf')
plt.close(fig)
