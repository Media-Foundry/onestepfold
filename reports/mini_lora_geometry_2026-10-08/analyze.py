import gzip,json,collections,hashlib
from pathlib import Path
import numpy as np
root=Path('/tmp/lora_geometry_analysis'); result={};detail=[]
for seed in (272001,272003):
 data=json.load(gzip.open(root/f'{seed}.json.gz','rt'))
 site={r['site_key']:r for r in data['sites'] if r['arm']=='exact'}
 rows={(r['label'],r['noise'],r['arm']):r for r in data['outputs']}
 summary={}
 for role in ('train','dev_new_site','dev_unseen_protein'):
  summary[role]={}
  for arm in ('4104_adapted','8208_adapted'):
   selected=[r for r in data['outputs'] if r['role']==role and r['arm']==arm]
   counts=collections.Counter();by_site=collections.defaultdict(collections.Counter);centers=collections.Counter();ratios=[];per_noise=collections.defaultdict(collections.Counter)
   for r in selected:
    b=rows[r['label'],r['noise'],'disabled'];e=rows[r['label'],r['noise'],'exact'];s=site[r['site_key']];name=f"{s['pdb']} {s['original_aa']}{r['position']+1}"
    for q in (r,b,e): assert sum(v<=0 for v in q['reference_oriented_volume_ratio'])==q['geometry']['checked_chirality_wrong']
    new=r['disabled_pass_to_fail'];fix=r['disabled_fail_to_pass']
    counts['new']+=new;counts['fixed']+=fix
    by_site[name]['new']+=new;by_site[name]['fixed']+=fix
    per_noise[r['noise']]['new']+=new;per_noise[r['noise']]['fixed']+=fix
    for label in ('severe_pairs','checked_chirality_wrong'):
     counts['baseline_'+label]+=b['geometry'][label];counts['adapted_'+label]+=r['geometry'][label]
    if new:
     kind=('both' if r['geometry']['severe_pairs'] and r['geometry']['checked_chirality_wrong'] else 'clash' if r['geometry']['severe_pairs'] else 'chirality')
     counts[kind]+=1
     counts['exact_already_failed']+=not e['geometry']['zero_severe_strict_checked_chirality']
     counts['also_failed_at_4104']+=not rows[r['label'],r['noise'],'4104_adapted']['geometry']['zero_severe_strict_checked_chirality']
     flips=[]
     for i,v in enumerate(r['reference_oriented_volume_ratio']):
      if v<=0:
       res=r['center_residues'][i][0];atom=r['center_atom_names'][i][0];key=f"{s['pdb']}:{res}:{atom}";centers[key]+=1
       rb=b['reference_oriented_volume_ratio'][i];ratios.append(rb)
       flips.append(dict(residue=res,atom=atom,mutated_center=res==r['position']+1,baseline_ratio=rb,adapted_ratio=v,exact_ratio=e['reference_oriented_volume_ratio'][i],baseline_signed_volume=b['signed_volumes'][i],adapted_signed_volume=r['signed_volumes'][i]))
     detail.append(dict(seed=seed,role=role,arm=arm,label=r['label'],site=name,aa=r['aa'],noise=r['noise'],kind=kind,flips=flips,geometry=r['geometry'],local_rmsd=r['fidelity']['local_ca_rmsd_global_frame']))
   summary[role][arm]=dict(counts=counts,by_site=by_site,centers=centers,noise=per_noise,baseline_flip_ratio_quantiles=np.quantile(ratios,[0,.25,.5,.75,1]).tolist() if ratios else [],baseline_flip_ratio_below_01=sum(v<.1 for v in ratios))
 result[str(seed)]=summary
(root/'analysis.json').write_text(json.dumps(result,indent=2))
(root/'new_failures.json').write_text(json.dumps(detail,indent=2))
for seed,roles in result.items():
 print('SEED',seed)
 for role,arms in roles.items():
  for arm,r in arms.items():
   print(role,arm,dict(r['counts']), 'noise',dict(r['noise']))
   print('sites',[(k,dict(v)) for k,v in r['by_site'].items() if v['new'] or v['fixed']])
   print('centers',r['centers'].most_common(12),'baseline flip ratio',r['baseline_flip_ratio_quantiles'])
