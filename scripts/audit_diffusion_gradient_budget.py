#!/usr/bin/env python3
"""Independent NumPy audit of saved component VJPs and descriptive summaries."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256, write_json


def audit_gradient_budget_probe(root):
    start=time.monotonic();lock=json.loads((root/'lock.json').read_text());execution=json.loads((root/'execution.json').read_text())
    assert execution['complete'] and all(w['exit_code']==0 for w in execution['workers'])
    for path,digest in {**lock['hashes'],**lock['input_hashes']}.items():assert sha256(Path(path))==digest
    training=json.loads((Path(lock['train'])/'lock.json').read_text());expected=[]
    for low,high in [(50,127),(128,255),(256,511),(512,1024)]:
        pool=[r for r in training['rows'] if low<=len(r['sequence'])<=high]
        expected.extend(r['group_id'] for r in sorted(pool,key=lambda r:hashlib.sha256(('diffusion-gradient-budget-v1:20260930:'+r['group_id']).encode()).hexdigest())[:4])
    assert expected==[r['group_id'] for r in lock['rows']] and all(r['role']=='train' for r in lock['rows'])
    names=lock['names'];weights=np.array([lock['weights'][n] for n in names]);points=[];count=0;total_bytes=0;max_gram_relative=0.
    parameter_order=None;manifest={}
    for i,assigned in enumerate(lock['assignments']):
        report=json.loads((root/f'worker_{i}/report.json').read_text())
        assert report['complete'] and report['no_optimizer_updates'] and report['base_parameters_unchanged']==1613
        assert report['lock_sha256']==sha256(root/'lock.json')
        assert report['calls']==dict(pairformer=0,diffusion=len(assigned)*6);count+=report['calls']['diffusion']
        assert len(report['points'])==len(assigned)*6
        for row in report['points']:
            g,state,seed=row['group_id'],row['state'],row['seed'];folder=root/'points'/g/f'{state}_{seed}'
            assert row==json.loads((folder/'report.json').read_text()) and row['archive_replay_exact']
            path=folder/'gradients.pt';assert sha256(path)==row['gradient_sha256'];total_bytes+=path.stat().st_size
            manifest[str(path.relative_to(root))]=row['gradient_sha256']
            data=torch.load(path,map_location='cpu',weights_only=False)
            assert data['lock_sha256']==sha256(root/'lock.json') and data['names']==names
            assert (data['group_id'],data['state'],data['seed'])==(g,state,seed)
            if parameter_order is None:parameter_order=(data['parameter_names'],data['sizes'])
            assert parameter_order==(data['parameter_names'],data['sizes'])
            assert sum(data['sizes'])==835584 and len(data['sizes'])==112
            v=data['raw_gradients'].numpy().astype(float);assert v.shape==(6,835584) and np.isfinite(v).all()
            weighted=v*weights[:,None];gram=v@v.T;wgram=weighted@weighted.T;s=row['statistics']
            np.testing.assert_allclose(gram,s['raw_gram'],rtol=1e-10,atol=1e-9)
            np.testing.assert_allclose(wgram,s['weighted_gram'],rtol=1e-10,atol=1e-9)
            max_gram_relative=max(max_gram_relative,float(np.linalg.norm(gram-np.array(s['raw_gram']))/max(np.linalg.norm(gram),1e-30)))
            norms=np.linalg.norm(v,axis=1);wnorms=np.linalg.norm(weighted,axis=1)
            np.testing.assert_allclose(norms,[s['raw_norm'][n] for n in names],rtol=1e-10,atol=1e-10)
            np.testing.assert_allclose(wnorms,[s['weighted_norm'][n] for n in names],rtol=1e-10,atol=1e-10)
            vectors=dict(structure=weighted[:3].sum(0),chemistry=weighted[3:5].sum(0),gt=weighted[:5].sum(0),teacher=weighted[5],gt_s2=weighted.sum(0))
            for key,x in vectors.items():np.testing.assert_allclose(np.linalg.norm(x),s['group_norms'][key],rtol=1e-10,atol=1e-10)
            for key,vector in [('gt','gt'),('gt_s2','gt_s2')]:
                direct=data['direct_'+key].numpy().astype(float)
                error=np.linalg.norm(vectors[vector]-direct)/max(np.linalg.norm(direct),1e-30)
                np.testing.assert_allclose(error,row[key+'_chain_relative'],rtol=1e-6,atol=1e-12)
                assert error<1e-4
            for a,b in [('structure','chemistry'),('teacher','gt'),('gt','gt_s2')]:
                denominator=np.linalg.norm(vectors[a])*np.linalg.norm(vectors[b]);saved=s['group_cosines'][a+'_vs_'+b]
                if denominator:np.testing.assert_allclose(np.dot(vectors[a],vectors[b])/denominator,saved,rtol=1e-9,atol=1e-10)
                else:assert saved is None
            cuts=np.cumsum([0]+data['sizes'])
            for kind in ['down','up']:
                norms=np.sqrt(sum((v[:,cuts[j]:cuts[j+1]]**2).sum(1) for j,n in enumerate(data['parameter_names']) if n.endswith('.'+kind)))
                np.testing.assert_allclose(norms,row['raw_block_norms'][kind],rtol=1e-10,atol=1e-10)
                if state=='initial' and kind=='down':assert np.all(norms==0)
            points.append(row)
            del data,v,weighted,gram,wgram,vectors
    expected_keys={(r['group_id'],state,seed) for r in lock['rows'] for state in lock['states'] for seed in lock['seeds']}
    assert {(r['group_id'],r['state'],r['seed']) for r in points}==expected_keys and len(points)==count==96
    summary={};per_protein=[]
    for state in lock['states']:
        part=[r for r in points if r['state']==state];groups=[]
        for chosen in lock['rows']:
            rows=[r for r in part if r['group_id']==chosen['group_id']];assert len(rows)==2
            row=dict(group_id=chosen['group_id'],pdb_id=chosen['pdb_id'],stratum=chosen['stratum'],state=state)
            scalar={}
            for key in ['teacher_to_gt_norm_ratio','chemistry_to_structure_norm_ratio']:
                scalar[key]=[r['statistics'][key] for r in rows]
            for key in ['structure_vs_chemistry','teacher_vs_gt','gt_vs_gt_s2']:
                scalar[key]=[r['statistics']['group_cosines'][key] for r in rows]
            for name in names:scalar['weighted_norm_'+name]=[r['statistics']['weighted_norm'][name] for r in rows]
            scalar['clash_signed_projection']=[r['statistics']['signed_projection_onto_gt']['clash'] for r in rows]
            for key,values in scalar.items():row[key]=float(np.mean(values)) if all(v is not None for v in values) else None
            groups.append(row);per_protein.append(row)
        stats={}
        for key in [k for k in groups[0] if k not in ['group_id','pdb_id','stratum','state']]:
            values=np.array([r[key] for r in groups if r[key] is not None])
            stats[key]=dict(proteins=len(values),mean=float(values.mean()) if len(values) else None,
                median=float(np.median(values)) if len(values) else None,
                p05=float(np.quantile(values,.05)) if len(values) else None,p95=float(np.quantile(values,.95)) if len(values) else None)
        summary[state]=dict(protein_mean_statistics=stats,
            largest_weighted_component_counts={n:sum(max(r['statistics']['weighted_norm'],key=r['statistics']['weighted_norm'].get)==n for r in part) for n in names},
            structure_chemistry_opposition_points=sum(r['statistics']['group_cosines']['structure_vs_chemistry'] is not None and r['statistics']['group_cosines']['structure_vs_chemistry']<0 for r in part),
            defined_structure_chemistry_points=sum(r['statistics']['group_cosines']['structure_vs_chemistry'] is not None for r in part))
    write_json(root/'gradient_manifest.json',manifest)
    write_json(root/'audit.json',dict(complete=True,points=96,proteins=16,counts=dict(diffusion=count,pairformer=0),
        max_gram_relative=max_gram_relative,gradient_bytes=total_bytes,lock_sha256=sha256(root/'lock.json'),
        manifest_sha256=sha256(root/'gradient_manifest.json'),script_sha256=sha256(Path(__file__)),seconds=time.monotonic()-start))
    write_json(root/'summary.json',dict(complete=True,summary=summary,per_protein=per_protein,points=points,
        audit_sha256=sha256(root/'audit.json'),scope='16 length-balanced TRAIN proteins, not independent prevalence or optimizer efficacy'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args()
    torch.set_num_threads(1);audit_gradient_budget_probe(a.root)
