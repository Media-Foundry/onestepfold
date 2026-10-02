from pathlib import Path
import json,gzip
import numpy as np
from scipy.spatial.distance import pdist
from fastglycan.adapter_supervision import build_adapter_supervision
r=Path('/home/husrcf/Code/onestepfold_runtime/functional_response_rank_v1_20261002')
with gzip.open(r/'report.json.gz','rt') as f:d=json.load(f)
lock=json.load(open(r/'lock.json'));checks=[]
for pi in range(10):
 site=next(s for s in d['sites'] if s['parent_index']==pi);pos=site['position'];worker=next(i for i,pis in enumerate(lock['assignments']) if pi in pis);aa=next(x['aa'] for x in site['outputs'] if not x['is_wt'])
 label=f'p{pi}_s{pos+1}_{aa}';inv=dict(np.load(r/f'worker_{worker}/{label}_inventory.npz'));co=np.load(r/f'worker_{worker}/{label}_coordinates.npz')['coordinates'];n=co.shape[-2]
 mapping=dict(inv,coordinates=co[0,0],mask=np.ones(n,bool));labels=build_adapter_supervision(mapping,inv['bonds'],str(inv['sequence']));ii,jj=np.triu_indices(n,1);allowed=~np.isin(ii*n+jj,labels['excluded']);centres=labels['centres'].numpy()
 for k in [-1,5]:
  ki=([-1]+lock['ranks']).index(k);x=co[ki,0].astype(float);distance=pdist(x);severe=int(((distance<1)&allowed).sum());a,b,c,e=centres.T;det=np.linalg.det(np.stack([x[b]-x[a],x[c]-x[a],x[e]-x[a]],axis=1));wrong=int((det*labels['volumes'].numpy()<=0).sum())
  recorded=next(v['geometry'] for v in site['outputs'] if v['aa']==aa and v['rank']==k and v['noise']==lock['seeds'][0]);assert severe==recorded['severe_pairs'] and wrong==recorded['checked_chirality_wrong']
  checks.append(dict(parent_index=pi,position=pos,aa=aa,rank=k,severe_pairs=severe,checked_chirality_wrong=wrong))
(r/'geometry_audit.json').write_text(json.dumps(dict(complete=True,method='all-pairs pdist instead of radius query; determinant instead of cross-product volume',comparisons=len(checks),records=checks),indent=2)+'\n')
print('geometry20 checks pass')
