#!/usr/bin/env python3
"""CPU-only reanalysis of frozen hard predictions; no new folding calls."""
import argparse,json
from pathlib import Path
from collections import Counter
import numpy as np
import torch
from scipy.stats import spearmanr
from fastglycan.collision_audit import collision_records,verify_exclusions
from fastglycan.paired_teacher_protocol import sha256,write_json
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);root=p.parse_args().root.resolve();out=root/'reanalysis';out.mkdir(exist_ok=True);report=json.loads((root/'report.json').read_text());lock=json.loads((root/'lock.json').read_text());audit=json.loads((root/'audit.json').read_text());assert sha256(root/'report.json')==audit['report_sha256'];byindex={report['parent']['index']:report['parent']}
for c in report['candidates']:byindex[c['hard']['index']]=c['hard']
result=dict(complete=False,source_sha256=sha256(Path(__file__)),original_report_sha256=sha256(root/'report.json'),cases=[],ranking={},model_deployment_accepted=False)
def key(pair):return '|'.join(sorted(f"{a['chain']}:{a['residue']}:{a['name']}" for a in [pair['a'],pair['b']]))
for index,row in sorted(byindex.items()):
 worker=index%lock['workers'];base=root/f'worker{worker}';tf=base/row['topology_file'];assert sha256(tf)==row['topology_sha256'];t=torch.load(tf,map_location='cpu',weights_only=False);top=t['topology'];check=verify_exclusions(top.n,top.bonds.numpy(),top.pairs.numpy());assert check['exact'] and check['duplicates']==0
 names=t['atom_names'];res=t['residue_ids'];chains=t['chain_ids'];identities=[(str(c),int(r),str(n)) for c,r,n in zip(chains,res,names)];assert len(set(identities))==len(identities)
 assert len(row['sequence'])==194 and min(res)==1 and max(res)==194
 radii={'C':1.7,'N':1.55,'O':1.52,'S':1.8};assert np.allclose(top.radii.numpy(),[radii[str(n)[0]] for n in names],rtol=0,atol=1e-7)
 inter=[]
 for i,j in top.bonds.numpy():
  if res[i]!=res[j] or chains[i]!=chains[j]:
   assert chains[i]==chains[j] and abs(int(res[i])-int(res[j]))==1 and {str(names[i]),str(names[j])}=={'C','N'}
   inter.append([int(i),int(j)])
 assert len(inter)==193
 entry=dict(index=index,sequence=row['sequence'],topology_sha256=row['topology_sha256'],exclusions=check,inter_residue_bonds=len(inter),values={})
 for seed,v in row['values'].items():
  f=base/v['coordinate_file'];assert sha256(f)==v['coordinate_sha256'];data=np.load(f)
  for label,expected in [('atom_names',names),('residue_ids',res),('chain_ids',chains)]:assert np.array_equal(data[label],expected)
  pairs=collision_records(data['coordinates'],top,names,res,chains,row['sequence']);maximum=next(x for x in pairs if x['is_maximum']);assert abs(maximum['penetration']-v['geometry']['max_penetration'])<1e-5;assert sum(x['severe'] for x in pairs)==v['geometry']['severe_pairs'];assert all(x['graph_distance'] is None or x['graph_distance']>3 for x in pairs)
  entry['values'][seed]=dict(pairs=pairs,maximum_pair=key(maximum),coordinate_sha256=v['coordinate_sha256'])
 result['cases'].append(entry)
parent=report['parent'];ranked=[c for c in report['candidates'] if c['arm']=='gradient' and c['proposal']['position']==37];scores=[c['proposal']['local_substitution_score'] for c in ranked];components=['task','total','bond','peptide','clash','chirality'];rows=[]
for c in ranked:
 values={}
 for seed,h in c['hard']['values'].items():
  par=parent['values'][seed];values[seed]={k:h[k]-par[k] for k in ['task','total']};values[seed].update({k:h['geometry_terms'][k]-par['geometry_terms'][k] for k in components[2:]})
 values['confirmation_mean']={k:float(np.mean([values[str(s)][k] for s in lock['confirmation_seeds']])) for k in components}
 rows.append(dict(substitution='Y38'+c['proposal']['to_aa'],score=c['proposal']['local_substitution_score'],original_gradient_rank=c['index']+1,deltas=values))
result['ranking']=dict(scope='selected15Y38substitutions only; descriptive posthoc association, not full-space prediction',rows=rows,spearman={seed:{k:float(spearmanr(scores,[r['deltas'][seed][k] for r in rows]).statistic) for k in components} for seed in ['211','200003','200009','confirmation_mean']})
result['max_pair_frequencies']={s:dict(Counter(e['values'][s]['maximum_pair'] for e in result['cases'])) for s in ['211','200003','200009']}
result.update(complete=True,structures=99,sequences=33);write_json(out/'report.json',result)
