#!/usr/bin/env python3
"""Independently score an exported GT-adaptation checkpoint on HPC3 CPU."""
import argparse
import json
from pathlib import Path
import numpy as np
from fastglycan.experimental_metrics import compare_experimental,prediction_atom37
from fastglycan.experimental_geometry import compare_local_geometry
from fastglycan.scaling_metrics import quality_metrics
from fastglycan.paired_teacher_protocol import sha256,write_json
from score_esmc_conditioning_bridge import dense_lddt


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--size',type=int,choices=(2048,8192),required=True);p.add_argument('--step',type=int,required=True)
    a=p.parse_args();r=a.root;lock=json.loads((r/'lock.json').read_text())
    assert a.step in lock['evaluation_steps']
    source=json.loads((r/'code_v1/source_manifest.json').read_text())
    for name,digest in source['files'].items():assert sha256(r/'code_v1'/name)==digest,name
    manifest=json.loads((r/'data_manifest.json').read_text());assert sha256(r/'data_manifest.json')==lock['common_files']['data_manifest.json']
    rows=manifest['selection'];byid={x['group_id']:x for x in rows}
    wanted={x['group_id'] for x in rows if x['split']=='validation'}|set(lock['train_probe_groups'])
    worker=r/('train_%d'%a.size)/('evaluation_%04d.json'%a.step);saved=json.loads(worker.read_text())
    assert saved['complete'] and saved['weights_unchanged'] and saved['step']==a.step and saved['size']==a.size
    assert saved['lock_sha256']==sha256(r/'lock.json')
    assert len(saved['predictions'])==320 and {(x['group_id'],x['noise']) for x in saved['predictions']}=={(g,n) for g in wanted for n in [12345,54321]}
    output=r/'scores'/('%d_%04d.json'%(a.size,a.step));output.parent.mkdir(exist_ok=True)
    assert not output.exists();scored=[];loaded={};dense_checked=[]
    first={s:min(g for g in wanted if byid[g]['split']==s) for s in ['train','validation']}
    for item in saved['predictions']:
        g=item['group_id'];record=byid[g];folder=r/'data'/g
        assert item['split']==record['split']
        if g not in loaded:
            for name in ('inventory.npz','gt.npz','prepared.json'):
                assert sha256(folder/name)==manifest['data_files'][g][name]
            with np.load(folder/'inventory.npz') as f:inventory=dict(f)
            with np.load(folder/'gt.npz') as f:arrays=dict(f)
            loaded={g:(inventory,arrays)}
        inventory,arrays=loaded[g]
        path=r/item['path'];assert path.resolve().is_relative_to(r.resolve())
        assert sha256(path)==item['sha256'];x=np.load(path,allow_pickle=False)
        assert x.shape==(len(inventory['atom_name']),3) and np.isfinite(x).all()
        assert item['counts']=={'trunk':1,'structure':1,'confidence':0} and item['sampling']==lock['sampling']
        prediction=inventory|{'coordinate':x}
        row=item|{'metrics':compare_experimental(prediction,arrays,record['sequence']),
                  'quality':quality_metrics(prediction,arrays,record['sequence']),
                  'geometry':compare_local_geometry(prediction,arrays,record['sequence'])}
        assert row['metrics']['predicted_gt_coverage']==1
        if g in first.values():
            positions,present=prediction_atom37(prediction,record['sequence'])
            mask=present&arrays['atom37_mask']&arrays['residue_mask'][:,None]
            dense=dense_lddt(positions[mask],arrays['atom37_positions'][mask],np.nonzero(mask)[0])
            assert abs(dense-row['quality']['all_atom_lddt'])<=1e-12
            dense_checked.append((g,item['noise']))
        scored.append(row)
    assert len(dense_checked)==4
    write_json(output,{'complete':True,'size':a.size,'step':a.step,'rows':scored,
        'worker_sha256':sha256(worker),'lock_sha256':sha256(r/'lock.json'),
        'data_manifest_sha256':sha256(r/'data_manifest.json'),'scoring_source_sha256':sha256(Path(__file__)),
        'source_manifest_sha256':sha256(r/'code_v1/source_manifest.json'),
        'dense_lddt_checks':dense_checked,'scope':'Independent saved-coordinate CPU scoring, both fixed K1 noise views'})
    print(json.dumps({'complete':True,'size':a.size,'step':a.step,'predictions':len(scored)}),flush=True)


if __name__=='__main__':main()
