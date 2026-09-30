#!/usr/bin/env python3
"""GT evaluation and independent metric checks after raw inference is complete."""
import argparse
import csv
import json
from pathlib import Path

import numpy as np
import torch
from audit_local_projection_gt import score
from fastglycan.connection_audit import measure_connections
from fastglycan.connection_diagnostics import describe_connection_distribution
from fastglycan.hybrid_geometry import GeometryTopology
from fastglycan.hybrid_proposals import identity_noise
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.repair_outcomes import absolute_failures
from fastglycan.scaling_metrics import lddt_observed
from onestepfold.data.gt_materializer import ATOM37_INDEX


def audit_step_reference(root):
    torch.set_num_threads(1)
    lock=json.loads((root/'lock.json').read_text());source=Path(lock['source']);records=[];max_error=0.
    previous=json.loads((Path(lock['previous'])/'runtime_lock.json').read_text())
    calibration=json.loads((root/'code/docs/connection_reference_bands.json').read_text())
    for path,digest in {**lock['hashes'],**lock['input_hashes'],**lock['weights_sha256'],**previous['input_hashes']}.items():
        assert sha256(Path(path))==digest
    for item in lock['rows']:
        folder=root/'cases'/item['pdb_id'];report=json.loads((folder/'report.json').read_text())
        assert report['complete'] and report['counts']==dict(pairformer=4,diffusion=16)
        assert report['lock_sha256']==sha256(root/'lock.json') and not report['gt_in_model']
        assert len(report['results'])==6 and report['identity_sha256']==sha256(folder/'identity.npz')
        assert {(e['seed'],e['steps']) for e in report['results']}=={(n,s) for n in lock['seeds'] for s in lock['steps']}
        packet=source/'chemistry'/item['group_id'];mapping=dict(np.load(packet/'mapping.npz'))
        atoms=torch.load(packet/'native.pt',map_location='cpu',weights_only=False)['atoms']
        identity=dict(np.load(folder/'identity.npz'))
        for name in ['atom_names','residue_ids','chain_ids']:assert np.array_equal(identity[name],mapping[name])
        names,residues=mapping['atom_names'],mapping['residue_ids'];target=mapping['coordinates'].astype(np.float64)
        gt=dict(np.load(source/'data'/item['group_id']/'gt.npz'));ai=np.array([ATOM37_INDEX[n] for n in names]);ri=residues-1
        assert mapping['mask'].all() and gt['atom37_mask'][ri,ai].all() and gt['residue_mask'][ri].all()
        assert np.array_equal(target,gt['atom37_positions'][ri,ai])
        topology=GeometryTopology(atoms,mapping['reference']);pairs=topology.pairs.numpy();bonds=topology.bonds.numpy()
        anchors=np.array([[int(np.flatnonzero((residues==i)&(names==n))[0]) for n in ['N','CA','C','O']]
            for i in range(1,len(item['sequence'])+1)])
        gt_branch=measure_connections(target,anchors,item['sequence'])['nearest_omega_sign']
        ca=names=='CA';bone=np.isin(names,['N','CA','C','O','OXT'])
        centres=topology.centres.numpy();c,n,a,b=centres.T
        side=np.array([[int(np.flatnonzero((residues==i)&(names==name))[0]) for name in
            ['CB','CA','CG1' if aa=='I' else 'OG1','CG2']] for i,aa in enumerate(item['sequence'],1) if aa in 'IT'],dtype=int).reshape(-1,4)
        for entry in report['results']:
            seed,steps=entry['seed'],entry['steps'];file=Path(entry['file'])
            assert sha256(file)==entry['sha256'] and entry['nfe']==steps and entry['rng_unchanged'] and entry['conditioning_unchanged']
            noise_file=folder/f'noise_{seed}.npy';assert sha256(noise_file)==entry['noise_sha256']
            assert np.array_equal(np.load(noise_file),identity_noise(atoms,seed).numpy())
            x0=np.load(source/'data'/item['group_id']/f'native_{seed}.npy')
            x=np.load(file);assert x.dtype==np.float32 and x.shape==target.shape and np.isfinite(x).all()
            if steps==1:assert entry['archived_s1_exact'] and np.array_equal(x,x0)
            x=x.astype(np.float64)
            aa_score=lddt_observed(x,target,residues)['score'];ca_score=lddt_observed(x[ca],target[ca],residues[ca])['score']
            independent,mask=score(x,target,residues);ind_ca,mask_ca=score(x[ca],target[ca],residues[ca])
            max_error=max(max_error,abs(aa_score-float(independent[mask].mean())),abs(ca_score-float(ind_ca[mask_ca].mean())))
            _,geometry=topology.terms(torch.tensor(x))
            distance=np.linalg.norm(x[pairs[:,0]]-x[pairs[:,1]],axis=1)
            depth=np.maximum(0,topology.radii.numpy()[pairs].sum(1)-distance)
            errors=np.linalg.norm(x[bonds[:,0]]-x[bonds[:,1]],axis=1)-topology.ideal.numpy()
            volumes=(np.cross(x[n]-x[c],x[a]-x[c])*(x[b]-x[c])).sum(1)
            independent_geometry=dict(bond_rmse=float(np.sqrt(np.mean(errors**2))),peptide_mae=float(np.abs(errors[topology.peptide.numpy()]).mean()),
                chirality_fraction=float((volumes*topology.volumes.numpy()>0).mean()),severe_pairs=int((distance<1).sum()),
                severe_pairs_per_atom=float((distance<1).sum()/len(x)),max_penetration=float(depth.max()))
            max_error=max(max_error,max(abs(geometry[k]-v) for k,v in independent_geometry.items()))
            side_wrong=0
            if len(side):
                c1,a1,b1,d1=side.T;ref=mapping['reference']
                v=(np.cross(x[a1]-x[c1],x[b1]-x[c1])*(x[d1]-x[c1])).sum(1)
                vr=(np.cross(ref[a1]-ref[c1],ref[b1]-ref[c1])*(ref[d1]-ref[c1])).sum(1)
                side_wrong=int((v*vr<=0).sum())
            xp=x[ca]-x[ca].mean(0);yp=target[ca]-target[ca].mean(0)
            u,_,vt=np.linalg.svd(xp.T@yp);rotation=u@np.diag([1,1,np.linalg.det(u@vt)])@vt
            rmsd=float(np.sqrt(np.mean(np.sum((xp@rotation-yp)**2,axis=1))))
            s1_branch=measure_connections(x0,anchors,item['sequence'])['nearest_omega_sign']
            connection=measure_connections(x,anchors,item['sequence'],s1_branch)
            nearest=measure_connections(x,anchors,item['sequence'])
            worst=[]
            for j in np.argsort(depth,kind='stable')[-10:][::-1]:
                left,right=pairs[j]
                worst.append(dict(atoms=[dict(chain=str(atoms.chain_id[k]),residue=int(residues[k]),atom=str(names[k])) for k in [left,right]],
                    distance=float(distance[j]),penetration=float(depth[j])))
            records.append(dict(pdb_id=item['pdb_id'],group_id=item['group_id'],seed=seed,steps=steps,
                all_atom_lddt=aa_score,ca_lddt=ca_score,ca_aligned_rmsd=rmsd,geometry=geometry,
                sidechain_checked_wrong=side_wrong,strict_checked_chirality=geometry['chirality_fraction']==1 and side_wrong==0,
                absolute_failures=absolute_failures(geometry),severe_both_backbone=int(((distance<1)&bone[pairs[:,0]]&bone[pairs[:,1]]).sum()),
                worst_pairs=worst,connection_max_to_s1_branch={k:float(np.abs(v).max()) for k,v in connection['residuals'].items()},
                legacy_joint_pass=None,legacy_joint_not_applicable='raw-only; no repair displacement contract',
                connection_distribution=describe_connection_distribution(nearest,item['sequence'],calibration),
                omega_nearest_branch_max=float(nearest['residuals']['omega'].max()),
                gt_branch_mismatches=int((nearest['nearest_omega_sign']!=gt_branch).sum()),
                schedule=entry['schedule'],seconds=entry['seconds'],nfe=steps))
    assert len(records)==12 and max_error<1e-8
    contrasts=[]
    for item in lock['rows']:
        for seed in lock['seeds']:
            base=next(r for r in records if r['pdb_id']==item['pdb_id'] and r['seed']==seed and r['steps']==1)
            for steps in [2,5]:
                value=next(r for r in records if r['pdb_id']==item['pdb_id'] and r['seed']==seed and r['steps']==steps)
                contrasts.append(dict(pdb_id=item['pdb_id'],seed=seed,steps=steps,
                    delta_aa=value['all_atom_lddt']-base['all_atom_lddt'],delta_ca=value['ca_lddt']-base['ca_lddt'],
                    severe_before=base['geometry']['severe_pairs'],severe_after=value['geometry']['severe_pairs']))
    write_json(root/'evaluation.json',dict(verified=True,outputs=12,archived_s1_replays=4,metric_max_abs=max_error,
        lock_sha256=sha256(root/'lock.json'),script_sha256=sha256(Path(__file__)),records=records,contrasts=contrasts,
        scope='selected2 diagnostic; no repair/training/generalization/deployment claim'))
    with (root/'contrasts.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(contrasts[0]));writer.writeheader();writer.writerows(contrasts)
    print(json.dumps(dict(verified=12,archived_s1_exact=4,metric_max_abs=max_error)),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True)
    audit_step_reference(parser.parse_args().root)
