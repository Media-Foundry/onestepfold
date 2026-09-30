#!/usr/bin/env python3
"""Offline TRAIN-only naming ambiguity audit; no coordinate/model changes."""
import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
import torch
from fastglycan.ambiguous_labels import align_ambiguous_gt
from fastglycan.paired_teacher_protocol import sha256,write_json


def audit_ambiguous_case(args):
    folder,row=args;folder=Path(folder);lock=json.loads((folder/'lock.json').read_text())
    predictions=Path(lock['predictions']);source=Path(lock['source']);g=row['group_id'];torch.set_num_threads(1)
    from fastglycan.scaling_metrics import lddt_observed
    from fastglycan.smooth_lddt_supervision import build_smooth_lddt_labels,smooth_lddt_loss
    mapping_path=source/'chemistry'/g/'mapping.npz';assert sha256(mapping_path)==lock['inputs'][str(mapping_path)]
    m=dict(np.load(mapping_path));mask=m['mask'];res=m['residue_ids'];records=[]
    original=build_smooth_lddt_labels(dict(coordinate=torch.as_tensor(m['coordinates']),coordinate_mask=torch.as_tensor(mask)),dict(atom_name=m['atom_names'],residue_id=res))
    for model in ['retained','weak']:
        for seed in [600001,600011]:
            p=predictions/'examples'/g/f'{model}_seed{seed}.npy';assert sha256(p)==lock['inputs'][str(p)]
            x=np.load(p);result=align_ambiguous_gt(x,m,row['sequence']);target=result['coordinates']
            alt=build_smooth_lddt_labels(dict(coordinate=torch.as_tensor(target),coordinate_mask=torch.as_tensor(mask)),dict(atom_name=m['atom_names'],residue_id=res))
            ca=m['atom_names']=='CA';assert np.array_equal(target[ca],m['coordinates'][ca])
            a=lddt_observed(x[mask],m['coordinates'][mask],res[mask])['score']
            b=lddt_observed(x[mask],target[mask],res[mask])['score']
            xx=torch.as_tensor(x).clone().requires_grad_(True)
            l0=smooth_lddt_loss(xx,original,temperature=.1);g0,=torch.autograd.grad(l0,xx)
            l1=smooth_lddt_loss(xx,alt,temperature=.1);g1,=torch.autograd.grad(l1,xx)
            assert torch.isfinite(g0).all() and torch.isfinite(g1).all()
            norm0=float(g0.double().norm());norm1=float(g1.double().norm())
            cosine=float((g0.double()*g1.double()).sum())/(norm0*norm1) if norm0*norm1>1e-30 else None
            records.append(dict(group_id=g,model=model,seed=seed,aa_original=a,aa_relabelled=b,delta_aa=b-a,
                smooth_original=float(l0.detach()),smooth_relabelled=float(l1.detach()),gradient_norm_original=norm0,
                gradient_norm_relabelled=norm1,gradient_cosine=cosine,
                relative_gradient_change=float((g1-g0).double().norm())/norm0 if norm0>1e-30 else None,
                candidate_groups=len(result['records']),swapped_groups=sum(r['swapped'] for r in result['records']),groups=result['records']))
    write_json(folder/'cases'/f'{g}.json',dict(complete=True,records=records));return records


def audit_ambiguous_labels(folder,predictions):
    assert not (folder/'lock.json').exists();folder.mkdir(parents=True,exist_ok=True)
    parent=json.loads((predictions/'lock.json').read_text());run=json.loads((predictions/'controller_execution.json').read_text())
    assert run['complete'] and len(parent['rows'])==32 and all(r['role']=='train' for r in parent['rows'])
    source=Path(parent['source']);inputs={}
    for row in parent['rows']:
        g=row['group_id'];mp=source/'chemistry'/g/'mapping.npz';inputs[str(mp)]=sha256(mp)
        assert inputs[str(mp)]==parent['input_hashes'][str(mp)]
        report=json.loads((predictions/'examples'/g/'report.json').read_text())
        assert report['lock_sha256']==sha256(predictions/'lock.json')
        for item in report['entries']:
            if item['seed'] in [600001,600011]:
                p=predictions/'examples'/g/item['name'];assert sha256(p)==item['sha256'];inputs[str(p)]=item['sha256']
    write_json(folder/'lock.json',dict(rows=parent['rows'],predictions=str(predictions),source=str(source),inputs=inputs,
        prediction_lock_sha256=sha256(predictions/'lock.json'),script_sha256=sha256(Path(__file__)),
        protocol_sha256=sha256(folder/'code/docs/mini_ambiguous_label_audit_v1.md')))
    with ProcessPoolExecutor(max_workers=8) as pool:
        records=[x for rr in pool.map(audit_ambiguous_case,[(str(folder),r) for r in parent['rows']]) for x in rr]
    assert len(records)==128
    summary={}
    for model in ['retained','weak']:
        rr=[r for r in records if r['model']==model]
        summary[model]={k:float(np.mean([r[k] for r in rr])) for k in ['aa_original','aa_relabelled','delta_aa','smooth_original','smooth_relabelled','gradient_cosine','relative_gradient_change']}
        summary[model].update(swapped_groups=sum(r['swapped_groups'] for r in rr),candidate_groups=sum(r['candidate_groups'] for r in rr))
    write_json(folder/'report.json',dict(complete=True,records=records,summary=summary,prediction_changes=0,model_calls=0,
        lock_sha256=sha256(folder/'lock.json'),scope='naming diagnostic, not new structure quality or revised historical metric'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--predictions',type=Path,required=True)
    a=p.parse_args();audit_ambiguous_labels(a.root,a.predictions)
