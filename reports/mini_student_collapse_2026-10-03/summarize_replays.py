from pathlib import Path
import json,csv,numpy as np
root=Path('/home/husrcf/Code/onestepfold_runtime/student_collapse_v1_20261003')
prior=Path('/home/husrcf/Code/onestepfold_runtime/pair_coverage_v1_20261003')
out=Path('reports/mini_student_collapse_2026-10-03');out.mkdir(parents=True,exist_ok=True)
rows=[];grads=[];checks=[]
for worker in range(4):
 report=json.load(open(root/f'probe_{worker}/report.json'));old=json.load(open(prior/'runs'/report['job']/'report.json'))
 assert report['complete'] and report['optimizer_steps']==0
 for record in report['records']:
  snapshot=next(h for h in old['history'] if h['step']==record['step'])
  case=next(x for x in snapshot['sites'] if (x['parent_index'],x['position'])==(record['parent_index'],record['position']))
  error=abs(case['mean_nmse']-record['loss']);assert error<2e-6
  checks.append(error)
  base={k:record[k] for k in ('job','step','parent_index','position')}
  for name,x in record['layers'].items():rows.append(dict(base,layer=name,**{k:v for k,v in x.items() if k!='shape'}))
  for name,x in record['gradients'].items():grads.append(dict(base,branch=name,gradient_norm=x['gradient_sq']**.5,nonzero=x['nonzero'],missing=x['missing'],**record['parameter_changes'][name]))
for name,data in [('layers',rows),('branches',grads)]:
 fields=list(dict.fromkeys(k for row in data for k in row))
 with (out/f'{name}.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(data)
(out/'audit.json').write_text(json.dumps(dict(complete=True,loss_replays=len(checks),max_replay_error=max(checks),optimizer_steps=0,s1_calls=0,c4_calls=0),indent=2)+'\n')
print('diagnostic loss replays',len(checks),'max error',max(checks))
