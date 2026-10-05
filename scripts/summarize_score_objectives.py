"""Post-audit summaries; all objectives and seeds retained, no model selection."""
import argparse,json,csv
from pathlib import Path
from collections import defaultdict
import numpy as np
from fastglycan.objective_audit import rank_correlation


def summarize_score_objectives(root):
    load=lambda p:json.loads(p.read_text());assert load(root/'independent_audit.json')['complete']
    lock=load(root/'lock.json');jobs={j['id']:j for j in lock['jobs']};rows=load(root/'report.json')['results'];out=root/'analysis';out.mkdir(exist_ok=True)
    records=[];groups={};contrasts={};traincurves=[];gradient=[]
    def stats(rr,key):
        per=defaultdict(list)
        for r in rr:
            if r[key] is not None:per[r['parent_index']].append(r[key])
        pp={str(k):float(np.mean(v)) for k,v in per.items()};a=list(pp.values())
        return dict(mean=float(np.mean(a)) if a else None,median=float(np.median(a)) if a else None,maximum=float(max(a)) if a else None,
                    per_protein=pp,undefined_sites=sum(r[key] is None for r in rr))
    for r in rows:
        rec={k:r[k] for k in ['job','arm','architecture','seed','category','parent_index','position','pdb_id','source_aa','raw_old_mse','centered_old_mse','selected_aa']}
        for ng in ['old','new','all']:
            s=r['selection']['aggregate'][ng]
            rec.update({f'{ng}_{k}':s[k] for k in ['spearman','top1_match','top1_regret','top3_recall','top5_recall','task_mae','task_rmse']})
        rec.update(r['selection']['cross_noise']);rec['selected_both_new_geometry']=all(g['zero_severe_strict_checked_chirality'] for g in r['selected_teacher_geometry'][2:]);records.append(rec)
    metrics=['all_spearman','old_spearman','new_spearman','regret_to_new_best','extra_regret_vs_teacher_old_choice','all_task_mae','all_task_rmse','raw_old_mse','centered_old_mse']
    for j in jobs:
        for category in ['train','development']:
            for source in ['all','A','D','L','T']:
                rr=[r for r in records if r['job']==j and r['category']==category and (source=='all' or r['source_aa']==source)]
                groups[f'{j}:{category}:{source}']=dict(sites=len(rr),proteins=len({r['parent_index'] for r in rr}),
                    top1=sum(r['all_top1_match'] for r in rr),geometry=sum(r['selected_both_new_geometry'] for r in rr),
                    old_rank_nonpositive=sum(r['old_spearman'] is not None and r['old_spearman']<=0 for r in rr),
                    old_rank_site_median=float(np.median([r['old_spearman'] for r in rr if r['old_spearman'] is not None])) if any(r['old_spearman'] is not None for r in rr) else None,
                    metrics={m:stats(rr,m) for m in metrics})
    pairs=[]
    for seed in [231301,231303]:
        for arch in ['context','aa_only']:
            for x,y in [('B','A'),('C','B'),('C','A')]:pairs.append((f'{x}_{arch}_s{seed}',f'{y}_{arch}_s{seed}'))
        for arm in ['A','B','C']:pairs.append((f'{arm}_context_s{seed}',f'{arm}_aa_only_s{seed}'))
    for x,y in pairs:
        values={}
        for m in ['all_spearman','regret_to_new_best']:
            a=groups[x+':development:all']['metrics'][m]['per_protein'];b=groups[y+':development:all']['metrics'][m]['per_protein'];ids=sorted(set(a)&set(b));d=np.array([a[i]-b[i] for i in ids]);rng=np.random.default_rng(314159)
            values[m]=dict(mean=float(d.mean()) if len(d) else None,descriptive95=np.quantile(d[rng.integers(len(d),size=(10000,len(d)))].mean(1),[.025,.975]).tolist() if len(d) else None,proteins=len(d),per_protein=dict(zip(ids,d.tolist())))
        contrasts[x+' minus '+y]=values
    train=load(root/'train.json')['cases'];heavy={(8,42),(8,60),(8,74)}
    for j in jobs:
        run=load(root/'runs'/j/'report.json')
        for snap in run['history']:
            for c,s in zip(train,snap['sites']):
                ids=[a for a in range(20) if a!=c['wt']];y=np.array(c['target_delta']).mean(0)[ids];p=np.array(s['predicted_delta'])[ids]
                traincurves.append(dict(job=j,step=snap['step'],parent_index=c['parent_index'],position=c['position'],rho_old=rank_correlation(y,p),objective=s['objective'],raw_mse=s['normalized_mse']*jobs[j]['scale']**2,centered_mse=s['centered_mse']*jobs[j]['scale']**2))
        for window in run['gradient_windows']:
            for i,c in enumerate(train):
                gradient.append(dict(job=j,end_step=window['end_step'],parent_index=c['parent_index'],position=c['position'],heavy=(c['parent_index'],c['position']) in heavy,
                                     count=window['counts'][i],**dict(zip(window['keys'],window['sums'][i]))))
    for name,data in [('selection',records),('training_curve',traincurves),('gradient_windows',gradient)]:
        with (out/f'{name}.csv').open('w') as f:
            w=csv.DictWriter(f,fieldnames=list(data[0]),lineterminator='\n');w.writeheader();w.writerows(data)
    (out/'summary.json').write_text(json.dumps(dict(complete=True,groups=groups,paired_contrasts=contrasts,promotion=False),indent=2,allow_nan=False)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);summarize_score_objectives(p.parse_args().root)
