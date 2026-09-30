#!/usr/bin/env python3
"""Offline coordinate/checkpoint audit, independent of model execution."""
import argparse
import json
from pathlib import Path

import numpy as np
import torch
from audit_local_projection_gt import score
from fastglycan.hybrid_geometry import GeometryTopology
from fastglycan.paired_teacher_protocol import sha256, write_json
from onestepfold.data.gt_materializer import ATOM37_INDEX


def audit_adapter_preflight(root):
    torch.set_num_threads(1)
    lock=json.loads((root/'lock.json').read_text());report=json.loads((root/'report.json').read_text())
    assert report['complete'] and report['lock_sha256']==sha256(root/'lock.json')
    assert report['counts']==dict(pairformer=4,diffusion=10)
    for path,digest in {**lock['hashes'],**lock['weights_sha256']}.items():assert sha256(Path(path))==digest
    source=root.parent/'fresh_contact_source_v1_20260930';group=lock['row']['group_id']
    packet=source/'chemistry'/group;mapping=dict(np.load(packet/'mapping.npz'))
    arrays=dict(np.load(source/'data/examples'/group/'gt.npz'));ri=mapping['residue_ids']-1
    ai=np.array([ATOM37_INDEX[name] for name in mapping['atom_names']])
    assert arrays['residue_mask'][ri].all() and arrays['atom37_mask'][ri,ai].all()
    assert np.array_equal(arrays['atom37_positions'][ri,ai],mapping['coordinates'])
    saved=torch.load(root/'targets.pt',map_location='cpu',weights_only=False)
    assert np.array_equal(saved['gt'].numpy(),mapping['coordinates'])
    baseline=np.load(root/'native_s1.npy');updated=np.load(root/'updated_s1.npy');teacher=np.load(root/'reference_s2.npy')
    assert np.array_equal(saved['baseline'].numpy(),baseline) and np.array_equal(saved['teacher'].numpy(),teacher)
    for name in ['zero_adapter','restored_s1']:assert np.array_equal(baseline,np.load(root/f'{name}.npy'))
    for name in ['reloaded_s1','merged_s1']:assert np.array_equal(updated,np.load(root/f'{name}.npy'))
    checkpoint=torch.load(root/'adapter.pt',map_location='cpu',weights_only=False)
    assert sha256(root/'adapter.pt')==report['checkpoint_sha256'] and checkpoint['lock_sha256']==sha256(root/'lock.json')
    assert len(checkpoint['names'])==len(set(checkpoint['names']))==56
    assert set(checkpoint['initial'])==set(checkpoint['trained'])==set(checkpoint['names'])
    changes=[];parameter_count=0
    for name in checkpoint['names']:
        initial=checkpoint['initial'][name];trained=checkpoint['trained'][name]
        assert set(initial)==set(trained)=={'up','down'} and initial['up'].count_nonzero()==0
        assert torch.equal(initial['down'],trained['down']) # B=0 at sole initial backward.
        assert trained['up'].count_nonzero()>0 and all(torch.isfinite(v).all() for v in trained.values())
        changes.append(dict(module=name,delta_weight_norm=float((trained['up'].double()@trained['down'].double()).norm())))
        parameter_count+=sum(v.numel() for v in trained.values())
    assert parameter_count==report['trainable_parameters']==835584
    native=torch.load(packet/'native.pt',map_location='cpu',weights_only=False);topology=GeometryTopology(native['atoms'],mapping['reference'])
    pairs=topology.pairs.numpy();bonds=topology.bonds.numpy();c,n,a,b=topology.centres.numpy().T
    error=0.;loss_error=0.;records={}
    for name in report['scores']:
        x=np.load(root/f'{name}.npy').astype(float);gt=mapping['coordinates'].astype(float)
        assert np.isfinite(x).all()
        aa,m=score(x,gt,mapping['residue_ids']);aa=float(aa[m].mean())
        d=np.linalg.norm(x[pairs[:,0]]-x[pairs[:,1]],axis=1)
        bond=np.linalg.norm(x[bonds[:,0]]-x[bonds[:,1]],axis=1)-topology.ideal.numpy()
        vol=(np.cross(x[n]-x[c],x[a]-x[c])*(x[b]-x[c])).sum(1)
        geometry=dict(bond_rmse=float(np.sqrt(np.mean(bond**2))),peptide_mae=float(np.abs(bond[topology.peptide.numpy()]).mean()),
            severe_pairs=int((d<1).sum()),severe_pairs_per_atom=float((d<1).sum()/len(x)),
            max_penetration=float(np.maximum(0,topology.radii.numpy()[pairs].sum(1)-d).max()),
            chirality_fraction=float((vol*topology.volumes.numpy()>0).mean()))
        error=max(error,abs(aa-report['scores'][name]['aa_lddt']),max(abs(v-report['scores'][name]['geometry'][k]) for k,v in geometry.items()))
        records[name]=dict(aa_lddt=aa,geometry=geometry)
        if name in ['native_s1','updated_s1']:
            key='losses_before' if name=='native_s1' else 'losses_after'
            for kind,target in [('gt',gt),('teacher',teacher.astype(float))]:
                xc=x-x.mean(0);yc=target-target.mean(0);u,_,vt=np.linalg.svd(yc.T@xc)
                rotation=u@np.diag([1,1,np.linalg.det(u@vt)])@vt
                loss=float(np.sum((yc@rotation-xc)**2,axis=1).mean())
                loss_error=max(loss_error,abs(loss-report[key][kind]))
    assert error<1e-8 and loss_error<1e-8
    np.savez_compressed(root/'identity_mapping.npz',**mapping)
    write_json(root/'audit.json',dict(complete=True,coordinate_variants=7,parameter_count=parameter_count,
        metric_max_abs=error,loss_max_abs=loss_error,weight_deltas=changes,records=records,
        script_sha256=sha256(Path(__file__)),scope='offline checkpoint/coordinates/GT audit; original parameter immutability checked in runtime before merge'))
    print(json.dumps(dict(audited=True,metric_max_abs=error,loss_max_abs=loss_error)),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);audit_adapter_preflight(p.parse_args().root)
