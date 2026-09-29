#!/usr/bin/env python3
"""Independent artifact replay, paired chart check, and joint/quality recomputation."""
import argparse
import json
from pathlib import Path

import numpy as np
import torch

from audit_anchored_geometry import replay, phase, cosine
from audit_local_projection_gt import score
from fastglycan.articulated_output import ArticulatedOutput
from fastglycan.anchored_geometry import PoseVariables
from fastglycan.hybrid_geometry import GeometryTopology
from fastglycan.paired_teacher_protocol import sha256, write_json
from onestepfold.data.gt_materializer import ATOM37_INDEX


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root
    lock=json.loads((root/'lock.json').read_text());source=Path(lock['source'])
    report=json.loads((root/'report.json').read_text());selection=json.loads((source/'selection.json').read_text())
    assert report['complete'] and report['expected']==32 and len(report['rows'])==32
    assert report['lock_sha256']==sha256(root/'lock.json')
    for path,value in lock['hashes'].items():assert sha256(Path(path))==value
    outcomes=[];paired=[]
    for row in report['rows']:
        index=row['index'];item=selection[index//4];g=item['group_id'];packet=source/'chemistry'/g
        if not row['success']:
            reason=json.loads((packet/'report.json').read_text())
            outcomes.append(dict(index=index,verified=False,source_skipped=not reason['passed'],
                                 reason=row.get('source_failure',row.get('error','unknown failure'))))
            continue
        assert row['group_id']==g and row['seed']==[12345,54321][(index//2)%2]
        assert row['arm']==['zero','fitted'][index%2]
        folder=root/'cases'/f'{index:02d}'
        for file,key in [('coordinates.npz','coordinates_sha256'),('values.pt','values_sha256')]:
            assert sha256(folder/file)==row[key]
        data=dict(np.load(folder/'coordinates.npz'));mapping=dict(np.load(packet/'mapping.npz'))
        inv=dict(np.load(source/'data'/g/'inventory.npz'));gt=dict(np.load(source/'data'/g/'gt.npz'))
        names,residues=data['atom_names'],data['residue_ids']
        assert np.array_equal(names,inv['atom_name']) and np.array_equal(residues,inv['residue_id'])
        ai=np.array([ATOM37_INDEX[n] for n in names]);ri=residues-1
        assert (gt['atom37_mask'][ri,ai]&gt['residue_mask'][ri]).all()
        assert np.array_equal(data['target'],gt['atom37_positions'][ri,ai])
        assert np.array_equal(data['raw'],np.load(source/'data'/g/f'native_{row["seed"]}.npy'))
        adapter=ArticulatedOutput(mapping['reference'],names,residues,item['sequence'],
                                  json.loads((packet/'variants.json').read_text())).double()
        variables=PoseVariables(adapter,torch.tensor(data['raw']))
        assert np.max(np.abs(variables.initial.numpy()-data['local']))<1e-8
        values=torch.load(folder/'values.pt',map_location='cpu',weights_only=True)
        replay_error=0.
        for label,key in [('start','initial'),('final','final')]:
            with torch.no_grad():
                for par,v in zip(variables.variables,values[key],strict=True):par.copy_(v)
            replay_error=max(replay_error,float(np.max(np.abs(replay(variables)-data[label]))))
        assert replay_error<1e-8
        old=source/'fits'/f'{index//4*3+1+(index//2)%2:02d}'
        old_coords=dict(np.load(old/'coordinates.npz'))
        if row['arm']=='zero':assert all(torch.count_nonzero(v)==0 for v in values['initial'])
        else:
            old_values=torch.load(old/'values.pt',map_location='cpu',weights_only=True)
            assert all(torch.equal(x,y) for x,y in zip(old_values,values['initial'],strict=True))
        assert np.max(np.abs(data['start']-old_coords['initial' if row['arm']=='zero' else 'final']))<1e-8
        atoms=torch.load(packet/'native.pt',map_location='cpu',weights_only=False)['atoms']
        top=GeometryTopology(atoms,mapping['reference']);bonds=top.bonds.numpy();pairs=top.pairs.numpy()
        ca,n,c,cb=top.centres.numpy().T;ca_mask=names=='CA'
        anchors=np.array([[int(np.flatnonzero((residues==j)&(names==n))[0]) for n in ['N','CA','C','O']]
                          for j in range(1,len(item['sequence'])+1)])
        side=np.array([[int(np.flatnonzero((residues==j)&(names==n))[0])
                       for n in ['CB','CA','CG1' if aa=='I' else 'OG1','CG2']]
                       for j,aa in enumerate(item['sequence'],1) if aa in 'IT'],dtype=int).reshape(-1,4)
        sc,sa,sb,sd=side.T;ref=mapping['reference']
        side_ref=np.sum(np.cross(ref[sa]-ref[sc],ref[sb]-ref[sc])*(ref[sd]-ref[sc]),axis=1)
        metric_error=0.
        for label in ['raw','local','start','final']:
            x=data[label];saved=row['metrics'][label]
            per,valid=score(x,data['target'],residues);cap,cav=score(x[ca_mask],data['target'][ca_mask],residues[ca_mask])
            checks=[(float(per[valid].mean()),saved['all_atom_lddt']),(float(cap[cav].mean()),saved['ca_lddt'])]
            residual=np.linalg.norm(x[bonds[:,0]]-x[bonds[:,1]],axis=1)-top.ideal.numpy()
            distance=np.linalg.norm(x[pairs[:,0]]-x[pairs[:,1]],axis=1)
            volume=np.sum(np.cross(x[n]-x[ca],x[c]-x[ca])*(x[cb]-x[ca]),axis=1)
            geom=dict(bond_rmse=float(np.sqrt(np.mean(residual**2))),
                peptide_mae=float(np.abs(residual[top.peptide.numpy()]).mean()),
                chirality_fraction=float((volume*top.volumes.numpy()>0).mean()),
                severe_pairs=int((distance<1).sum()),severe_pairs_per_atom=float((distance<1).sum()/len(x)),
                max_penetration=float(np.maximum(0,top.radii.numpy()[pairs].sum(-1)-distance).max()))
            checks += [(value,saved['geometry'][key]) for key,value in geom.items()]
            side_ok=bool((np.sum(np.cross(x[sa]-x[sc],x[sb]-x[sc])*(x[sd]-x[sc]),axis=1)*side_ref>0).all())
            chirality=geom['chirality_fraction']==1 and side_ok
            edges={k:[] for k in ['cn','angle_c','angle_n','omega','carbonyl']}
            for j,(left,right) in enumerate(zip(anchors,anchors[1:])):
                _,pa,pc,po=left;nn,na,_,_=right
                omega=1 if phase(data['raw'],[pa,pc,nn,na])[0]>=0 else -1
                edges['cn'].append(np.linalg.norm(x[pc]-x[nn])-(1.341 if item['sequence'][j+1]=='P' else 1.329))
                edges['angle_c'].append(cosine(x[pa],x[pc],x[nn])+.4473)
                edges['angle_n'].append(cosine(x[pc],x[nn],x[na])+.5203)
                edges['omega'].append(np.linalg.norm(phase(x,[pa,pc,nn,na])-[omega,0]))
                edges['carbonyl'].append(np.linalg.norm(phase(x,[nn,pa,pc,po])-[-1,0]))
            checks += [(float(np.abs(v).max()),saved['connection_max'][k]) for k,v in edges.items()]
            connected=all(np.max(np.abs(edges[k]))<=tol+1e-6 for k,tol in
                          dict(cn=.03,angle_c=.04,angle_n=.04,omega=.1,carbonyl=.1).items())
            diff=((x-data['raw'])**2).sum(-1);hr=float(np.sqrt(diff.mean()));cr=float(np.sqrt(diff[ca_mask].mean()))
            checks += [(hr,saved['preservation']['heavy_rms']),(cr,saved['preservation']['ca_rms']),
                       (float(np.sqrt(diff.max())),saved['preservation']['max_displacement'])]
            accepted=(geom['bond_rmse']<=.25 and geom['peptide_mae']<=.15 and geom['severe_pairs_per_atom']<=.02
                      and geom['max_penetration']<=2 and chirality and connected and hr<=2 and cr<=1)
            assert bool(accepted)==saved['joint_pass'] and bool(connected)==saved['connection_pass']
            assert bool(chirality)==saved['all_checked_chirality_pass']
            metric_error=max(metric_error,max(abs(a-b) for a,b in checks))
        assert metric_error<1e-8
        outcomes.append(dict(index=index,verified=True,pose_max_abs=replay_error,metric_max_abs=metric_error))
    for i in range(0,32,2):
        a,b=report['rows'][i:i+2]
        if not (a['success'] and b['success']):
            paired.append(dict(index=i//2,paired=False));continue
        for key in ['chart_sha256','objective_sha256','raw_sha256']:assert a[key]==b[key]
        x=dict(np.load(root/'cases'/f'{i:02d}'/'coordinates.npz'))
        y=dict(np.load(root/'cases'/f'{i+1:02d}'/'coordinates.npz'))
        assert all(np.array_equal(x[k],y[k]) for k in ['raw','local','target','atom_names','residue_ids'])
        paired.append(dict(index=i//2,paired=True,chart_sha256=a['chart_sha256'],objective_sha256=a['objective_sha256']))
    write_json(root/'audit.json',dict(complete=True,report_sha256=sha256(root/'report.json'),
        script_sha256=sha256(Path(__file__)),verified=sum(x['verified'] for x in outcomes),
        paired=sum(x['paired'] for x in paired),cases=outcomes,pairs=paired))


if __name__=='__main__':main()
