#!/usr/bin/env python3
"""Standalone measured forward curves; lines merely connect sampled alpha values."""
import argparse,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root
fig,axes=plt.subplots(2,3,figsize=(14,8),constrained_layout=True)
colors={'E':'#d62728','R':'#2ca02c','C':'#1f77b4','ER':'#ff7f0e','EC':'#9467bd','RC':'#17becf','ERC':'#111111'}
for row,case in enumerate(['8bzn','control']):
 for source,color in colors.items():
  data=json.load(open(root/(case+'_'+source)/'report.json'));points=[p for p in data['rows'] if not p['legacy_softmax']];x=[p['alpha'] for p in points]
  y=[[p['ca_aligned_rmsd'] for p in points],[p['geometry']['severe_pairs'] for p in points],[p['tracked_distance'] for p in points]]
  for col in range(3):axes[row,col].plot(x,y[col],'-o',color=color,label=source,markersize=3,linewidth=1.3)
 for col,title in enumerate(['CA displacement vs native hard (Å)','Noncovalent pairs <1 Å','Tracked pair distance (Å)']):
  ax=axes[row,col];ax.set_title(case+' — '+title);ax.set_xscale('symlog',linthresh=1e-4);ax.set_xticks([0,1e-4,1e-3,.01,.1,.2581587],['0','1e-4','1e-3','.01','.10','.258']);ax.set_xlabel('Non-native probability mass α');ax.grid(alpha=.2)
axes[0,0].legend(ncol=4,fontsize=8)
fig.suptitle('Fixed-graph C4/S1 forward interpolation; two development cases\nNative hard predictions are references, not experimental ground truth. Lines connect tested points only.')
fig.savefig(root/'interpolation_curves.png',dpi=180);fig.savefig(root/'interpolation_curves.pdf');plt.close(fig)
