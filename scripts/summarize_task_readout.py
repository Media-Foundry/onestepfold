"""Site/parent-weighted direct-score evaluation; no model selection."""
import argparse,csv,json
from pathlib import Path
from collections import defaultdict
import numpy as np
from fastglycan.multicontext_response import noise_selection
from fastglycan.response_coverage import coverage_stratum,SETS


def write_csv(path,rows):
    if not rows:return
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)


def mean_proteins(rows,key):
    values=defaultdict(list)
    for x in rows:
        if x[key] is not None:values[x['parent_index']].append(x[key])
    per={str(p):float(np.mean(v)) for p,v in values.items()}
    return dict(mean=float(np.mean(list(per.values()))) if per else None,
                median=float(np.median(list(per.values()))) if per else None,
                maximum=float(max(per.values())) if per else None,per_protein=per,valid_proteins=len(per))


def summarize_task_readout(root,out):
    out.mkdir(parents=True,exist_ok=True)
    load=lambda p:json.loads(p.read_text())
    lock=load(root/'lock.json');cases=load(root/'evaluation_labels.json')['cases'];report=load(root/'report.json')
    assert report['complete'];inventory={(x['parent_index'],x['position']):x for x in lock['contexts']}
    selections=[];predictions=[];records=[]
    for c in cases:
        pi,pos=c['parent_index'],c['position'];inv=inventory[pi,pos]
        ids=[i for i in range(20) if i!=c['wt']];names=[lock['aa'][i] for i in ids];target=np.array(c['target_delta'])[:,ids]
        models=[(x['job'],x['selection'],np.repeat(np.array(x['predicted_delta'])[None],4,axis=0)) for x in report['results'] if x['parent_index']==pi and x['position']==pos]
        for arm,pred in c['comparators'].items():
            label='legacy_'+arm
            models.append((label,noise_selection(target,np.array(pred)[:,ids],names),np.array(pred)))
        for method,selection,pred in models:
            base=dict(parent_index=pi,pdb_id=c['pdb_id'],position_1based=pos+1,source_aa=inv['source_aa'],
                      common_holdout=inv['common_holdout'],restricted_stratum=inv['strata']['restricted'],expanded_stratum=inv['strata']['expanded'],method=method)
            chosen=lock['aa'].index(selection['cross_noise']['student_old_choice'])
            gg=[c['teacher_geometry'][n][chosen] for n in (2,3)]
            old_choice_native_task=np.array(c['target_delta'])[2:,chosen]+np.array(c['wt_task'])[2:]
            geom=dict(selected_both_new_checked_geometry=all(x['zero_severe_strict_checked_chirality'] for x in gg),
                      selected_new_wrong_chirality_sum=sum(x['checked_chirality_wrong'] for x in gg))
            for ng,val in selection['aggregate'].items():
                selections.append(dict(base,noise_group=ng,**val,**selection['cross_noise'],**geom))
            records.append(dict(base,selection=selection,geometry=geom))
            for n,noise in enumerate(lock['seeds']):
                for j in ids:predictions.append(dict(base,noise=noise,aa=lock['aa'][j],predicted_delta=float(pred[n,j]),teacher_delta=c['target_delta'][n][j]))
    write_csv(out/'selection.csv',selections);write_csv(out/'predictions.csv',predictions)
    trainparents={p for p,i in SETS['restricted']}
    groups={'unseen_protein':lambda x:x['common_holdout'] and x['parent_index'] not in trainparents,
            'common_seen_site':lambda x:x['common_holdout'] and x['parent_index'] in trainparents,
            'prior_4pt4':lambda x:x['parent_index']==6,
            'unseen_covered_both':lambda x:x['common_holdout'] and x['parent_index'] not in trainparents and x['source_aa'] in 'TYAN',
            'unseen_newly_covered':lambda x:x['common_holdout'] and x['parent_index'] not in trainparents and x['source_aa'] in 'DLVI',
            'unseen_uncovered_both':lambda x:x['common_holdout'] and x['parent_index'] not in trainparents and x['source_aa'] not in 'TYANDLVI'}
    for a in SETS:
        for category in ('train','seen_protein_covered_source','seen_protein_uncovered_source','unseen_protein_covered_source','unseen_protein_uncovered_source'):
            groups[a+'_'+category]=lambda x,arm=a,k=category:coverage_stratum(lock['rows'],arm,x['parent_index'],x['position_1based']-1)==k
    methods=sorted({x['method'] for x in records});summaries={};table=[]
    for group,predicate in groups.items():
        summaries[group]={}
        for method in methods:
            rows=[x for x in selections if x['method']==method and x['noise_group']=='all' and predicate(x)]
            if not rows:summaries[group][method]=dict(sites=0,proteins=0);continue
            result=dict(sites=len(rows),proteins=len({x['parent_index'] for x in rows}),top1=sum(x['top1_match'] for x in rows),
                        chosen_both_new_geometry=sum(x['selected_both_new_checked_geometry'] for x in rows),metrics={})
            for key in ('spearman','top1_regret','task_mae','task_rmse','top3_recall','top5_recall','regret_to_new_best','extra_regret_vs_teacher_old_choice'):
                result['metrics'][key]=mean_proteins(rows,key)
            for ng in ('old','new'):
                rr=[x for x in selections if x['method']==method and x['noise_group']==ng and predicate(x)]
                result[ng]=dict(spearman=mean_proteins(rr,'spearman'),regret=mean_proteins(rr,'top1_regret'))
            summaries[group][method]=result
            table.append(dict(group=group,method=method,sites=result['sites'],proteins=result['proteins'],rho=result['metrics']['spearman']['mean'],
                              top1=result['top1'],cross_regret=result['metrics']['regret_to_new_best']['mean'],
                              median_cross_regret=result['metrics']['regret_to_new_best']['median'],max_cross_regret=result['metrics']['regret_to_new_best']['maximum'],
                              delta_mae=result['metrics']['task_mae']['mean'],selected_both_new_geometry=result['chosen_both_new_geometry']))
    write_csv(out/'groups.csv',table)
    contrasts={}
    for arm in SETS:
        contrasts[arm]={}
        for seed in (231301,231303):
            m=f'{arm}_context_s{seed}';contrasts[arm][str(seed)]={}
            for control in (f'{arm}_aa_only_s{seed}','legacy_wt_z'):
                mm=summaries['unseen_protein'][m]['metrics'];bb=summaries['unseen_protein'][control]['metrics']
                paired={}
                for key in ('spearman','regret_to_new_best'):
                    pp=mm[key]['per_protein'];qq=bb[key]['per_protein'];ids=sorted(set(pp)&set(qq));d=np.array([pp[i]-qq[i] for i in ids])
                    rng=np.random.default_rng(314159);boot=d[rng.integers(len(d),size=(10000,len(d)))].mean(1)
                    paired[key]=dict(mean=float(d.mean()),descriptive95=np.quantile(boot,[.025,.975]).tolist(),per_protein=dict(zip(ids,d.tolist())))
                contrasts[arm][str(seed)][control]=paired
    (out/'analysis.json').write_text(json.dumps(dict(complete=True,groups=summaries,contrasts=contrasts),indent=2,allow_nan=False)+'\n')
    curves=[]
    for job in lock['jobs']:
        r=load(root/'runs'/job['id']/'report.json')
        for h in r['history']:
            for x in h['sites']:curves.append(dict(method=job['id'],step=h['step'],parent_index=x['parent_index'],position=x['position'],normalized_mse=x['normalized_mse']))
    write_csv(out/'learning.csv',curves)
    print(json.dumps(summaries['unseen_protein'],indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();summarize_task_readout(a.root,a.out)
