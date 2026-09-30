#!/usr/bin/env python3
"""Independent saved-pose/geometry audit and locked local-screen summary."""
import argparse
import csv
import json
from pathlib import Path

import numpy as np
import torch

from audit_anchored_geometry import replay
from audit_local_projection_gt import score
from fastglycan.articulated_output import ArticulatedOutput
from fastglycan.articulated_reference import geometry_invariants
from fastglycan.anchored_geometry import PoseVariables
from fastglycan.hybrid_geometry import GeometryTopology
from fastglycan.connection_audit import measure_connections,TOLERANCES
from fastglycan.paired_teacher_protocol import sha256,write_json


def audit_sidechain_trial(root):
    torch.set_num_threads(1);lock=json.loads((root/'lock.json').read_text());source=Path(lock['source'])
    coupled=lock['contract']=='fixed_backbone_sidechain_repulsion_v1'
    assert coupled or lock['contract']=='fixed_backbone_sidechain_fit_v1'
    report=json.loads((root/'report.json').read_text());selection=json.loads((source/'selection.json').read_text())
    assert report['complete'] and report['lock_sha256']==sha256(root/'lock.json') and len(report['rows'])==16
    for p,h in lock['hashes'].items():assert sha256(Path(p))==h
    outcomes=[];pairs=[]
    for row in report['rows']:
        item=selection[row['index']//2];packet=source/'chemistry'/item['group_id']
        if not row['success']:
            assert row.get('not_run') and not json.loads((packet/'report.json').read_text())['passed']
            outcomes.append(dict(index=row['index'],verified=False,source_skip=True));continue
        folder=root/'cases'/f'{row["index"]:02d}'
        for name,key in [('coordinates.npz','coordinates_sha256'),('values.pt','values_sha256')]:assert sha256(folder/name)==row[key]
        d=dict(np.load(folder/'coordinates.npz'));m=dict(np.load(packet/'mapping.npz'));names=d['atom_names'];res=d['residue_ids'];seq=item['sequence']
        old=dict(np.load(Path(lock['baseline'])/'cases'/f'{2*row["index"]+1:02d}'/'coordinates.npz'))
        assert all(np.array_equal(d[k],old[k]) for k in ['raw','target','output_reference','atom_names','residue_ids'])
        assert np.max(np.abs(d['initial']-old['local']))<1e-8 and np.array_equal(d['target'],m['coordinates']) and m['mask'].all()
        variants=json.loads((packet/'variants.json').read_text())
        adapter=ArticulatedOutput(d['output_reference'],names,res,seq,variants).double();pose=PoseVariables(adapter,torch.tensor(d['raw']))
        state=torch.load(folder/'values.pt',weights_only=True,map_location='cpu');mobile=np.zeros(len(names),bool);dof=0
        for group,q,values,mask in zip(pose.groups,pose.variables,state['values'],state['masks'],strict=True):
            expected=torch.zeros_like(q);nn=names[group.indices[0].numpy()]
            for j,rotation in enumerate(group.rotations):
                if all(nn[k] not in ['N','CA','C','O','OXT'] for k in rotation.moving):
                    expected[:,6+j]=1;mobile[group.indices[:,list(rotation.moving)].numpy().ravel()]=True
            assert torch.equal(expected,mask) and torch.count_nonzero(values[expected==0])==0
            dof+=int(expected.sum())
            with torch.no_grad():q.copy_(values)
        assert dof==row['fit']['eligible_dof'] and np.array_equal(mobile,d['mobile'])
        assert row['no_mobile_residues']==[int(r) for r in np.unique(res) if not mobile[res==r].any()]
        error=float(np.max(np.abs(replay(pose)-d['final'])));assert error<1e-8
        assert np.array_equal(d['initial'][~mobile],d['final'][~mobile])
        invariant=0.
        for group in adapter.groups:
            nn=names[group.indices[0].numpy()].tolist()
            # The exact per-residue variant, including termini, defines all angles.
            first=int(res[int(group.indices[0,0])]);key=__import__('fastglycan.articulated_output',fromlist=['AA']).AA[seq[first-1]]+':'+','.join(nn)
            for ii in group.indices.numpy():
                before=geometry_invariants(d['initial'][ii],variants[key]['bonds']);after=geometry_invariants(d['final'][ii],variants[key]['bonds'])
                invariant=max(invariant,max(float(np.max(np.abs(a-b))) for a,b in zip(before,after)))
        assert invariant<1e-8
        atoms=torch.load(packet/'native.pt',weights_only=False,map_location='cpu')['atoms'];top=GeometryTopology(atoms,m['reference'])
        bonds=top.bonds.numpy();pairs_ix=top.pairs.numpy();ca,n,c,cb=top.centres.numpy().T;ca_mask=names=='CA';bone=np.isin(names,['N','CA','C','O','OXT'])
        if coupled:
            variable=np.zeros(len(pairs_ix),bool)
            for group in adapter.groups:
                nn=names[group.indices[0].numpy()]
                for rotation in group.rotations:
                    if set(nn[list(rotation.moving)]).intersection({'N','CA','C','O','OXT'}):continue
                    for ii in group.indices.numpy():
                        moving=set(ii[list(rotation.moving)])-set(ii[[rotation.parent,rotation.child]])
                        other=set(range(len(names)))-set(ii[list(rotation.moving)])-{int(ii[rotation.parent])}
                        x=np.isin(pairs_ix[:,0],list(moving));y=np.isin(pairs_ix[:,1],list(other))
                        z=np.isin(pairs_ix[:,1],list(moving));w=np.isin(pairs_ix[:,0],list(other))
                        variable|=(x&y)|(z&w)
            assert np.array_equal(variable,d['collision_pair_mask']) and int(variable.sum())==row['collision']['pairs']
            assert row['collision']['excluded_pairs']==int((~variable).sum()) and row['collision']['weight']==1.
            ix=pairs_ix[~variable]
            fixed_distance_error=float(np.max(np.abs(np.linalg.norm(d['initial'][ix[:,0]]-d['initial'][ix[:,1]],axis=1)-np.linalg.norm(d['final'][ix[:,0]]-d['final'][ix[:,1]],axis=1)))) if len(ix) else 0.
            assert fixed_distance_error<1e-8
        collision_error=0.;collision_diagnostics={}

        anchors=np.array([[np.flatnonzero((res==r)&(names==n))[0] for n in ['N','CA','C','O']] for r in range(1,len(seq)+1)])
        raw_branch=measure_connections(d['raw'],anchors,seq)['nearest_omega_sign'];metric_error=0.
        side=np.array([[np.flatnonzero((res==r)&(names==n))[0] for n in ['CB','CA','CG1' if aa=='I' else 'OG1','CG2']] for r,aa in enumerate(seq,1) if aa in 'IT'],int).reshape(-1,4)
        a,b,c1,d1=side.T
        def volumes(x):return np.sum(np.cross(x[b]-x[a],x[c1]-x[a])*(x[d1]-x[a]),axis=1)
        refvol=volumes(m['reference'])
        for label in ['initial','final']:
            x=d[label];saved=row['metrics'][label];per,valid=score(x,d['target'],res);pc,vc=score(x[ca_mask],d['target'][ca_mask],res[ca_mask])
            distances=np.linalg.norm(x[pairs_ix[:,0]]-x[pairs_ix[:,1]],axis=1);depths=top.radii.numpy()[pairs_ix].sum(1)-distances
            residual=np.linalg.norm(x[bonds[:,0]]-x[bonds[:,1]],axis=1)-top.ideal.numpy()
            signs=np.sum(np.cross(x[n]-x[ca],x[c]-x[ca])*(x[cb]-x[ca]),axis=1)*top.volumes.numpy()
            geometry=dict(bond_rmse=float(np.sqrt(np.mean(residual**2))),peptide_mae=float(np.abs(residual[top.peptide.numpy()]).mean()),
                chirality_fraction=float((signs>0).mean()),severe_pairs=int((distances<1).sum()),severe_pairs_per_atom=float((distances<1).sum()/len(x)),max_penetration=float(np.maximum(0,depths).max()))
            checks=[(float(per[valid].mean()),saved['all_atom_lddt']),(float(pc[vc].mean()),saved['ca_lddt'])]
            checks += [(v,saved['geometry'][k]) for k,v in geometry.items()]
            chirality=bool((signs>0).all() and (volumes(x)*refvol>0).all());assert chirality==saved['checked_chirality']
            edges=measure_connections(x,anchors,seq,raw_branch)['residuals'];checks += [(float(np.abs(v).max()),saved['connection_max'][k]) for k,v in edges.items()]
            assert saved['connection_pass']==all(np.abs(v).max()<=TOLERANCES[k]+1e-6 for k,v in edges.items())
            squared=((x-d['raw'])**2).sum(1);hr=float(np.sqrt(squared.mean()));cr=float(np.sqrt(squared[ca_mask].mean()))
            checks += [(hr,saved['preservation']['heavy_rms']),(cr,saved['preservation']['ca_rms']),(float(np.sqrt(squared.max())),saved['preservation']['max_displacement'])]
            assert saved['preservation']['accepted']==(hr<=2 and cr<=1)
            checks.append((float(squared[~bone].mean()),row['fit']['initial_mse' if label=='initial' else 'final_mse']))
            if coupled:
                vdepth=depths[variable];mean=float(np.maximum(vdepth-1.5,0).dot(np.maximum(vdepth-1.5,0))/len(x)/.25)
                tail=float(np.mean(np.maximum(np.sort(vdepth)[-16:]-1.9,0)**2/.01)) if len(vdepth) else 0.
                largest=int(np.argmax(depths))
                collision_diagnostics[label]=dict(variable_severe=int((distances[variable]<1).sum()),
                    excluded_severe=int((distances[~variable]<1).sum()),
                    variable_max_penetration=float(np.maximum(0,vdepth).max()) if len(vdepth) else 0.,
                    excluded_max_penetration=float(np.maximum(0,depths[~variable]).max()) if (~variable).any() else 0.,
                    worst_pair=[dict(residue=int(res[i]),atom=str(names[i])) for i in pairs_ix[largest]],
                    worst_pair_variable=bool(variable[largest]),worst_distance=float(distances[largest]))
                saved_terms=row['collision'][label]
                collision_error=max(collision_error,abs(mean-saved_terms['mean']),abs(tail-saved_terms['tail']),abs(mean+tail+squared[~bone].mean()-row['collision'][label+'_objective']))
                assert collision_error<1e-8

            metric_error=max(metric_error,max(abs(float(a)-float(b)) for a,b in checks))
        assert metric_error<1e-8 and np.array_equal(d['initial'][bone],d['final'][bone])
        outcomes.append(dict(index=row['index'],verified=True,pose_max_abs=error,metric_max_abs=metric_error,invariant_max_abs=invariant,collision_objective_max_abs=collision_error,excluded_distance_max_abs=fixed_distance_error if coupled else None,collision_diagnostics=collision_diagnostics))
        a=row['metrics']['initial'];b=row['metrics']['final']
        pairs.append(dict(pdb_id=item['pdb_id'],seed=row['seed'],delta_aa=b['all_atom_lddt']-a['all_atom_lddt'],delta_ca=b['ca_lddt']-a['ca_lddt'],
            initial_aa=a['all_atom_lddt'],final_aa=b['all_atom_lddt'],initial_severe=a['geometry']['severe_pairs'],final_severe=b['geometry']['severe_pairs'],
            initial_penetration=a['geometry']['max_penetration'],final_penetration=b['geometry']['max_penetration'],
            chirality=b['checked_chirality'],budget=b['preservation']['accepted'],seconds=row['fit_seconds'],iterations=row['fit']['iterations'],closures=row['fit']['closure_calls'],
            eligible_dof=dof,no_mobile_residues=len(row['no_mobile_residues']),initial_mse=row['fit']['initial_mse'],final_mse=row['fit']['final_mse'],
            initial_joint=a['connection_pass'],final_joint=b['connection_pass']))
    assert len(pairs)==14 and len(outcomes)==16
    proteins=[dict(pdb_id=p,delta_aa=float(np.mean([x['delta_aa'] for x in pairs if x['pdb_id']==p])),delta_ca=float(np.mean([x['delta_ca'] for x in pairs if x['pdb_id']==p]))) for p in sorted({x['pdb_id'] for x in pairs})]
    da=float(np.mean([p['delta_aa'] for p in proteins]));limits=lock['screen']
    screen=dict(quality=da>0,backbone_ca_unchanged=all(x['delta_ca']==0 for x in pairs),chirality=all(x['chirality'] for x in pairs),budget=all(x['budget'] for x in pairs),
        severe_total=sum(x['final_severe'] for x in pairs)<=limits['severe_total_max'],zero_severe=sum(x['final_severe']==0 for x in pairs)>=limits['zero_severe_min'],
        maximum_penetration=max(x['final_penetration'] for x in pairs)<=limits['penetration_max'])
    write_json(root/'audit.json',dict(complete=True,report_sha256=sha256(root/'report.json'),script_sha256=sha256(Path(__file__)),verified=len(pairs),cases=outcomes))
    write_json(root/'summary.json',dict(audit_sha256=sha256(root/'audit.json'),pairs=pairs,proteins=proteins,mean_delta_aa=da,screen=screen,local_candidate=all(screen.values()),deployment_acceptance=False))
    for name,entries in [('paired_predictions',pairs),('paired_proteins',proteins)]:
        with (root/(name+'.csv')).open('w',newline='') as out:
            w=csv.DictWriter(out,fieldnames=list(entries[0]),lineterminator='\n');w.writeheader();w.writerows(entries)
    print(json.dumps(dict(verified=len(pairs),delta_aa=da,screen=screen,local_candidate=all(screen.values()))))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);audit_sidechain_trial(p.parse_args().root)
