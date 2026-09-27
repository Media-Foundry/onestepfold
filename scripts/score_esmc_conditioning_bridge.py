#!/usr/bin/env python3
"""Independent CPU scoring of saved paired native/ESMC predictions."""
import argparse
import json
from pathlib import Path

import numpy as np
from fastglycan.experimental_metrics import compare_experimental, prediction_atom37
from fastglycan.experimental_geometry import compare_local_geometry
from fastglycan.scaling_metrics import quality_metrics
from fastglycan.paired_teacher_protocol import sha256, write_json


def dense_lddt(predicted, reference, residue):
    x,y=np.asarray(predicted,dtype=np.float64),np.asarray(reference,dtype=np.float64)
    dx=np.linalg.norm(x[:,None,:]-x[None,:,:],axis=-1)
    dy=np.linalg.norm(y[:,None,:]-y[None,:,:],axis=-1)
    keep=(dy<15)&(residue[:,None]!=residue[None,:])
    count=keep.sum(-1);valid=count>0
    score=sum((np.abs(dx-dy)<t).astype(float) for t in (.5,1.,2.,4.))/4
    return float(((score*keep).sum(-1)[valid]/count[valid]).mean())


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--worker',type=int,required=True)
    a=p.parse_args();r=a.root
    assert 0<=a.worker<4
    out=r/('scores_%d.json'%a.worker)
    assert not out.exists()
    lock=json.loads((r/'bundle_manifest.json').read_text())
    manifest=json.loads((r/'code_v1/source_manifest.json').read_text())
    for name,digest in manifest['files'].items():assert sha256(r/'code_v1'/name)==digest
    worker=r/('worker_%d'%a.worker)/'report.json'
    saved=json.loads(worker.read_text())
    assert saved['complete'] and saved['weights_unchanged'] and not saved['preflight']
    assert saved['bundle_manifest_sha256']==sha256(r/'bundle_manifest.json')
    selected=lock['selection'][a.worker::4]
    expected={(x['group_id'],c,n) for x in selected for c in ['native_reference','esmc_bridge'] for n in [12345,54321]}
    found={(x['group_id'],x['condition'],x['noise']) for x in saved['predictions']}
    assert expected==found and len(found)==len(saved['predictions'])==640
    records={x['group_id']:x for x in selected}
    rows=[];loaded={};dense_checked=[]
    for item in saved['predictions']:
        g=item['group_id'];record=records[g];folder=r/'data'/g
        if g not in loaded:
            for name in ('inventory.npz','gt.npz','prepared.json'):
                assert sha256(folder/name)==lock['data_files'][g][name]
            with np.load(folder/'inventory.npz') as f:inventory=dict(f)
            with np.load(folder/'gt.npz') as f:arrays=dict(f)
            loaded={g:(inventory,arrays)}
        inventory,arrays=loaded[g]
        path=r/item['path'];assert path.resolve().is_relative_to(r.resolve())
        assert sha256(path)==item['sha256']
        x=np.load(path,allow_pickle=False)
        assert x.shape==(len(inventory['atom_name']),3) and np.isfinite(x).all()
        assert item['counts']=={'trunk':1,'structure':1,'confidence':0}
        assert item['sampling']['noise_schedule']==[2560.,0.] and item['sampling']['N_sample']==1
        assert item['sampling']['parameters']['gamma0']==0 and item['sampling']['parameters']['step_scale_eta']==1
        prediction=inventory|{'coordinate':x}
        row=item|{'metrics':compare_experimental(prediction,arrays,record['sequence']),
                  'geometry':compare_local_geometry(prediction,arrays,record['sequence']),
                  'quality':quality_metrics(prediction,arrays,record['sequence'])}
        assert row['metrics']['predicted_gt_coverage']==1
        if g==selected[0]['group_id']:
            positions,present=prediction_atom37(prediction,record['sequence'])
            mask=present&arrays['atom37_mask']&arrays['residue_mask'][:,None]
            residue=np.nonzero(mask)[0]
            dense=dense_lddt(positions[mask],arrays['atom37_positions'][mask],residue)
            assert abs(dense-row['quality']['all_atom_lddt'])<=1e-12
            dense_checked.append((g,item['condition'],item['noise']))
        rows.append(row)
    assert len(dense_checked)==4
    write_json(out,{'complete':True,'worker':a.worker,'rows':rows,'worker_report_sha256':sha256(worker),
                   'bundle_manifest_sha256':sha256(r/'bundle_manifest.json'),
                   'dense_lddt_independent_checks':dense_checked,'scoring_source_sha256':sha256(Path(__file__)),
                   'scope':'CPU metrics from saved coordinates; fixed observed masks and float64 distance evaluation'})
    print('Scored640 saved predictions on160 targets',flush=True)


if __name__=='__main__':main()
