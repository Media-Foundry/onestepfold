"""Decompose frozen labels and all TRAIN prediction snapshots without fitting."""
import argparse,csv,json
from collections import defaultdict
from pathlib import Path
import numpy as np
from fastglycan.objective_audit import score_decomposition,noise_audit,rank_correlation


def audit_score_objective(root,out,gradroot):
    load=lambda p:json.loads(p.read_text())
    lock=load(root/'lock.json');cases=load(root/'evaluation_labels.json')['cases']
    assert load(root/'execution.json')['complete'] and load(root/'independent_audit.json')['complete']
    lookup={(c['parent_index'],c['position']):c for c in cases}
    labelrows=[];errors=[];gradrows=[]
    for c in cases:
        ids=[a for a in range(20) if a!=c['wt']];y=np.array(c['target_delta'])[:,ids];old=y[:2].mean(0)
        row={k:c[k] for k in ['parent_index','position','pdb_id','source_aa','role']}
        row.update(score_decomposition(old,np.zeros(19)));row.update(noise_audit(y));labelrows.append(row)
    train=[r for r in labelrows if r['role']=='train']
    # Previously reported highest raw-energy trio, fixed identities (zero-based positions).
    heavy={(8,74),(8,60),(8,42)}
    assert heavy=={(r['parent_index'],r['position']) for r in sorted(train,key=lambda x:x['label_energy'],reverse=True)[:3]}
    for j in lock['jobs']:
        run=load(root/'runs'/j['id']/'report.json')
        for snap in run['history']:
            for v in snap['sites']:
                c=lookup[v['parent_index'],v['position']];ids=[a for a in range(20) if a!=c['wt']]
                y=np.array(c['target_delta'])[:,ids];p=np.array(v['predicted_delta'])[ids];old=y[:2].mean(0)
                row=dict(job=j['id'],size=j['size'],architecture=j['architecture'],seed=j['seed'],step=snap['step'],terminal=snap['step']==j['steps'],parent_index=c['parent_index'],position=c['position'],source_aa=c['source_aa'])
                row.update(score_decomposition(old,p));row.update(rho_old=rank_correlation(old,p),rho_new=rank_correlation(y[2:].mean(0),p),rho_all=rank_correlation(y.mean(0),p))
                assert abs(row['mse']/j['scale']**2-v['normalized_mse'])<1e-4*max(1,v['normalized_mse'])
                errors.append(row)
    summaries={}
    for j in lock['jobs']:
        for step in sorted({r['step'] for r in errors if r['job']==j['id']}):
            rows=[r for r in errors if r['job']==j['id'] and r['step']==step]
            metrics={}
            for name in ['mse','mean_error','centered_error','label_energy','centered_energy']:
                total=sum(r[name] for r in rows);part=sum(r[name] for r in rows if (r['parent_index'],r['position']) in heavy)
                metrics[name]=dict(mean=total/len(rows),heavy_share=part/total if total else None)
            rho={}
            for name in ['rho_old','rho_new','rho_all']:
                vals=[r[name] for r in rows if r[name] is not None]
                rho[name]=dict(mean=float(np.mean(vals)) if vals else None,median=float(np.median(vals)) if vals else None,
                               undefined=len(rows)-len(vals),nonpositive=sum(v<=0 for v in vals),above_05=sum(v>.5 for v in vals),above_09=sum(v>.9 for v in vals))
            summaries[f'{j["id"]}:{step}']=dict(sites=len(rows),metrics=metrics,ranks=rho)
    for path in sorted(gradroot.glob('n32_*.json')):
        d=load(path);assert d['complete'] and d['parameters_unchanged'] and d['optimizer_updates']==0
        gradrows.extend(d['rows'])
    assert len(gradrows)==1536
    gs={}
    for job,step in sorted({(r['job'],r['step']) for r in gradrows}):
        rows=[r for r in gradrows if r['job']==job and r['step']==step];result={}
        for name in ['gradient_norm','centered_gradient_norm','mean_gradient_norm','clipped_norm','score_gradient_norm']:
            total=sum(r[name] for r in rows);part=sum(r[name] for r in rows if (r['parent_index'],r['position']) in heavy)
            sq=sum(r[name]**2 for r in rows);sp=sum(r[name]**2 for r in rows if (r['parent_index'],r['position']) in heavy)
            result[name]=dict(mean=total/len(rows),median=float(np.median([r[name] for r in rows])),heavy_norm_share=part/total if total else None,heavy_squared_norm_share=sp/sq if sq else None)
        result['clipped_sites']=sum(r['gradient_norm']>1 for r in rows)
        gs[f'{job}:{step}']=result
    energy={}
    for name in ['label_energy','mean_energy','centered_energy']:
        total=sum(r[name] for r in train);part=sum(r[name] for r in train if (r['parent_index'],r['position']) in heavy)
        energy[name]=dict(total=total,heavy_share=part/total)
    out.mkdir(parents=True,exist_ok=True)
    for name,rows in [('labels',labelrows),('training_decomposition',errors),('gradients',gradrows)]:
        with (out/f'{name}.csv').open('w') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    (out/'summary.json').write_text(json.dumps(dict(complete=True,training_sites=128,heavy_sites=sorted(heavy),energy=energy,snapshots=summaries,gradients=gs,
                                                  label_rows=len(labelrows),prediction_rows=len(errors),gradient_rows=len(gradrows),optimizer_updates=0,c4_calls=0,s1_calls=0),indent=2,allow_nan=False)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--gradroot',type=Path,required=True)
    a=p.parse_args();audit_score_objective(a.root,a.out,a.gradroot)
