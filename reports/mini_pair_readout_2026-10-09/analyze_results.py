"""Equal-parent summaries; never use held observations to refit a readout."""
import gzip
import json
from pathlib import Path

import numpy as np


def parent_mean(rows, getter):
    return {p:float(np.mean([getter(r) for r in rows if r['parent']==p])) for p in sorted({r['parent'] for r in rows})}


def interval(first, second):
    assert first.keys()==second.keys()
    delta=np.array([first[k]-second[k] for k in first])
    rng=np.random.default_rng(275001)
    samples=delta[rng.integers(len(delta),size=(10000,len(delta)))].mean(1)
    return dict(mean=float(delta.mean()),interval=np.quantile(samples,[.025,.975]).tolist(),
                improved=int((delta<0).sum()),parents=len(delta),descriptive=True)


def analyze_pair_readout(root):
    result=dict(complete=True,runs={},all_panels_development=True)
    lock=json.loads((root/'readout_lock.json').read_text())
    for initialization in lock['arms']:
        for seed in lock['seeds']:
            folder=root/'runs'/initialization/str(seed)
            ev=json.loads((folder/'evaluation.json').read_text())
            fit=json.loads((folder/'fit.json').read_text())
            with gzip.open(folder/'scores.json.gz','rt') as f:scores=json.load(f)
            latent={};contrasts={}
            for role in sorted({r['role'] for r in ev['sites']}):
                rows=[r for r in ev['sites'] if r['role']==role];latent[role]={};contrasts[role]={}
                methods={'old':lambda r:r['old'], 'full':lambda r:r['full'],
                         'full64':lambda r:r['linear64']['full64'],
                         'centered_fit':lambda r:dict(centered=r['centered_fit'])}
                for method,getter in methods.items():
                    values={}
                    for component in ('raw','common','centered') if method!='centered_fit' else ('centered',):
                        values[component]={}
                        for metric in ('nmse','cosine','energy_ratio'):
                            parents=parent_mean(rows,lambda r:getter(r)[component][metric])
                            values[component][metric]=float(np.mean(list(parents.values())))
                    if method!='centered_fit':
                        parents=parent_mean(rows,lambda r:getter(r)['common']['predicted_energy']/max(getter(r)['raw']['predicted_energy'],1e-300))
                        values['predicted_common_fraction']=float(np.mean(list(parents.values())))
                    latent[role][method]=values
                base=parent_mean(rows,lambda r:r['old']['centered']['nmse'])
                for name,getter in [('full',lambda r:r['full']['centered']['nmse']),('centered_fit',lambda r:r['centered_fit']['nmse'])]:
                    contrasts[role][name+'-old_centered']=interval(parent_mean(rows,getter),base)
            choices={};lookup={(r['site_key'],r['arm']):r for r in scores['sites']}
            for role in scores['summary']:
                choices[role]=[]
                for row in scores['sites']:
                    if row['role']!=role or row['arm']!='full':continue
                    old=lookup[row['site_key'],'old'];base=lookup[row['site_key'],'disabled'];exact=lookup[row['site_key'],'exact']
                    if row['old_selected']!=base['old_selected'] or row['old_selected']!=old['old_selected']:
                        choices[role].append(dict(site=row['site_key'],pdb=row['pdb'],position=row['position']+1,original=row['original_aa'],
                            base_aa=base['old_selected'],old_aa=old['old_selected'],full_aa=row['old_selected'],exact_aa=exact['old_selected'],
                            base_regret=base['old_select_new_regret'],old_regret=old['old_select_new_regret'],full_regret=row['old_select_new_regret'],
                            full_minus_base=row['old_select_new_regret']-base['old_select_new_regret']))
            result['runs'][f'{initialization}_{seed}']=dict(fit=fit['audits'],latent=latent,latent_contrasts=contrasts,
                functional=scores['summary'],functional_contrasts=scores['contrasts'],changed_choices=choices,
                native_fp32_objectives=ev['native_fp32_objectives'],direct_objectives=ev['direct_objectives'],
                max_fp32_head_error=max(r['fp32_full_head_max_error'] for r in ev['numerical']),
                max_centered_layernorm_relation=max(r['centered_layernorm_normal_relative'] for r in ev['numerical']),
                seconds=ev['seconds'])
    (root/'analysis.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    for name,r in result['runs'].items():
        print(name)
        print('fits', {k:{f:v[f] for f in ('rank','objective_old','objective_fit','objective_zero')} for k,v in r['fit'].items()})
        for role,methods in r['latent'].items():
            print(role,'latent',{m:{c:round(v['nmse'],7) for c,v in value.items() if isinstance(v,dict)} for m,value in methods.items()})
            print(role,'functional',{m:{k:round(v[k],7) if isinstance(v[k],float) else v[k] for k in ('spearman','centered_response_rmse','regret','top1','geometry_pass','local_max')} for m,v in r['functional'][role].items() if m in ('disabled','old','full','mismatched')})


if __name__=='__main__':
    analyze_pair_readout(Path(__file__).resolve().parent)
