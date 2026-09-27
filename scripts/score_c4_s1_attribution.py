#!/usr/bin/env python3
"""CPU scoring and target-cluster statistics for locked c4_s1 inference panels."""
import argparse,concurrent.futures,csv,json,math,tarfile
from pathlib import Path
import numpy as np
from evaluate_stage0 import evaluate_row
from fastglycan.paired_teacher_protocol import sha256,write_json
METRICS=('tm_score_ca','all_atom_lddt')

def score_folder(spec):
    rootstr,name,manifest=spec;root=Path(rootstr);folder=root/name
    done=json.loads((folder/'complete.json').read_text());assert done['complete'] and done['progress_sha256']==sha256(folder/'progress.json')
    p=json.loads((folder/'progress.json').read_text());archives={};rows=[]
    try:
        for r in p['records']:
            path=folder/r['artifact']['cif'];assert sha256(path)==r['artifact']['sha256']
            target=dict(manifest[r['group_id']]);target['shard']=target['shard'].replace('/hpc2hdd/home/shuang886/Folding/','/data/user/shuang886/Folding/',1)
            predroot=folder if r['condition']=='fp32_controlled' else folder/r['condition']
            score=evaluate_row(target,predroot,r['setting'],archives,seed=r['seed']);assert score['status']=='ok',score
            assert all(np.isfinite(score[m]) for m in METRICS)
            score.update(setting=r['setting'],seed=r['seed'],condition=r['condition'],feature_sha256=r['feature_sha256'],prediction_sha256=r['artifact']['sha256'],model_forward_seconds=r['model_forward_seconds'],peak_allocated_bytes=r['peak_allocated_bytes'],source=name)
            rows.append(score)
    finally:
        for f in archives.values():f.close()
    write_json(folder/'scores.json',dict(complete=True,progress_sha256=sha256(folder/'progress.json'),records=rows))
    return rows

def summarize(delta):
    n,seeds=delta.shape;mean_target=delta.mean(1);rng=np.random.default_rng(20260927);ix=rng.integers(0,n,size=(10000,n))
    out=dict(n_targets=n,n_seeds=seeds,mean=float(delta.mean()),mean_ci95=np.quantile(mean_target[ix].mean(1),[.025,.975]).tolist(),by_seed=[],persistence={})
    for s in range(seeds):
        d=delta[:,s];out['by_seed'].append(dict(mean=float(d.mean()),p01=float(np.quantile(d,.01)),p05=float(np.quantile(d,.05)),worst5_mean=float(np.sort(d)[:math.ceil(.05*n)].mean()),minimum=float(d.min())))
    for threshold in (-.05,-.1):
        failures=(delta<threshold);k=failures.sum(1);rate=failures.mean(1)
        out['persistence'][str(threshold)]=dict(k_counts={str(i):int((k==i).sum()) for i in range(seeds+1)},fraction=float(rate.mean()),fraction_ci95=np.quantile(rate[ix].mean(1),[.025,.975]).tolist(),persistent_3or4=int((k>=3).sum()))
    # Same sampled seed columns for all target rows preserve the crossed design.
    seed_ix=rng.integers(0,seeds,size=(10000,seeds));sampled=delta[ix]
    crossed=np.take_along_axis(sampled,seed_ix[:,None,:],axis=2).mean((1,2))
    out['crossed_mean_ci95_sensitivity']=np.quantile(crossed,[.025,.975]).tolist()
    return out

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--precision',action='store_true');p.add_argument('--precision-prefix',default='precision_');a=p.parse_args();root=a.root.resolve()
    lock=json.loads((root/'lock.json').read_text());manifest=json.loads((root/'manifest.json').read_text());old=Path(lock['old_root'])
    names=[f'a_{i}' for i in range(16)]+[f'b_{i}' for i in range(8)]
    if a.precision:names += [f'{a.precision_prefix}{i}' for i in range(8)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=8) as ex:chunks=list(ex.map(score_folder,[(str(root),n,manifest) for n in names]))
    records=[r for chunk in chunks for r in chunk]
    for i in range(16):
        name=f'repeat/worker_{i}/scores.json';assert sha256(old/name)==lock['bound_old_files'][name]
        for r in json.loads((old/name).read_text())['records']:
            if r['setting'] in ('c4_s2','c4_s5'):records.append(r|dict(condition='native',source='historical_reference'))
    index={}
    for r in records:
        key=(r['condition'],r['group_id'],r['seed'],r['setting']);assert key not in index,key;index[key]=r
    result=dict(complete=True,lock_sha256=sha256(root/'lock.json'),precision=a.precision,panels={},note='A preselected historical development panel; B discovery-selected diagnostic panel. No best-of-seed. Paired deltas retain K1; fixed four seeds, shared MC effects. TM-style/old AA lDDT definitions.')
    csvrows=[]
    for panel,ids in [('a',lock['panel_a']),('b',lock['panel_b'])]:
        modes=['native'] if panel=='a' else ['native','controlled']+(['fp32_controlled'] if a.precision else [])
        panelout={}
        for mode in modes:
            panelout[mode]={}
            for ref in ('c4_s2','c4_s5'):
                perref={};masks=[]
                for m in METRICS:
                    delta=[]
                    for g in ids:
                        diffs=[]
                        for seed in lock['seeds']:
                            left=index[(mode,g,seed,'c4_s1')];right=index[(mode,g,seed,ref)]
                            assert left['common_atom_count']==right['common_atom_count'] and left['all_atom_lddt_pair_count']==right['all_atom_lddt_pair_count']
                            assert left['feature_sha256']==right['feature_sha256']
                            diffs.append(left[m]-right[m])
                            csvrows.append(dict(panel=panel,condition=mode,reference=ref,metric=m,group_id=g,pdb_id=manifest[g]['pdb_id'],seed=seed,candidate=left[m],reference_score=right[m],delta=diffs[-1]))
                        delta.append(diffs)
                    delta=np.array(delta);perref[m]=summarize(delta);masks.append(delta<-.05)
                    perref[m]['targets']=[dict(group_id=g,pdb_id=manifest[g]['pdb_id'],delta=delta[i].tolist(),mean=float(delta[i].mean()),k=int((delta[i]<-.05).sum())) for i,g in enumerate(ids)]
                union=np.logical_or(*masks);perref['either_metric_k_counts']={str(k):int((union.sum(1)==k).sum()) for k in range(5)}
                panelout[mode][ref]=perref
        result['panels'][panel]=panelout
    if a.precision:
        result['fp32_minus_bf16_controlled']={}
        for s in ('c4_s1','c4_s2','c4_s5'):
            result['fp32_minus_bf16_controlled'][s]={}
            for m in METRICS:
                d=np.array([[index[('fp32_controlled',g,seed,s)][m]-index[('controlled',g,seed,s)][m] for seed in lock['seeds']] for g in lock['panel_b']])
                result['fp32_minus_bf16_controlled'][s][m]=summarize(d)
    dest=root/('final_precision' if a.precision else 'final');dest.mkdir(exist_ok=False)
    write_json(dest/'report.json',result)
    with (dest/'per_target.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(csvrows[0]));w.writeheader();w.writerows(csvrows)
    write_json(dest/'acceptance.json',dict(complete=True,prediction_records=len(records),report_sha256=sha256(dest/'report.json'),csv_sha256=sha256(dest/'per_target.csv'),source_scores={n:sha256(root/n/'scores.json') for n in names}))
    print('Scoring and paired persistence complete',dest,flush=True)
if __name__=='__main__':main()
