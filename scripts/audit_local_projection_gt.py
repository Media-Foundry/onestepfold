#!/usr/bin/env python3
"""Artifact-level independent pose replay, dense scores and geometry audit."""
import argparse
import json
from pathlib import Path

import numpy as np
import torch
from scipy.spatial.distance import cdist

from audit_anchored_geometry import replay, phase, cosine
from fastglycan.articulated_output import ArticulatedOutput
from fastglycan.anchored_geometry import PoseVariables
from fastglycan.hybrid_geometry import GeometryTopology
from fastglycan.paired_teacher_protocol import sha256, write_json


def score(x, y, residue):
    reference=cdist(y,y); measured=cdist(x,x)
    keep=(reference<15)&(residue[:,None]!=residue[None,:])
    counts=keep.sum(1); valid=counts>0
    agreement=np.zeros_like(reference)
    for threshold in (.5,1.,2.,4.):agreement+=((np.abs(measured-reference)<threshold)&keep)/4
    per=np.zeros(len(x));per[valid]=agreement.sum(1)[valid]/counts[valid]
    return per,valid


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();r=a.root
    report=json.loads((r/'report.json').read_text());lock=json.loads((r/'execution_lock.json').read_text())
    assert report['complete'] and report['lock_sha256']==sha256(r/'execution_lock.json')
    assert len(report['rows'])==24 and all(x['returncode']==0 for x in report['execution'])
    for path,d in lock['hashes'].items():assert sha256(Path(path))==d
    selection=json.loads((r/'selection.json').read_text());audit=[]
    for row in report['rows']:
        i=row['index']; selected=selection[i//3];g=selected['group_id'];assert row['group_id']==g
        packet=r/'chemistry'/g; source=json.loads((packet/'report.json').read_text())
        if not row['success']:
            assert not source['passed'] and row['not_run']
            audit.append(dict(index=i,source_failed=True,fit_verified=False));continue
        folder=r/'fits'/f'{i:02d}'
        for name,key in [('coordinates.npz','coordinates_sha256'),('values.pt','values_sha256')]:
            assert sha256(folder/name)==row[key]
        data=dict(np.load(folder/'coordinates.npz'));m=dict(np.load(packet/'mapping.npz'))
        inv=dict(np.load(r/'data'/g/'inventory.npz'))
        assert m['mask'].all() and np.array_equal(data['target'],m['coordinates'])
        assert np.array_equal(data['atom_names'],inv['atom_name']) and np.array_equal(data['residue_ids'],inv['residue_id'])
        expected=m['coordinates'] if row['arm']=='gt_self' else np.load(r/'data'/g/(row['arm']+'.npy'))
        assert np.array_equal(data['raw'],expected)
        adapter=ArticulatedOutput(m['reference'],m['atom_names'],m['residue_ids'],selected['sequence'],
                                  json.loads((packet/'variants.json').read_text())).double()
        variables=PoseVariables(adapter,torch.tensor(data['raw']))
        assert np.max(np.abs(variables.initial.numpy()-data['initial']))<1e-8
        values=torch.load(folder/'values.pt',map_location='cpu',weights_only=True)
        with torch.no_grad():
            for parameter,value in zip(variables.variables,values,strict=True):parameter.copy_(value)
        replay_error=float(np.max(np.abs(replay(variables)-data['final'])));assert replay_error<1e-8
        atoms=torch.load(packet/'native.pt',map_location='cpu',weights_only=False)['atoms']
        top=GeometryTopology(atoms,m['reference']);pairs=top.pairs.numpy();bonds=top.bonds.numpy()
        ca,n,c,cb=top.centres.numpy().T;ri=data['residue_ids'];names=data['atom_names']
        bone=np.isin(names,['N','CA','C','O']);only_ca=names=='CA'
        anchors=np.array([[int(np.flatnonzero((ri==j)&(names==n))[0]) for n in ['N','CA','C','O']]
                          for j in range(1,len(selected['sequence'])+1)])
        error=0.
        for label in ['raw','initial','final']:
            x=data[label];saved=row['metrics'][label];per,valid=score(x,data['target'],ri)
            cp,cv=score(x[only_ca],data['target'][only_ca],ri[only_ca])
            checks=[(float(per[valid].mean()),saved['all_atom_lddt']),(float(cp[cv].mean()),saved['ca_lddt']),
                    (float(per[valid&bone].sum()/valid.sum()),saved['atom_centred']['backbone_contribution']),
                    (float(per[valid&~bone].sum()/valid.sum()),saved['atom_centred']['sidechain_contribution'])]
            diff=np.sum((x-data['raw'])**2,axis=1)
            checks += [(float(diff.mean()),saved['raw_mse']),(float(diff[bone].mean()),saved['backbone_raw_mse']),
                       (float(diff[~bone].mean()),saved['sidechain_raw_mse'])]
            distances=np.linalg.norm(x[pairs[:,0]]-x[pairs[:,1]],axis=1)
            residual=np.linalg.norm(x[bonds[:,0]]-x[bonds[:,1]],axis=1)-top.ideal.numpy()
            volume=np.sum(np.cross(x[n]-x[ca],x[c]-x[ca])*(x[cb]-x[ca]),axis=1)
            geom=dict(bond_rmse=float(np.sqrt(np.mean(residual**2))),
                peptide_mae=float(np.abs(residual[top.peptide.numpy()]).mean()),
                chirality_fraction=float((volume*top.volumes.numpy()>0).mean()),
                severe_pairs=int((distances<1).sum()),
                max_penetration=float(np.maximum(0,top.radii.numpy()[pairs].sum(-1)-distances).max()))
            checks += [(v,saved['geometry'][k]) for k,v in geom.items()]
            edges={k:[] for k in ['cn','angle_c','angle_n','omega','carbonyl']}
            for j,(left,right) in enumerate(zip(anchors,anchors[1:])):
                _,pa,pc,po=left;nn,na,_,_=right
                omega=1 if phase(data['raw'],[pa,pc,nn,na])[0]>=0 else -1
                edges['cn'].append(np.linalg.norm(x[pc]-x[nn])-(1.341 if selected['sequence'][j+1]=='P' else 1.329))
                edges['angle_c'].append(cosine(x[pa],x[pc],x[nn])+.4473)
                edges['angle_n'].append(cosine(x[pc],x[nn],x[na])+.5203)
                edges['omega'].append(np.linalg.norm(phase(x,[pa,pc,nn,na])-[omega,0]))
                edges['carbonyl'].append(np.linalg.norm(phase(x,[nn,pa,pc,po])-[-1,0]))
            checks += [(float(np.abs(v).max()),saved['connection_max'][k]) for k,v in edges.items()]
            error=max(error,max(abs(a-b) for a,b in checks))
        assert error<1e-8
        audit.append(dict(index=i,fit_verified=True,pose_max_abs=replay_error,metric_max_abs=error))
    write_json(r/'audit.json',dict(complete=True,report_sha256=sha256(r/'report.json'),
        script_sha256=sha256(Path(__file__)),verified_fits=sum(x['fit_verified'] for x in audit),
        retained_source_failures=sum(x.get('source_failed',False) for x in audit),cases=audit))


if __name__=='__main__':main()
