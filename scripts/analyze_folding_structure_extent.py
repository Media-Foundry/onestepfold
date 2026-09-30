#!/usr/bin/env python3
"""Read frozen predictions; characterize global errors without new inference."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
import time
import traceback
import numpy as np
from fastglycan.structure_extent import structure_extent_diagnostics


def extent_sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()


def analyze_structure_extent_case(args):
    destination,row=args;destination=Path(destination);start=time.monotonic()
    manifest=json.loads((destination/'manifest.json').read_text());root=Path(manifest['evaluation_root'])
    lock=json.loads((root/'lock.json').read_text());source=Path(lock['source']);g=row['group_id']
    result=dict(group_id=g,pdb_id=row['pdb_id'],complete=False,records=[])
    try:
        mapping_path=source/'chemistry'/g/'mapping.npz';gt_path=source/'data/examples'/g/'gt.npz'
        for p in [mapping_path,gt_path]:assert extent_sha(p)==lock['input_hashes'][str(p)]
        m=dict(np.load(mapping_path));gt=dict(np.load(gt_path));ca=(m['atom_names']=='CA')&m['mask']
        ids=m['residue_ids'][ca];assert len(ids)==len(row['sequence']) and np.array_equal(ids,np.arange(1,len(ids)+1))
        # The existing GT schema atom37 ordering is N,CA,C,CB,O,...; match CA=1.
        assert gt['atom37_mask'][ids-1,1].all() and gt['residue_mask'][ids-1].all()
        y=gt['atom37_positions'][ids-1,1];assert np.array_equal(y,m['coordinates'][ca])
        report_path=root/'examples'/g/'report.json';report=json.loads(report_path.read_text())
        assert extent_sha(report_path)==manifest['example_reports'][g]
        assert report['lock_sha256']==manifest['evaluation_lock_sha256']
        seeds=lock['train_seeds'] if row['role']=='train' else lock['validation_seeds']
        assert {(e['model'],e['seed']) for e in report['entries']}=={(m,s) for m in lock['models'] for s in seeds}
        for e in report['entries']:
            p=report_path.parent/e['name'];assert extent_sha(p)==e['sha256']
            x=np.load(p);assert x.dtype==np.float32 and x.shape==m['coordinates'].shape
            d=structure_extent_diagnostics(x[ca],y,ids)
            old=manifest['rmsd'][g][e['model']][str(e['seed'])]
            error=abs(d['ca_rmsd']-old);assert error<1e-8,(g,e['model'],error)
            result['records'].append(dict(model=e['model'],seed=e['seed'],prediction_sha256=e['sha256'],rmsd_replay_error=error,**d))
        result['complete']=True
    except Exception:result['error']=traceback.format_exc()
    result['seconds']=time.monotonic()-start
    (destination/'cases'/f'{g}.json').write_text(json.dumps(result,sort_keys=True)+'\n')
    return result


def summarize_structure_extent(destination,workers):
    destination=Path(destination);manifest=json.loads((destination/'manifest.json').read_text())
    for path,digest in manifest['hashes'].items():assert extent_sha(path)==digest,path
    root=Path(manifest['evaluation_root']);lock=json.loads((root/'lock.json').read_text())
    (destination/'cases').mkdir(exist_ok=False);start=time.monotonic()
    with ProcessPoolExecutor(max_workers=workers) as pool:results=list(pool.map(analyze_structure_extent_case,[(str(destination),r) for r in lock['rows']]))
    failures=[r for r in results if not r['complete']]
    if failures:
        (destination/'failure.json').write_text(json.dumps(failures,indent=2));raise RuntimeError('incomplete analysis; preserve denominator')
    lookup={r['group_id']:{(x['model'],x['seed']):x for x in r['records']} for r in results}
    scalar=['ca_rmsd','residual_median','residual_p90','fraction_gt2','fraction_gt5','top5_sse_fraction','remainder95_rmsd_fixed_alignment','fragment32_rmsd','rg_ratio']
    metrics=scalar+[f'{b}.{v}' for b in ['all','seq24_gt_lt15','seq24_gt_15_30','seq24_gt_ge30'] for v in ['mae','rmse','signed_mean']]
    def value(record,key):
        if '.' not in key:return record[key]
        band,field=key.split('.');return record['distance_bands'][band][field]
    summary={};paired=[]
    for cohort,groups in lock['cohorts'].items():
        means={}
        for group in groups:
            for model in lock['models']:
                rr=[r for (m,_),r in lookup[group].items() if m==model];assert len(rr)==2
                means[group,model]={}
                for key in metrics:
                    vv=[value(r,key) for r in rr];means[group,model][key]=None if any(v is None for v in vv) else float(np.mean(vv))
        summary[cohort]={'proteins':len(groups),'models':{},'contrasts':[]}
        for model in lock['models']:
            sm={}
            for key in metrics:
                xx=[means[g,model][key] for g in groups if means[g,model][key] is not None]
                sm[key]=dict(proteins=len(xx),mean=float(np.mean(xx)) if xx else None,median=float(np.median(xx)) if xx else None)
            summary[cohort]['models'][model]=sm
        for candidate,reference in lock['contrasts']:
            sm={}
            for key in metrics:
                xx=[means[g,candidate][key]-means[g,reference][key] for g in groups if means[g,candidate][key] is not None and means[g,reference][key] is not None]
                if xx:
                    x=np.array(xx);boot=np.random.default_rng(lock['bootstrap']['seed']).integers(0,len(x),size=(lock['bootstrap']['replicates'],len(x)))
                    sm[key]=dict(proteins=len(x),mean=float(x.mean()),median=float(np.median(x)),increased=int((x>0).sum()),ci95=np.quantile(x[boot].mean(1),[.025,.975]).tolist())
                else:sm[key]=dict(proteins=0,mean=None,ci95=None)
            summary[cohort]['contrasts'].append(dict(candidate=candidate,reference=reference,metrics=sm))
        for group in groups:
            concentration=[]
            for seed in sorted({s for _,s in lookup[group]}):
                a=lookup[group]['coordinate_zero',seed];b=lookup[group]['expanded',seed]
                positive=np.maximum(0,np.square(a['aligned_residual'])-np.square(b['aligned_residual']));total=positive.sum()
                concentration.append(float(np.sort(positive)[-a['top5_count']:].sum()/total) if total>1e-20 else None)
            paired.append(dict(cohort=cohort,group_id=group,pdb_id=next(r['pdb_id'] for r in results if r['group_id']==group),
                candidate=means[group,'coordinate_zero'],reference=means[group,'expanded'],positive_sse_increase_top5_fraction=concentration))
    output=dict(complete=True,proteins=len(results),outputs=sum(len(r['records']) for r in results),summary=summary,paired=paired,
                rmsd_replay_max=max(x['rmsd_replay_error'] for r in results for x in r['records']),seconds=time.monotonic()-start,
                manifest_sha256=extent_sha(destination/'manifest.json'),scope='posthoc existing-coordinate diagnostic; no new model calls or gate')
    (destination/'report.json').write_text(json.dumps(output,indent=2)+'\n')
    with gzip.open(destination/'cases.json.gz','wt') as f:json.dump(results,f,sort_keys=True)
    print(json.dumps({k:v for k,v in output.items() if k not in ('summary','paired')}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--workers',type=int,default=8);a=p.parse_args()
    summarize_structure_extent(a.root,a.workers)
