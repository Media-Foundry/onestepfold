#!/usr/bin/env python3
"""Descriptive residuals and worst identities, without new acceptance thresholds."""
import argparse
import json
from pathlib import Path

import numpy as np
import torch
from fastglycan.connection_audit import measure_connections, TOLERANCES
from fastglycan.hybrid_geometry import GeometryTopology
from fastglycan.paired_teacher_protocol import sha256, write_json


def describe_fresh_contact_geometry(root):
    torch.set_num_threads(1)
    lock=json.loads((root/'lock.json').read_text());assert lock['confirmation_contract']=='fresh_contact_v1'
    report=json.loads((root/'report.json').read_text());audit=json.loads((root/'audit.json').read_text())
    assert audit['report_sha256']==sha256(root/'report.json')
    source=Path(lock['source']);selection=json.loads((source/'selection.json').read_text())
    output=root/'geometry_details';output.mkdir(exist_ok=False);records=[]
    for row in report['rows']:
        if not row['success']:
            records.append(dict(index=row['index'],available=False,error=row.get('error','missing')));continue
        i=row['index'];item=selection[i//4];packet=source/'chemistry'/item['group_id']
        folder=root/'cases'/f'{i:02d}';assert sha256(folder/'coordinates.npz')==row['coordinates_sha256']
        arrays=dict(np.load(folder/'coordinates.npz'));mapping=dict(np.load(packet/'mapping.npz'))
        atoms=torch.load(packet/'native.pt',map_location='cpu',weights_only=False)['atoms']
        topology=GeometryTopology(atoms,mapping['reference']);pairs=topology.pairs.numpy();radii=topology.radii.numpy()
        names,residues=arrays['atom_names'],arrays['residue_ids'];bone=np.isin(names,['N','CA','C','O','OXT'])
        anchors=np.array([[int(np.flatnonzero((residues==r)&(names==n))[0]) for n in ['N','CA','C','O']]
            for r in range(1,len(item['sequence'])+1)])
        raw_branch=measure_connections(arrays['raw'],anchors,item['sequence'])['nearest_omega_sign']
        gt=measure_connections(arrays['target'],anchors,item['sequence'])
        saved=dict(residue_ids=residues,atom_names=names);phases={}
        for phase in ['raw','start','final']:
            x=arrays[phase];m=measure_connections(x,anchors,item['sequence'],raw_branch)
            connections={}
            for name,values in m['residuals'].items():
                absolute=np.abs(values);saved[phase+'_'+name]=values
                connections[name]=dict(mean_abs=float(absolute.mean()),
                    quantiles=dict(zip(['p50','p95','p99','max'],map(float,np.quantile(absolute,[.5,.95,.99,1])))),
                    legacy_exceeded=int((absolute>TOLERANCES[name]+1e-6).sum()),edges=len(values),
                    legacy_exceeded_fraction=float((absolute>TOLERANCES[name]+1e-6).mean()))
            distance=np.linalg.norm(x[pairs[:,0]]-x[pairs[:,1]],axis=1)
            depth=np.maximum(0,radii[pairs].sum(axis=1)-distance)
            severe=distance<1;worst=np.argsort(depth,kind='stable')[-10:][::-1]
            descriptions=[]
            for j in worst:
                a,b=pairs[j]
                descriptions.append(dict(atoms=[dict(chain=str(atoms.chain_id[k]),residue=int(residues[k]),atom=str(names[k])) for k in [a,b]],
                    distance=float(distance[j]),penetration=float(depth[j]),both_backbone=bool(bone[a] and bone[b])))
            displacement=np.linalg.norm(x-arrays['raw'],axis=1);maximum=int(displacement.argmax())
            saved[phase+'_atom_displacement']=displacement
            phases[phase]=dict(connections=connections,allowed_pairs=len(pairs),
                penetration_quantiles=dict(zip(['p50','p95','p99','max'],map(float,np.quantile(depth,[.5,.95,.99,1])))),
                positive_penetration_pairs=int((depth>0).sum()),severe_pairs=int(severe.sum()),
                severe_both_backbone=int((severe&bone[pairs[:,0]]&bone[pairs[:,1]]).sum()),worst_pairs=descriptions,
                atom_displacement_quantiles=dict(zip(['p50','p95','p99','max'],map(float,np.quantile(displacement,[.5,.95,.99,1])))),
                max_atom=dict(residue=int(residues[maximum]),atom=str(names[maximum]),backbone=bool(bone[maximum])),
                backbone_max_displacement=float(displacement[bone].max()),
                branch_mismatch_count=int((m['nearest_omega_sign']!=gt['nearest_omega_sign']).sum()))
        file=output/f'{i:02d}.npz';np.savez_compressed(file,**saved)
        records.append(dict(index=i,available=True,pdb_id=row['pdb_id'],group_id=item['group_id'],seed=row['seed'],
            arm=row['arm'],phases=phases,residuals_sha256=sha256(file)))
    write_json(root/'geometry_details.json',dict(report_sha256=sha256(root/'report.json'),
        script_sha256=sha256(Path(__file__)),records=records,
        scope='descriptive only; old thresholds unchanged; no replacement chemical gate'))
    print('Described geometry for',sum(r['available'] for r in records),'outputs',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    describe_fresh_contact_geometry(p.parse_args().root)
