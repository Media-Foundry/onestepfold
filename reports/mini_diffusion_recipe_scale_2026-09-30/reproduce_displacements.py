from pathlib import Path
import numpy as np,json
r=Path('/media/PM982/onestepfold/diffusion_recipe_evaluation_v1_20260930');out=r.parent/'diffusion_recipe_artifacts_v1_20260930';lock=json.loads((r/'lock.json').read_text())
rows=[]
for item in lock['rows']:
 g=item['group_id'];ca=np.load(Path(lock['source'])/'chemistry'/g/'mapping.npz')['atom_names']=='CA'
 for seed in lock['train_seeds']:
  raw=np.load(r/'examples'/g/f'native_s1_seed{seed}.npy').astype(float)
  for model in ['old_low','old_high','calibrated_low','calibrated_high','native_s2']:
   x=np.load(r/'examples'/g/f'{model}_seed{seed}.npy').astype(float);metrics={}
   for mask,key in [(ca,'ca'),(np.ones(len(x),bool),'heavy')]:
    p=x[mask]-x[mask].mean(0);y=raw[mask]-raw[mask].mean(0);u,_,v=np.linalg.svd(p.T@y);rot=u@np.diag([1,1,np.linalg.det(u@v)])@v
    metrics[key+'_aligned_to_raw_rms']=float(np.sqrt(np.mean(np.sum((p@rot-y)**2,axis=1))))
   rows.append(dict(group_id=g,seed=seed,model=model,**metrics))
summary={}
for model in sorted({x['model'] for x in rows}):
 part=[x for x in rows if x['model']==model]
 summary[model]={key:dict(mean=float(np.mean([x[key] for x in part])),median=float(np.median([x[key] for x in part])),max=max(x[key] for x in part)) for key in ['ca_aligned_to_raw_rms','heavy_aligned_to_raw_rms']}
(out/'aligned_displacements.json').write_text(json.dumps(dict(complete=True,no_new_prediction=True,note='posthoc displacement description, no new acceptance rule; CA and heavy align independently',summary=summary,records=rows),indent=2));print(json.dumps(summary))
