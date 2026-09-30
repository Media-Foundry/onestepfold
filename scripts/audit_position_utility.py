#!/usr/bin/env python3
"""Independent saved-coordinate contact/stereo/pair audit; no additional inference."""
import argparse,json,time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import torch
from scipy.spatial.distance import cdist
from scipy.special import expit
from fastglycan.geometry_audit import independent_allowed_pairs
from fastglycan.hybrid_geometry import RADII
from fastglycan.paired_teacher_protocol import sha256,write_json


def audit_hard_position_sequence(task):
    folder,row=task;folder=Path(folder);torch.set_num_threads(1)
    assert sha256(folder/row['topology_file'])==row['topology_sha256']
    native=torch.load(folder/row['topology_file'],map_location='cpu',weights_only=False)
    atoms=native['atoms'];reference=native['reference'].numpy();names=np.asarray(atoms.atom_name);res=np.asarray(atoms.res_id)
    pairs=independent_allowed_pairs(atoms);radii=np.array([RADII[str(e).upper()] for e in atoms.element]);lookup={(int(r),str(n)):i for r,n,i in zip(res,names,range(len(names)))}
    centres=[];kind=[]
    for i,aa in enumerate(row['sequence'],1):
        if aa!='G':centres.append([lookup[i,a] for a in ['CA','N','C','CB']]);kind.append('CA')
        if aa in 'IT':centres.append([lookup[i,a] for a in ['CB','CA','CG1' if aa=='I' else 'OG1','CG2']]);kind.append(aa)
    centres=np.asarray(centres,dtype=int).reshape(-1,4);base=np.linalg.det(reference[centres[:,1:]]-reference[centres[:,0,None]])
    errors=[];checked=[]
    for seed,value in row['values'].items():
        file=folder/value['coordinate_file'];assert sha256(file)==value['coordinate_sha256']
        packet=dict(np.load(file));x=packet['coordinates'].reshape(-1,3).astype(float)
        assert str(packet['sequence'])==row['sequence'] and np.array_equal(packet['atom_names'],names) and np.array_equal(packet['residue_ids'],res)
        distance=np.linalg.norm(x[pairs[:,0]]-x[pairs[:,1]],axis=-1);penetration=np.maximum(0,radii[pairs].sum(1)-distance)
        severe=int((distance<1).sum());v=np.linalg.det(x[centres[:,1:]]-x[centres[:,0,None]]);wrong=v*base<=0;isca=np.asarray(kind)=='CA'
        assert severe==value['geometry']['severe_pairs']
        assert int(wrong[isca].sum())==value['chemistry']['ca_wrong'] and int(wrong[~isca].sum())==value['chemistry']['side_wrong']
        error=abs(float(penetration.max())-value['geometry']['max_penetration']);assert error<1e-6
        ca=x[names=='CA'];d=cdist(ca,ca);idx=np.arange(len(ca));sep=np.abs(idx[:,None]-idx[None,:])
        contact=expit((8-d)/1.5)[sep>8].mean();clash=np.square(np.maximum(3-d[sep>1],0)).mean();chain=np.square(np.linalg.norm(np.diff(ca,axis=0),axis=1)-3.8).mean()
        loss=-contact+clash+.1*chain;task_error=abs(loss-value['task']);assert task_error<1e-5
        errors.append([error,task_error]);checked.append(dict(seed=int(seed),severe=severe,ca_wrong=int(wrong[isca].sum()),side_wrong=int(wrong[~isca].sum())))
    return dict(parent_index=row['parent_index'],sequence_index=row['sequence_index'],outputs=checked,max_errors=np.max(errors,axis=0).tolist())


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root.resolve();begin=time.monotonic()
    tasks=[]
    for i in range(8):
        folder=root/f'worker_{i}';d=json.loads((folder/'report.json').read_text());assert d['complete'];tasks.extend((str(folder),r) for r in d['records'])
    with ProcessPoolExecutor(max_workers=8) as pool:rows=list(pool.map(audit_hard_position_sequence,tasks))
    report=dict(complete=True,sequences=len(rows),outputs=sum(len(r['outputs']) for r in rows),max_errors=np.max([r['max_errors'] for r in rows],axis=0).tolist(),error_order=['penetration_fp64_vs_native_fp32','task_fp64_dense_vs_native_fp32'],rows=rows,seconds=time.monotonic()-begin,script_sha256=sha256(Path(__file__)))
    write_json(root/'coordinate_audit.json',report);print(json.dumps({k:v for k,v in report.items() if k!='rows'}))
