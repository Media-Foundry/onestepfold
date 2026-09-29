#!/usr/bin/env python3
"""Export a scientific overview from completed independent32 summaries."""
import argparse,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

p=argparse.ArgumentParser();p.add_argument('--report',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=json.loads(a.report.read_text());assert d['complete'];a.out.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False})
fig,axes=plt.subplots(2,2,figsize=(11,8));colors={'raw':'#777777','mean':'#3478b8','tail':'#d36928'};labels=['50–127','128–255','256–511','512–1024'];xx=np.arange(4)
ax=axes[0,0]
for j,m in enumerate(['raw','mean','tail']):
 vals=[]
 for i in range(4):
  x=d['groups'][f'length_stratum_{i}']['geometry']['tail' if m=='raw' else m];vals.append(100*x['raw_pass' if m=='raw' else 'repaired_pass']/x['instances'])
 ax.bar(xx+(j-1)*.25,vals,width=.24,label=m,color=colors[m])
ax.set(xticks=xx,xticklabels=labels,ylabel='Joint geometry pass (%)',ylim=(0,105),title='A. Locked joint checks (24 instances per stratum)');ax.legend(frameon=False,ncol=3)
meta={x['group_id']:x for x in d['instance_rows']};ax=axes[0,1]
for p in d['proteins']:
 x=p['quality']['raw']['all_atom_lddt'];y=p['quality']['tail']['all_atom_lddt']
 if x is None or y is None:continue
 homo=meta[p['group_id']]['source_context']=='homooligomer_chain';ax.scatter(x,y,c=colors['tail'],marker='^' if homo else 'o',s=48 if homo else 25,alpha=.8)
ax.plot([0,1],[0,1],color='gray',lw=1,ls='--');ax.set(xlabel='Raw all-atom lDDT',ylabel='Tail-repaired all-atom lDDT',xlim=(0,1),ylim=(0,1),title='B. Protein means across three fixed noises')
ax=axes[1,0]
labelled={p['group_id'] for p in sorted((p for p in d['proteins'] if p['paired']['tail']['all_atom_lddt'] is not None),key=lambda p:p['paired']['tail']['all_atom_lddt'])[:2]}
for p in d['proteins']:
 v=p['paired']['tail']['all_atom_lddt'];row=meta[p['group_id']]
 if v is None:continue
 homo=row['source_context']=='homooligomer_chain';ax.scatter(row['length'],v,color=colors['tail'],marker='^' if homo else 'o',s=48 if homo else 25)
 if p['group_id'] in labelled:ax.annotate(row['pdb_id'].upper(),(row['length'],v),xytext=(5,5),textcoords='offset points',fontsize=7)
ax.axhline(0,color='gray',lw=1);ax.axhline(-.02,color='#a83232',lw=1,ls='--');ax.set(xlabel='Chain length (residues)',ylabel='Tail − raw all-atom lDDT',title='C. Paired per-protein quality change')
ax=axes[1,1]
for j,m in enumerate(['mean','tail']):
 values=[d['groups'][f'length_stratum_{i}']['repair_cost'][m]['seconds'].get('median',np.nan) for i in range(4)]
 ax.bar(xx+(j-.5)*.35,values,width=.34,color=colors[m],label=m)
ax.set(xticks=xx,xticklabels=labels,ylabel='Median repair process time (s)',title='D. Actual cost; iteration caps are matched');ax.legend(frameon=False)
fig.suptitle('C4/S1 + frozen iterative geometry repair: independent32',fontsize=13)
fig.text(.5,.015,'Triangles: four homooligomer-derived chains. Same 28+4 source panel and all fixed seeds; no best-of-three.\nOperational geometry checks do not imply complete chemical validity, one-step repair, or design utility.',ha='center',fontsize=8)
fig.tight_layout(rect=(0,.055,1,.95));fig.savefig(a.out/'independent32_overview.png',dpi=220);fig.savefig(a.out/'independent32_overview.pdf');plt.close(fig)
