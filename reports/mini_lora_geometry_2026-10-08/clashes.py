import json,gzip
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from fastglycan.factor_student_data import FactorTeacherStore
from fastglycan.adapter_supervision import build_adapter_supervision
root=Path('/data/user/shuang886/Folding/lora_distributed_v3_20261008/audit')
lock=json.loads((root/'lora_lock.json').read_text());source=Path(lock['source_root']);old=json.loads((source/'lock.json').read_text());store=FactorTeacherStore(old['teachers'])
pre=json.loads((Path(lock['native_root'])/'compensation_preflight.json').read_text());output=[]
for seed in (272001,272003):
 data=json.load(gzip.open(root/f'runs/{seed}/scores.json.gz','rt'));site={r['site_key']:r for r in data['sites'] if r['arm']=='exact'}
 for r in data['outputs']:
  if r['arm']!='8208_adapted' or not r['disabled_pass_to_fail'] or not r['geometry']['severe_pairs']:continue
  label=r['label'];pi=r['parent'];ni=0 if r['noise']==230201 else 1;inv=dict(np.load(store.path(pi,label,'inventory.npz')))
  exact=np.load(store.path(pi,label,'coordinates.npz'))['coordinates'][0,ni]
  seq=store.rows[pi]['sequence'];pos=r['position'];seq=seq[:pos]+r['aa']+seq[pos+1:]
  labels=build_adapter_supervision(dict(inv,coordinates=exact,mask=np.ones(len(exact),bool)),inv['bonds'],seq)
  x=np.load(root/f'runs/{seed}/coordinates/8208_adapted_{label}.npz')['coordinates'][ni].astype(float)
  b=np.load(Path(lock['native_root'])/pre['baseline'][label]['path'])['coordinates'][ni].astype(float)
  pairs=cKDTree(x).query_pairs(1.,output_type='ndarray');pairs=pairs[~np.isin(pairs[:,0]*len(x)+pairs[:,1],labels['excluded'])];pairs=pairs[np.linalg.norm(x[pairs[:,0]]-x[pairs[:,1]],axis=1)<1.]
  assert len(pairs)==r['geometry']['severe_pairs']
  for i,j in pairs:
   output.append(dict(seed=seed,role=r['role'],pdb=site[r['site_key']]['pdb'],site=r['site_key'],label=label,noise=r['noise'],atoms=[f"{inv['residue_ids'][k]}:{inv['atom_names'][k]}" for k in (i,j)],at_mutation=bool(any(inv['residue_ids'][k]==pos+1 for k in (i,j))),baseline_distance=float(np.linalg.norm(b[i]-b[j])),adapted_distance=float(np.linalg.norm(x[i]-x[j])),exact_distance=float(np.linalg.norm(exact[i]-exact[j]))))
Path('/tmp/lora_clashes_result.json').write_text(json.dumps(output,indent=2));print('DONE',len(output))
