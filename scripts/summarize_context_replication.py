"""Post-close protein-balanced curve summaries; never used for model selection."""
import argparse,csv,json
from collections import defaultdict
from pathlib import Path
import numpy as np
from fastglycan.context_coverage import aa_table_projection
from fastglycan.multicontext_response import noise_selection


def summarize_context_replication(root,out):
    load=lambda p:json.loads(p.read_text())
    assert load(root/'execution.json')['complete'] and load(root/'independent_audit.json')['complete']
    lock=load(root/'lock.json');report=load(root/'report.json');labels=load(root/'evaluation_labels.json')['cases']
    jobs={j['id']:j for j in lock['jobs']};records=[];curve=[]
    def mean_by_protein(rows,key):
        pp=defaultdict(list)
        for r in rows:
            if r[key] is not None:pp[r['parent_index']].append(r[key])
        values={str(k):float(np.mean(v)) for k,v in pp.items()}
        a=list(values.values())
        return dict(mean=float(np.mean(a)) if a else None,median=float(np.median(a)) if a else None,maximum=float(max(a)) if a else None,per_protein=values)
    for r in report['results']:
        job=jobs[r['job']]
        regimes=[]
        if r['step']==32768:regimes.append('fixed_updates')
        if r['step']==job['steps']:regimes.append('fixed_exposures')
        for regime in regimes:
            for ng,v in r['selection']['aggregate'].items():
                records.append(dict(job=r['job'],size=job['size'],architecture=job['architecture'],seed=job['seed'],step=r['step'],regime=regime,
                                    category=r['category'],parent_index=r['parent_index'],pdb_id=r['pdb_id'],position=r['position'],source_aa=r['source_aa'],noise_group=ng,
                                    **v,**r['selection']['cross_noise'],selected_both_new_geometry=all(g['zero_severe_strict_checked_chirality'] for g in r['selected_teacher_geometry'][2:])))
    summaries={}
    for job in lock['jobs']:
        for regime in ('fixed_updates','fixed_exposures'):
            for category in ('train','other_train_pool','confirmation'):
                for source in ('all','A','D','L','T'):
                    rows=[r for r in records if r['job']==job['id'] and r['regime']==regime and r['category']==category and r['noise_group']=='all' and (source=='all' or r['source_aa']==source)]
                    if not rows:continue
                    key=f'{job["id"]}:{regime}:{category}:{source}'
                    item=dict(job=job['id'],regime=regime,category=category,source=source,sites=len(rows),proteins=len({r['parent_index'] for r in rows}),top1=sum(r['top1_match'] for r in rows),selected_geometry=sum(r['selected_both_new_geometry'] for r in rows),metrics={})
                    for m in ('spearman','top1_regret','regret_to_new_best','extra_regret_vs_teacher_old_choice','task_mae','task_rmse','top3_recall','top5_recall'):
                        item['metrics'][m]=mean_by_protein(rows,m)
                    for ng in ('old','new'):
                        rr=[r for r in records if r['job']==job['id'] and r['regime']==regime and r['category']==category and r['noise_group']==ng and (source=='all' or r['source_aa']==source)]
                        item[ng]=mean_by_protein(rr,'spearman')
                    summaries[key]=item
                    curve.append(dict(job=job['id'],size=job['size'],seed=job['seed'],architecture=job['architecture'],regime=regime,category=category,source=source,sites=item['sites'],proteins=item['proteins'],rho=item['metrics']['spearman']['mean'],top1=item['top1'],cross_regret=item['metrics']['regret_to_new_best']['mean'],median_regret=item['metrics']['regret_to_new_best']['median'],max_regret=item['metrics']['regret_to_new_best']['maximum'],delta_mae=item['metrics']['task_mae']['mean'],selected_geometry=item['selected_geometry']))
    tables={str(n):aa_table_projection(load(root/f'train_n{n}.json')['cases'],lock['aa']) for n in (8,16,32)}
    contrasts={}
    for n in (8,16,32):
        for seed in (231301,231303):
            for regime in ('fixed_updates','fixed_exposures'):
                context=summaries[f'n{n}_context_s{seed}:{regime}:confirmation:all'];aa=summaries[f'n{n}_aa_only_s{seed}:{regime}:confirmation:all']
                paired={}
                for m in ('spearman','regret_to_new_best'):
                    x=context['metrics'][m]['per_protein'];y=aa['metrics'][m]['per_protein'];ids=sorted(set(x)&set(y));d=np.array([x[i]-y[i] for i in ids])
                    rng=np.random.default_rng(314159)
                    ci=np.quantile(d[rng.integers(len(d),size=(10000,len(d)))].mean(1),[.025,.975]).tolist() if len(d) else None
                    paired[m]=dict(mean=float(d.mean()) if len(d) else None,descriptive95=ci,per_protein=dict(zip(ids,d.tolist())))
                contrasts[f'n{n}_s{seed}:{regime}']=paired
    exact=[]
    for c in labels:
        ids=[a for a in range(20) if a!=c['wt']];y=np.array(c['target_delta'])[:,ids]
        s=noise_selection(y,y,[lock['aa'][a] for a in ids]);exact.append(dict(parent_index=c['parent_index'],position=c['position'],source_aa=c['source_aa'],role=c['role'],**s['cross_noise']))
    out.mkdir(parents=True,exist_ok=True)
    for name,rows in [('selection',records),('curve',curve),('exact_old_selection',exact)]:
        with (out/f'{name}.csv').open('w') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    (out/'analysis.json').write_text(json.dumps(dict(complete=True,groups=summaries,paired_contrasts=contrasts,training_tables=tables),indent=2,allow_nan=False)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    a=p.parse_args();summarize_context_replication(a.root,a.out)
