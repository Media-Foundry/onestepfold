"""Equal-parent descriptive response summaries; no fitting or selection."""
import argparse,json
from collections import defaultdict
from pathlib import Path
import numpy as np
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);root=p.parse_args().root
rows=json.loads((root/'results.json').read_text())['rows'];assert len(rows)==48
summary={};parents=[]
for role in sorted({r['role'] for r in rows}):
 selected=[r for r in rows if r['role']==role];summary[role]={}
 for stage in ('after','increment'):
  for arm in selected[0][stage]:
   for field in ('s','z'):
    for part in ('raw','centered','common'):
     for metric in ('nmse','energy_ratio','cosine'):
      values=defaultdict(list)
      for r in selected:
       v=r[stage][arm][field][part][metric]
       if v is not None:values[r['parent']].append(v)
      by_parent={k:float(np.mean(v)) for k,v in values.items()}
      key=f'{stage}/{arm}/{field}/{part}/{metric}'
      summary[role][key]=dict(mean=float(np.mean(list(by_parent.values()))) if by_parent else None,
         median=float(np.median(list(by_parent.values()))) if by_parent else None,parents=len(by_parent),sites=sum(map(len,values.values())))
      parents.append(dict(role=role,key=key,values=by_parent))
contrasts=[]
for role in summary:
 for field in ('s','z'):
  for part in ('raw','centered','common'):
   for arm in ('single_272001','single_272003','dual_272001','dual_272003'):
    a=next(x['values'] for x in parents if x['role']==role and x['key']==f'after/{arm}/{field}/{part}/nmse')
    b=next(x['values'] for x in parents if x['role']==role and x['key']==f'after/disabled/{field}/{part}/nmse')
    diffs={k:a[k]-b[k] for k in a}
    contrasts.append(dict(role=role,field=field,part=part,arm=arm,mean_nmse_delta=float(np.mean(list(diffs.values()))),
         improved_parents=sum(v<0 for v in diffs.values()),parents=len(diffs),parent_deltas=diffs))
(root/'summary.json').write_text(json.dumps(dict(complete=True,summary=summary,parent_values=parents,contrasts=contrasts,independent_confirmation=False),indent=2)+'\n')
for role,metrics in summary.items():
 print(role)
 for field in ('s','z'):
  for arm in ('disabled','single_272001','single_272003','dual_272001','dual_272003'):
   print(field,arm,{f'{part}_{m}':metrics[f'after/{arm}/{field}/{part}/{m}']['mean'] for part in ('common','centered') for m in ('nmse','cosine')})
