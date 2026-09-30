#!/usr/bin/env python3
"""Read-only pair identities after the bounded sidechain fit; no reranking."""
import argparse
import json
from pathlib import Path

import numpy as np
import torch

from fastglycan.hybrid_geometry import GeometryTopology
from fastglycan.paired_teacher_protocol import sha256,write_json


def inspect_sidechain_collisions(root,output):
    lock=json.loads((root/'lock.json').read_text());report=json.loads((root/'report.json').read_text());audit=json.loads((root/'audit.json').read_text())
    assert audit['report_sha256']==sha256(root/'report.json') and audit['verified']==14
    rows=[];fixed_total=0;new_total=0;removed_total=0;shared_total=0
    for row in report['rows']:
        if not row['success']:continue
        path=root/'cases'/f'{row["index"]:02d}'/'coordinates.npz';assert sha256(path)==row['coordinates_sha256']
        d=dict(np.load(path));packet=Path(lock['source'])/'chemistry'/row['group_id'];m=dict(np.load(packet/'mapping.npz'))
        atoms=torch.load(packet/'native.pt',weights_only=False,map_location='cpu')['atoms'];top=GeometryTopology(atoms,m['reference'])
        pair=top.pairs.numpy();radii=top.radii.numpy()[pair].sum(1);dist={k:np.linalg.norm(d[k][pair[:,0]]-d[k][pair[:,1]],axis=1) for k in ['initial','final']}
        sets={k:set(np.flatnonzero(v<1).tolist()) for k,v in dist.items()}
        new=sets['final']-sets['initial'];gone=sets['initial']-sets['final'];shared=sets['initial']&sets['final']
        new_total+=len(new);removed_total+=len(gone);shared_total+=len(shared)
        immutable=~d['mobile'][pair].any(1);fixed=sets['final']&set(np.flatnonzero(immutable).tolist());fixed_total+=len(fixed)
        displacement=np.linalg.norm(d['final']-d['initial'],axis=1)
        def describe(j):
            a,b=pair[j];return dict(atoms=[dict(residue=int(d['residue_ids'][i]),name=str(d['atom_names'][i]),declared_mobile=bool(d['mobile'][i]),displacement=float(displacement[i])) for i in [a,b]],
                initial_distance=float(dist['initial'][j]),final_distance=float(dist['final'][j]),initial_penetration=float(radii[j]-dist['initial'][j]),final_penetration=float(radii[j]-dist['final'][j]),
                both_immutable=bool(immutable[j]),any_actual_change=bool((displacement[[a,b]]>1e-8).any()))
        worst=int(np.argmax(radii-dist['final']))
        assert len(sets['initial'])==row['metrics']['initial']['geometry']['severe_pairs'] and len(sets['final'])==row['metrics']['final']['geometry']['severe_pairs']
        rows.append(dict(index=row['index'],pdb_id=row['pdb_id'],seed=row['seed'],new=len(new),removed=len(gone),shared=len(shared),final_immutable=len(fixed),
            new_pairs=[describe(j) for j in sorted(new)],removed_pairs=[describe(j) for j in sorted(gone)],shared_pairs=[describe(j) for j in sorted(shared)],worst=describe(worst)))
    assert new_total+shared_total==41 and removed_total+shared_total==37
    assert all(not p['both_immutable'] and p['any_actual_change'] for r in rows for p in r['new_pairs'])
    write_json(output,dict(complete=True,report_sha256=sha256(root/'report.json'),audit_sha256=sha256(root/'audit.json'),script_sha256=sha256(Path(__file__)),
        new=new_total,removed=removed_total,shared=shared_total,final_both_immutable=fixed_total,rows=rows,
        scope='post-hoc pair identity analysis; declared mobile does not prove nonzero sensitivity; no causal force attribution'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();inspect_sidechain_collisions(a.root,a.output)
