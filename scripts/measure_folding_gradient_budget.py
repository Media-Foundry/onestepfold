#!/usr/bin/env python3
"""Replay fixed TRAIN coordinates, measure loss-side gradients without model calls."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import time
import traceback
import numpy as np
import torch
from fastglycan.adapter_supervision import adapter_loss_parts
from fastglycan.global_distance_supervision import build_global_ca_distance_labels,global_ca_distance_loss
from fastglycan.gradient_budget import coordinate_gradient_budget
from fastglycan.paired_teacher_protocol import sha256


def measure_folding_gradient_case(args):
    root,case=args;root=Path(root);torch.set_num_threads(1);start=time.monotonic()
    m=json.loads((root/'manifest.json').read_text());out={k:case[k] for k in ['stage','group_id','seed']};out['complete']=False
    try:
        for key in ['mapping','gt','labels','teacher','coordinate']:
            path=case[key];assert sha256(Path(path))==m['hashes'][path],path
        assert case['group_id'] in m['train_groups']
        mapping=dict(np.load(case['mapping']));gt=dict(np.load(case['gt']));labels=torch.load(case['labels'],map_location='cpu',weights_only=False)
        assert np.array_equal(labels['coordinate'].numpy(),mapping['coordinates']) and np.array_equal(labels['coordinate_mask'].numpy(),mapping['mask'])
        ca=(mapping['atom_names']=='CA')&mapping['mask'];ri=mapping['residue_ids'][ca]-1
        assert gt['atom37_mask'][ri,1].all() and gt['residue_mask'][ri].all()
        assert np.array_equal(gt['atom37_positions'][ri,1],mapping['coordinates'][ca])
        x=torch.tensor(np.load(case['coordinate']),requires_grad=True);assert x.dtype==torch.float32
        teacher=torch.as_tensor(np.load(case['teacher']));parts=adapter_loss_parts(x,labels,teacher,smooth_temperature=m['smooth_temperature'])
        newlabels=build_global_ca_distance_labels(mapping);parts['global_distance']=global_ca_distance_loss(x,newlabels)
        gradients={}
        for key,loss in parts.items():
            grad,=torch.autograd.grad(loss,x,retain_graph=True);assert torch.isfinite(loss) and torch.isfinite(grad).all()
            gradients[key]=grad.detach().double().numpy()
        recipes={name:coordinate_gradient_budget(gradients,w,ca) for name,w in m['recipes'].items()}
        fname=f"{case['stage']}_{case['group_id']}_{case['seed']}"
        path=root/'gradients'/f'{fname}.npz';np.savez_compressed(path,ca_mask=ca,**gradients)
        out.update(complete=True,losses={k:float(v.detach()) for k,v in parts.items()},recipes=recipes,gradient_sha256=sha256(path),
                   atoms=len(x),observed_ca=int(ca.sum()),pairs=len(newlabels['pairs']),coordinate_sha256=m['hashes'][case['coordinate']])
    except Exception:out['error']=traceback.format_exc()
    out['seconds']=time.monotonic()-start
    (root/'cases'/f"{case['stage']}_{case['group_id']}_{case['seed']}.json").write_text(json.dumps(out,indent=2)+'\n')
    return out


def run_folding_gradient_budget(root,workers):
    start=time.monotonic();m=json.loads((root/'manifest.json').read_text())
    assert len(m['train_groups'])==32 and len(set(m['train_groups']))==32 and len(m['cases'])==384
    expected={(stage,g,s) for stage in m['stages'] for g in m['train_groups'] for s in m['seeds']}
    assert len(expected)==384 and {(c['stage'],c['group_id'],c['seed']) for c in m['cases']}==expected
    for p,h in m['hashes'].items():assert sha256(Path(p))==h,p
    for name in ['cases','gradients']:(root/name).mkdir(exist_ok=False)
    with ProcessPoolExecutor(max_workers=workers) as pool:records=list(pool.map(measure_folding_gradient_case,[(str(root),c) for c in m['cases']]))
    complete=all(x['complete'] for x in records)
    report=dict(complete=complete,records=records,manifest_sha256=sha256(root/'manifest.json'),seconds=time.monotonic()-start,
                model_calls=0,parameter_updates=0,validation_read=False,scope='Loss-coordinate gradients on saved TRAIN32; not parameter or Adam update attribution; no coefficient chosen')
    (root/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='records'}))
    if not complete:raise RuntimeError('incomplete bounded gradient budget diagnostic')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--workers',type=int,default=8);a=p.parse_args()
    run_folding_gradient_budget(a.root.resolve(),a.workers)
