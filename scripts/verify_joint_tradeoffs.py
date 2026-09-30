#!/usr/bin/env python3
"""Dense directed-distance audit of all saved endpoint attribution tables."""
import argparse
import csv
import io
import json
from pathlib import Path
import tarfile

import numpy as np
from scipy.spatial.distance import cdist

from fastglycan.paired_teacher_protocol import sha256, write_json


def verify_joint_tradeoffs(root):
    result=json.loads((root/'report.json').read_text());source=Path(result['source'])
    for p,h in result['hashes'].items():assert sha256(Path(p))==h
    report=json.loads((source/'report.json').read_text())
    with tarfile.open(source/'artifacts.tar.gz') as tar:
        files={m.name:tar.extractfile(m).read() for m in tar if m.isfile()}
    partitions=list(csv.DictReader((root/'partitions.csv').open()));cases=list(csv.DictReader((root/'cases.csv').open()))
    maxerr=0.;checked=0;matrix_count=0
    for index in range(0,32,2):
        left,right=report['rows'][index:index+2]
        if not left['success']:continue
        old=dict(np.load(io.BytesIO(files[f'cases/{index:02d}/coordinates.npz'])))
        new=dict(np.load(io.BytesIO(files[f'cases/{index+1:02d}/coordinates.npz'])))
        coords=dict(raw=old['raw'],local=old['local'],start=new['start'],zero_final=old['final'],warm_final=new['final'])
        for metric in ['aa','ca']:
            use=np.ones(len(old['raw']),bool) if metric=='aa' else old['atom_names']=='CA'
            res=old['residue_ids'][use];names=old['atom_names'][use];truth=cdist(old['target'][use],old['target'][use]);raw=cdist(old['raw'][use],old['raw'][use])
            valid=(truth<15)&(res[:,None]!=res[None,:]);degree=valid.sum(1);keep=degree>0
            factors=np.divide(valid,degree[:,None],out=np.zeros_like(truth),where=degree[:,None]>0)/keep.sum()
            bone=np.isin(names,['N','CA','C','O']);bb=bone[:,None]&bone[None,:];oo=~bone[:,None]&~bone[None,:]
            pair_masks={'BB':bb,'BO':~bb&~oo,'OO':oo};sep=np.abs(res[:,None]-res[None,:]);sep_masks={'1':sep==1,'2-4':(sep>=2)&(sep<=4),'5+':sep>=5}
            for stage,x in coords.items():
                d=cdist(x[use],x[use]);gt_error=np.abs(d-truth);raw_error=np.abs(d-raw)
                thresholds=np.stack([(gt_error<t)*factors/4 for t in [.5,1.,2.,4.]])
                contributions=thresholds.sum(0);matrix_count+=1
                records=[r for r in partitions if r['pdb_id']==left['pdb_id'] and int(r['seed'])==left['seed'] and r['metric']==metric and r['stage']==stage]
                for r in records:
                    partition,group=r['partition'],r['group']
                    if partition=='threshold':
                        k=[.5,1.,2.,4.].index(float(group));checks={'score':thresholds[k].sum(),'support':.25};count=valid.sum()//2
                    else:
                        if partition=='pair_type':mask=pair_masks[group]
                        elif partition=='separation':mask=sep_masks[group]
                        else:
                            kind,space=group.split(':');mask=pair_masks[kind]&sep_masks[space]
                        checks={'score':contributions[mask].sum(),'support':factors[mask].sum(),
                            'gt_distance_mae':(factors*gt_error)[mask].sum(),'raw_distance_mae':(factors*raw_error)[mask].sum()};count=(valid&mask).sum()//2
                    assert int(r['count'])==count
                    maxerr=max(maxerr,*[abs(float(v)-float(r[k])) for k,v in checks.items()]);checked+=1
                c=[r for r in cases if r['pdb_id']==left['pdb_id'] and int(r['seed'])==left['seed'] and r['metric']==metric and r['stage']==stage]
                assert len(c)==1
                for k,v in [('score',contributions.sum()),('gt_distance_mae',(factors*gt_error).sum()),('raw_distance_mae',(factors*raw_error).sum())]:maxerr=max(maxerr,abs(float(v)-float(c[0][k])))
    assert matrix_count==140 and maxerr<1e-12
    summaries=list(csv.DictReader((root/'summary.csv').open()));proteins=list(csv.DictReader((root/'protein_contrasts.csv').open()))
    max_summary=0.
    for r in summaries+proteins:
        new,old=r['contrast'].split('-');pdbs=[r['pdb_id']] if 'pdb_id' in r else sorted({c['pdb_id'] for c in cases})
        for field in ['score','gt_distance_mae','raw_distance_mae']:
            if not r.get(field):continue
            per=[]
            for pdb in pdbs:
                seeds=[]
                for seed in [12345,54321]:
                    values=[]
                    for stage in [new,old]:
                        found=[x for x in partitions if x['pdb_id']==pdb and int(x['seed'])==seed and x['stage']==stage and all(x[k]==r[k] for k in ['metric','partition','group'])]
                        assert len(found)<=1;values.append(float(found[0][field]) if found else 0.)
                    seeds.append(values[0]-values[1])
                per.append(np.mean(seeds))
            max_summary=max(max_summary,abs(float(np.mean(per))-float(r[field])))
    assert max_summary<1e-12
    for r in summaries:
        if r['partition']!='pair_type':continue
        matched=[v for v in summaries if all(v[k]==r[k] for k in ['contrast','metric','partition'])]
        new,old=r['contrast'].split('-')
        for key in ['score','gt_distance_mae','raw_distance_mae']:
            a=np.mean([float(c[key]) for c in cases if c['metric']==r['metric'] and c['stage']==new])
            b=np.mean([float(c[key]) for c in cases if c['metric']==r['metric'] and c['stage']==old])
            assert abs(sum(float(v[key]) for v in matched)-(a-b))<1e-12
    objective=list(csv.DictReader((root/'objectives.csv').open()));objective_error=0.
    fields=['anchor','rotation','torsion','connection_cn','connection_angle_c','connection_angle_n','connection_omega','connection_carbonyl','repulsion','tail','budget']
    for r in objective:
        row=next(x for x in report['rows'] if x['success'] and x['pdb_id']==r['pdb_id'] and x['seed']==int(r['seed']) and x['arm']==('zero' if r['arm']=='zero' else 'sidechain'))
        expected=row['final_cross_objectives']['calibrated'];total=sum(float(r[k]) for k in fields)
        objective_error=max(objective_error,abs(total-expected),abs(total-float(r['total'])))
        assert abs(sum(float(r[k]) for k in fields if k.startswith('connection_'))-100*row['history'][-1]['terms']['connection'])<1e-8
    assert len(objective)==28 and objective_error<1e-8
    hashes={str(root/name):sha256(root/name) for name in ['partitions.csv','cases.csv','objectives.csv','protein_contrasts.csv','summary.csv']}
    write_json(root/'audit.json',dict(complete=True,report_sha256=sha256(root/'report.json'),script_sha256=sha256(Path(__file__)),
        matrices_verified=matrix_count,partition_rows_verified=checked,aggregation_rows_verified=len(summaries)+len(proteins),
        max_partition_error=maxerr,max_summary_error=max_summary,max_objective_sum_error=objective_error,output_hashes=hashes,
        scope='independent dense directed-distance arithmetic; objective sums checked against source audit, not independent chemistry'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    verify_joint_tradeoffs(p.parse_args().root)
