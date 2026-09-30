#!/usr/bin/env python3
"""Calibrate one global-distance coefficient from frozen TRAIN coordinates."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import time
import traceback
import numpy as np
import torch
from fastglycan.adapter_supervision import adapter_loss_parts
from fastglycan.global_distance_supervision import build_global_ca_distance_labels,global_ca_distance_loss


def distance_calibration_sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()


def calibrate_global_distance_case(args):
    root,case=args;root=Path(root);torch.set_num_threads(1);start=time.monotonic()
    manifest=json.loads((root/'manifest.json').read_text());g=case['group_id'];seed=case['seed']
    out=dict(group_id=g,seed=seed,complete=False)
    try:
        for key in ['mapping','gt','labels','teacher','coordinate']:
            p=case[key];assert distance_calibration_sha(p)==manifest['hashes'][p],p
        mapping=dict(np.load(case['mapping']));gt=dict(np.load(case['gt']))
        labels=torch.load(case['labels'],map_location='cpu',weights_only=False)
        assert torch.equal(labels['coordinate'],torch.as_tensor(mapping['coordinates'],dtype=torch.float64))
        assert np.array_equal(labels['coordinate_mask'].numpy(),mapping['mask'])
        ca=(mapping['atom_names']=='CA')&mapping['mask'];ri=mapping['residue_ids'][ca]-1
        assert gt['atom37_mask'][ri,1].all() and gt['residue_mask'][ri].all()
        assert np.array_equal(gt['atom37_positions'][ri,1],mapping['coordinates'][ca])
        newlabels=build_global_ca_distance_labels(mapping)
        raw=np.load(case['coordinate']);assert raw.dtype==np.float32
        x=torch.tensor(raw,requires_grad=True);teacher=torch.as_tensor(np.load(case['teacher']))
        parts=adapter_loss_parts(x,labels,teacher,smooth_temperature=manifest['smooth_temperature'])
        parts['global_distance']=global_ca_distance_loss(x,newlabels)
        gradients={};records={}
        for key,value in parts.items():
            grad,=torch.autograd.grad(value,x,retain_graph=True)
            assert torch.isfinite(value) and torch.isfinite(grad).all()
            weight=1. if key=='global_distance' else manifest['weights'][key]
            weighted=grad.detach().double()*weight;gradients[key]=weighted.numpy()
            records[key]=dict(loss=float(value.detach()),weight=weight,all_norm=float(weighted.norm()),ca_norm=float(weighted[ca].norm()))
        dot={}
        for key in manifest['weights']:
            a=gradients['global_distance'];b=gradients[key];dot[key]={}
            for field,mask in [('all',slice(None)),('ca',ca)]:
                u=a[mask].ravel();v=b[mask].ravel();den=np.linalg.norm(u)*np.linalg.norm(v)
                dot[key][field]=float(u@v/den) if den>1e-20 else None
        file=root/'gradients'/f'{g}_{seed}.npz'
        np.savez_compressed(file,ca_mask=ca,**gradients)
        out.update(complete=True,parts=records,cosines_with_global=dot,pair_count=len(newlabels['pairs']),
                   ca_count=int(ca.sum()),atoms=len(x),gradients_sha256=distance_calibration_sha(file))
    except Exception:out['error']=traceback.format_exc()
    out['seconds']=time.monotonic()-start
    (root/'cases'/f'{g}_{seed}.json').write_text(json.dumps(out,indent=2)+'\n');return out


def run_global_distance_calibration(root,workers):
    root=Path(root);m=json.loads((root/'manifest.json').read_text());start=time.monotonic()
    for p,h in m['hashes'].items():assert distance_calibration_sha(p)==h,p
    assert len(m['groups'])==32 and len(set(m['groups']))==32 and len(m['cases'])==64
    for name in ['cases','gradients']:(root/name).mkdir(exist_ok=False)
    with ProcessPoolExecutor(max_workers=workers) as pool:records=list(pool.map(calibrate_global_distance_case,[(str(root),c) for c in m['cases']]))
    if not all(x['complete'] for x in records):
        (root/'failure.json').write_text(json.dumps(records,indent=2));raise RuntimeError('incomplete64-case calibration')
    ratios=[]
    for group in m['groups']:
        rr=[x for x in records if x['group_id']==group];assert {x['seed'] for x in rr}==set(m['seeds'])
        a=np.mean([x['parts']['coordinate']['ca_norm'] for x in rr]);b=np.mean([x['parts']['global_distance']['ca_norm'] for x in rr])
        assert np.isfinite(a) and np.isfinite(b) and b>1e-12
        ratios.append(dict(group_id=group,old_weighted_ca_norm=float(a),new_unweighted_ca_norm=float(b),ratio=float(a/b)))
    coefficient=float(np.median([r['ratio'] for r in ratios]));assert coefficient>0 and np.isfinite(coefficient)
    for r in records:
        r['weighted_global_all_norm']=coefficient*r['parts']['global_distance']['all_norm']
        r['weighted_global_ca_norm']=coefficient*r['parts']['global_distance']['ca_norm']
    output=dict(complete=True,coefficient=coefficient,rule='median_protein(mean_noise(old0.01_CA_gradient_norm)/mean_noise(new_unweighted_CA_gradient_norm))',
                groups=ratios,records=records,seconds=time.monotonic()-start,manifest_sha256=distance_calibration_sha(root/'manifest.json'),
                model_calls=0,parameter_updates=0,validation_read=False,scope='coordinate-side budget calibration, not parameter-gradient matching or folding benefit')
    (root/'report.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({k:v for k,v in output.items() if k not in ('groups','records')}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--workers',type=int,default=8);a=p.parse_args()
    run_global_distance_calibration(a.root,a.workers)
