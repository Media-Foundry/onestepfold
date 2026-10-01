#!/usr/bin/env python3
"""CPU-only independent target-distance, collision, stereocentre and selection audit."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import time
import numpy as np
import torch
from fastglycan.geometry_audit import independent_allowed_pairs
from fastglycan.hybrid_geometry import RADII
from fastglycan.backbone_sequence_task import backbone_candidate_accept
from fastglycan.paired_teacher_protocol import sha256, write_json


def audit_backbone_candidate(task):
    root,folder,row=task;root=Path(root);folder=Path(folder);torch.set_num_threads(1)
    pi=row['parent_index'];si=row['sequence_index']
    native=torch.load(folder/f'p{pi}_s{si}_topology.pt',map_location='cpu',weights_only=False)
    atoms=native['atoms'];reference=np.asarray(native['reference'],dtype=float)
    names=np.asarray(atoms.atom_name);res=np.asarray(atoms.res_id)
    allowed=independent_allowed_pairs(atoms);radii=np.array([RADII[str(e).upper()] for e in atoms.element])
    lookup={(int(r),str(n)):i for i,(r,n) in enumerate(zip(res,names))};centres=[];labels=[]
    for i,aa in enumerate(row['sequence'],1):
        if aa!='G':centres.append([lookup[i,a] for a in ['CA','N','C','CB']]);labels.append('CA')
        if aa in 'IT':centres.append([lookup[i,a] for a in ['CB','CA','CG1' if aa=='I' else 'OG1','CG2']]);labels.append(aa)
    centres=np.asarray(centres,dtype=int).reshape(-1,4)
    refvol=np.linalg.det(reference[centres[:,1:]]-reference[centres[:,0,None]])
    packet=torch.load(root/f'audit_{pi}/audit.pt',map_location='cpu',weights_only=False)
    pairs=packet['pairs'].numpy();desired=packet['distances'].numpy();errors=[]
    for seed,value in row['values'].items():
        file=folder/value['coordinate_file'];assert sha256(file)==value['coordinate_sha256']
        data=dict(np.load(file));x=data['coordinates'].reshape(-1,3).astype(float)
        assert np.isfinite(x).all() and str(data['sequence'])==row['sequence']
        for key,array in [('atom_names',names),('residue_ids',res),('chain_ids',atoms.chain_id)]:assert np.array_equal(data[key],array)
        assert np.array_equal(data['reference'],reference)
        d=np.linalg.norm(x[allowed[:,0]]-x[allowed[:,1]],axis=-1)
        penetration=np.maximum(0,radii[allowed].sum(1)-d)
        chem=value['chemistry'];legacy=chem['legacy_geometry']
        assert int((d<1).sum())==legacy['severe_pairs']
        vol=np.linalg.det(x[centres[:,1:]]-x[centres[:,0,None]]);wrong=vol*refvol<=0;ca=np.array(labels)=='CA'
        assert int(wrong[ca].sum())==chem['ca_wrong'] and int(wrong[~ca].sum())==chem['side_wrong']
        cx=x[names=='CA'];delta=np.linalg.norm(cx[pairs[:,0]]-cx[pairs[:,1]],axis=-1)-desired
        expected=np.where(np.abs(delta)<=1,.5*delta**2,np.abs(delta)-.5).mean()
        error=[abs(float(penetration.max())-legacy['max_penetration']),abs(float(expected)-value['task'])]
        assert error[0]<1e-6 and error[1]<1e-5,error
        errors.append(error)
    return dict(parent_index=pi,sequence_index=si,max_errors=np.max(errors,axis=0).tolist())


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root.resolve();started=time.monotonic()
    lock=json.loads((root/'lock.json').read_text());manifest=json.loads((root/'candidates_lock.json').read_text());report=json.loads((root/'report.json').read_text())
    tasks=[];records={}
    for i in range(8):
        folder=root/f'evaluate_{i}';r=json.loads((folder/'report.json').read_text());assert r['complete']
        for row in r['records']:tasks.append((str(root),str(folder),row));records[(row['parent_index'],row['sequence'])]=row
    with ProcessPoolExecutor(max_workers=8) as pool:checked=list(pool.map(audit_backbone_candidate,tasks))
    assert len(records)*3==manifest['expected_outputs']==report['predictions']
    selection=[]
    for i,proposal in enumerate(manifest['proposals']):
        parent=records[(i,proposal['parent'])]
        for arm,options in proposal['arms'].items():
            for option in options:
                changes=[j for j,(x,y) in enumerate(zip(proposal['parent'],option['sequence'])) if x!=y]
                assert changes==[option['position']] and option['from_aa']==proposal['parent'][changes[0]] and option['to_aa']==option['sequence'][changes[0]]
            eligible=[o for o in options if backbone_candidate_accept(records[(i,o['sequence'])]['values'][str(lock['proposal_seed'])],parent['values'][str(lock['proposal_seed'])])['accepted']]
            chosen=min(eligible,key=lambda o:(records[(i,o['sequence'])]['values'][str(lock['proposal_seed'])]['task'],o['sequence'])) if eligible else None
            expected=report['parents'][i]['arms'][arm]
            assert expected['selected_sequence']==(chosen['sequence'] if chosen else None)
            success=bool(chosen and all(backbone_candidate_accept(records[(i,chosen['sequence'])]['values'][str(seed)],parent['values'][str(seed)])['accepted'] for seed in lock['confirmation_seeds']))
            assert success==expected['selected_confirmed'];selection.append(dict(parent=i,arm=arm,confirmed=success))
    projection_errors=[]
    for i in range(4):
        r=json.loads((root/f'audit_{i}/report.json').read_text());path=root/f'audit_{i}/audit.pt';assert sha256(path)==r['artifact_sha256']
        packet=torch.load(path,map_location='cpu',weights_only=False)
        for j,v in enumerate(packet['directions']):
            for key,field in [('gq','native'),('reference_gq','reference')]:
                projection_errors.append(abs(float((packet[key].double()*v.double()).sum())-r['directions'][j][field]['right']))
    assert max(projection_errors)<1e-14
    output=dict(complete=True,outputs=report['predictions'],sequences=len(records),max_errors=np.max([r['max_errors'] for r in checked],axis=0).tolist(),
        error_order=['penetration_FP64_vs_FP32','target_distance_FP64_vs_FP32'],projection_max_error=max(projection_errors),selection=selection,
        seconds=time.monotonic()-started,source_sha256=sha256(Path(__file__)))
    write_json(root/'independent_audit.json',output);print(json.dumps(output))
