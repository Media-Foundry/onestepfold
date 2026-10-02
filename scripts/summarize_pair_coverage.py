"""Descriptive paired coverage summaries; no model or threshold selection."""
import argparse
import csv
import gzip
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from fastglycan.response_coverage import SETS, coverage_stratum


def csv_rows(path, rows):
    rows=list(rows)
    if not rows: return
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n')
        w.writeheader();w.writerows(rows)


def protein_mean(rows, metric):
    groups=defaultdict(list)
    for row in rows:
        if row[metric] is not None: groups[row['parent_index']].append(row[metric])
    values={str(k):float(np.mean(v)) for k,v in groups.items()}
    return dict(mean=float(np.mean(list(values.values()))) if values else None,per_protein=values)


def summarize_pair_coverage(root, out):
    out.mkdir(parents=True,exist_ok=True)
    load=lambda p:json.loads(p.read_text())
    lock=load(root/'evaluation_lock.json')
    with gzip.open(root/'report.json.gz','rt') as f: report=json.load(f)
    assert report['complete']
    inventory={(x['parent_index'],x['position']):x for x in lock['contexts']}
    selections=[];ranks=[];latent=[];polar=[];prior_polar=[];outputs=[]
    for site in report['sites']:
        pi,pos=site['parent_index'],site['position'];inv=inventory[pi,pos]
        base=dict(parent_index=pi,pdb_id=site['pdb_id'],position_1based=pos+1,source_aa=inv['source_aa'],length=inv['length'],common_holdout=inv['common_holdout'],
                  restricted_stratum=inv['strata']['restricted'],expanded_stratum=inv['strata']['expanded'])
        for s in site['selections']:
            for group,value in s['aggregate'].items():
                selections.append(dict(base,arm=s['arm'],reference=s['reference'],noise_group=group,
                                       **value,**s['cross_noise']))
        for r in site['ranking']:ranks.append(dict(base,**r))
        for x in site['outputs']:
            if x['is_wt']:continue
            f=x['compression_fidelity'];g=x['geometry'];ch=x['chirality']
            outputs.append(dict(base,arm=x['arm'],aa=x['aa'],noise=x['noise'],task=x['task'],
                                geometry_pass=g['zero_severe_strict_checked_chirality'],new_failure=x['new_failure'],recovered=x['recovered'],
                                local_rmsd=f['local_ca_rmsd_global_frame'],all_atom_lddt=f['all_atom_lddt'],
                                chirality_wrong=g['checked_chirality_wrong'],
                                minimum_oriented_normalized=ch['minimum_oriented_normalized'],minimum_reference_ratio=ch['minimum_reference_ratio']))
    for record in report['latent']:
        pi,pos=record['parent_index'],record['position'];inv=inventory[pi,pos]
        base=dict(parent_index=pi,pdb_id=inv['pdb_id'],position_1based=pos+1,source_aa=inv['source_aa'],
                  arm=record['arm'],common_holdout=inv['common_holdout'])
        latent.append(dict(base,nmse=record['mean_nmse'],centered_nmse=record['centered_nmse'],
                           energy_ratio=record['energy_ratio'],centered_energy_ratio=record['centered_energy_ratio']))
        for aa,x in zip([a for a in lock['aa'] if a!=inv['source_aa']],record['polar']):polar.append(dict(base,aa=aa,**x))
    prior=load(root/'prior_polar.json')
    for record in prior['records']:
        for value in record['candidates']:
            prior_polar.append(dict(arm=record['arm'],parent_index=record['parent_index'],position_1based=record['position']+1,role=record['role'],**value))
    for name,records in [('selection',selections),('ranking',ranks),('latent',latent),('polar',polar),('prior_polar',prior_polar),('outputs',outputs)]:csv_rows(out/f'{name}.csv',records)
    flat_inventory=[]
    for x in lock['contexts']:
        flat_inventory.append({**{k:v for k,v in x.items() if k!='strata'},**{k+'_stratum':v for k,v in x['strata'].items()}})
    csv_rows(out/'inventory.csv',flat_inventory)
    source0=set('TYAN');source1=set('TYANDLVI')
    trainparents={p for p,i in SETS['restricted']}
    groups={
        'common_holdout':lambda x:x['common_holdout'],
        'common_seen_protein':lambda x:x['common_holdout'] and x['parent_index'] in trainparents,
        'common_unseen_protein':lambda x:x['common_holdout'] and x['parent_index'] not in trainparents,
        'unseen_source_covered_both':lambda x:x['common_holdout'] and x['parent_index'] not in trainparents and x['source_aa'] in source0,
        'unseen_source_newly_covered':lambda x:x['common_holdout'] and x['parent_index'] not in trainparents and x['source_aa'] in source1-source0,
        'unseen_source_uncovered_both':lambda x:x['common_holdout'] and x['parent_index'] not in trainparents and x['source_aa'] not in source1,
        'prior_4pt4':lambda x:x['parent_index']==6,
    }
    for arm in SETS:
        for stratum in ('train','seen_protein_covered_source','seen_protein_uncovered_source','unseen_protein_covered_source','unseen_protein_uncovered_source'):
            groups[arm+'_'+stratum]=lambda x,a=arm,s=stratum:coverage_stratum(lock['rows'],a,x['parent_index'],x['position_1based']-1)==s
    summaries={};table=[]
    for name,predicate in groups.items():
        summaries[name]={}
        for arm in lock['arms']:
            rows=[x for x in selections if x['arm']==arm and x['reference']=='baseline' and x['noise_group']=='all' and predicate(x)]
            if not rows:
                summaries[name][arm]=dict(sites=0,proteins=0,missing=True);continue
            group=dict(sites=len(rows),proteins=len({x['parent_index'] for x in rows}),metrics={})
            for key in ('spearman','top1_regret','task_mae','task_rmse','top3_recall','top5_recall','regret_to_new_best','extra_regret_vs_teacher_old_choice'):
                group['metrics'][key]=protein_mean(rows,key)
            for ng in ('old','new'):
                group[ng]=protein_mean([x for x in selections if x['arm']==arm and x['reference']=='baseline' and x['noise_group']==ng and predicate(x)],'spearman')
            group['top1_sites']=sum(x['top1_match'] for x in rows)
            yy=[x for x in outputs if x['arm']==arm and predicate(x)]
            rms=np.array([x['local_rmsd'] for x in yy])
            group.update(instances=len(yy),geometry_pass=sum(x['geometry_pass'] for x in yy),new_failures=sum(x['new_failure'] for x in yy),
                         recovered=sum(x['recovered'] for x in yy),local_mean=float(rms.mean()),local_p95=float(np.quantile(rms,.95)),
                         local_p99=float(np.quantile(rms,.99)),local_max=float(rms.max()),local_over1=int((rms>1).sum()))
            ll=[x for x in latent if x['arm']==arm and predicate(x)]
            group['latent_nmse']=protein_mean(ll,'nmse')
            summaries[name][arm]=group
            table.append(dict(group=name,arm=arm,sites=group['sites'],proteins=group['proteins'],
                              spearman=group['metrics']['spearman']['mean'],top1=group['top1_sites'],
                              regret=group['metrics']['top1_regret']['mean'],cross_regret=group['metrics']['regret_to_new_best']['mean'],
                              nmse=group['latent_nmse']['mean'],geometry_pass=group['geometry_pass'],new_failures=group['new_failures'],
                              recovered=group['recovered'],local_over1=group['local_over1'],local_max=group['local_max']))
    csv_rows(out/'groups.csv',table)
    # Fixed common unseen panel; pair proteins and average the two initialization seeds.
    # Descriptive bootstrap of DEVELOPMENT proteins, not a confirmatory p-value.
    contrasts={}
    for name in ('common_unseen_protein','unseen_source_covered_both','unseen_source_newly_covered','unseen_source_uncovered_both'):
        contrasts[name]={}
        for metric in ('spearman','regret_to_new_best','task_mae'):
            perarm=[]
            for arm in ('restricted','expanded'):
                maps=[summaries[name][f'{arm}_s{seed}']['metrics'][metric]['per_protein'] for seed in (231301,231303)]
                perarm.append({p:float(np.mean([m[p] for m in maps])) for p in maps[0]})
            keys=sorted(set(perarm[0])&set(perarm[1]));difference=np.array([perarm[1][p]-perarm[0][p] for p in keys])
            rng=np.random.default_rng(314159)
            boot=difference[rng.integers(len(keys),size=(10000,len(keys)))].mean(1)
            contrasts[name][metric]=dict(expanded_minus_restricted=float(difference.mean()),
                                         descriptive_bootstrap95=np.quantile(boot,[.025,.975]).tolist(),
                                         per_protein=dict(zip(keys,difference.tolist())),proteins=len(keys))
    history=[]
    for job in lock['jobs']:
        r=load(root/'runs'/job['id']/'report.json')
        for row in r['history']:
            for m in row['sites']:
                history.append(dict(arm=job['id'],step=row['step'],per_site_exposures=row['step']//10,parent_index=m['parent_index'],
                                    position_1based=m['position']+1,nmse=m['mean_nmse'],centered_nmse=m['centered_nmse']))
    csv_rows(out/'learning_curve.csv',history)
    (out/'analysis.json').write_text(json.dumps(dict(complete=True,groups=summaries,contrasts=contrasts),indent=2,allow_nan=False)+'\n')
    print(json.dumps({name:{arm:{k:v for k,v in g.items() if k in ('sites','proteins','top1_sites','latent_nmse','new_failures','local_max')}|{'rho':g.get('metrics',{}).get('spearman',{}).get('mean')} for arm,g in summaries[name].items()} for name in ('restricted_train','expanded_train','common_unseen_protein','prior_4pt4')},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();summarize_pair_coverage(a.root,a.out)
