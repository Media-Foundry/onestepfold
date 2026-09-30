#!/usr/bin/env python3
"""Freeze an output-only whole CCD ideal-reference intervention after geometry preflight."""
import argparse
import json
from pathlib import Path

import numpy as np
import torch

from fastglycan.articulated_output import ArticulatedOutput
from fastglycan.ideal_output_reference import ideal_output_reference
from fastglycan.paired_teacher_protocol import sha256, write_json


def prepare_ideal_reference_trial(root, baseline, parameters):
    torch.set_num_threads(1)
    assert not (root/'lock.json').exists()
    previous=json.loads((baseline/'lock.json').read_text());audit=json.loads((baseline/'audit.json').read_text())
    assert previous['prediction_contract']=='c4_s1_confirmation_v1'
    assert audit['verified']==28 and audit['paired']==14 and audit['report_sha256']==sha256(baseline/'report.json')
    assert json.loads((baseline/'pipeline_exit.json').read_text())['returncode']==0
    for path,digest in previous['hashes'].items():assert sha256(Path(path))==digest
    document=json.loads(parameters.read_text());assert set(document['records'])==set('ACDEFGHIKLMNPQRSTVWY')
    source=Path(previous['source']);selection=json.loads((source/'selection.json').read_text())
    records=[]
    for item in selection:
        packet=source/'chemistry'/item['group_id'];chem=json.loads((packet/'report.json').read_text())
        if not chem['passed']:
            records.append(dict(pdb_id=item['pdb_id'],supported=False,reason=chem['error']));continue
        d=dict(np.load(packet/'mapping.npz'));variants=json.loads((packet/'variants.json').read_text())
        original=d['reference'];names=d['atom_names'];residues=d['residue_ids'];seq=item['sequence']
        updated,changes=ideal_output_reference(original,names,residues,seq,variants,document['records'])
        changing=(residues>1)&(residues<len(seq))&(names!='CA')
        assert np.array_equal(original[~changing],updated[~changing])
        repeat,_=ideal_output_reference(updated,names,residues,seq,variants,document['records'])
        assert np.max(np.abs(repeat-updated))<1e-12
        q,_=np.linalg.qr(np.random.default_rng(9302031).normal(size=(3,3)));q[:,-1]*=np.linalg.det(q)
        equiv,_=ideal_output_reference(original@q+3,names,residues,seq,variants,document['records'])
        assert np.max(np.abs(equiv-(updated@q+3)))<1e-12
        stereocentres=0;length_error=0.
        for i,aa in enumerate(seq,1):
            lookup={str(names[j]):int(j) for j in np.flatnonzero(residues==i)}
            centres=[]
            if aa!='G':centres.append(['CA','N','C','CB'])
            if aa in 'IT':centres.append(['CB','CA','CG1' if aa=='I' else 'OG1','CG2'])
            for atoms in centres:
                ix=[lookup[n] for n in atoms]
                a,b,c,e=original[ix];u,v,w,z=updated[ix]
                before=np.dot(np.cross(b-a,c-a),e-a);after=np.dot(np.cross(v-u,w-u),z-u)
                assert before*after>0;stereocentres+=1
            if i not in [1,len(seq)]:
                template=document['records'][aa];tn=template['atom_names'];xx=np.asarray(template['ideal'])
                for a,b,_ in template['bonds']:
                    measured=np.linalg.norm(updated[lookup[tn[a]]]-updated[lookup[tn[b]]])
                    length_error=max(length_error,abs(measured-np.linalg.norm(xx[a]-xx[b])))
        assert length_error<1e-12
        old=ArticulatedOutput(original,names,residues,seq,variants).double()
        new=ArticulatedOutput(updated,names,residues,seq,variants).double()
        local_error=0.;ca_error=0.;fallbacks=0
        for seed in previous['seeds']:
            raw=torch.tensor(np.load(source/'data'/item['group_id']/f'native_{seed}.npy'),dtype=torch.float64)
            with torch.no_grad():old_out=old(raw);new_out=new(raw)
            local_error=max(local_error,float((old_out['coordinate'][~changing]-new_out['coordinate'][~changing]).abs().max()))
            ca_error=max(ca_error,float((new_out['coordinate'][names=='CA']-raw[names=='CA']).abs().max()))
            fallbacks+=int(new_out['fallback_counts'].sum())
        assert local_error<1e-8 and ca_error<1e-8 and fallbacks==0
        records.append(dict(pdb_id=item['pdb_id'],supported=True,changed_residues=len(changes),
            checked_stereocentres=stereocentres,length_max_abs=length_error,unchanged_projection_max_abs=local_error,
            ca_projection_max_abs=ca_error,fallbacks=fallbacks,terminal_atoms_unchanged=True,
            ring_adjacency_unchanged=True,ring_geometry_from_ideal=True,idempotence_max_abs=float(np.max(np.abs(repeat-updated))),
            equivariance_max_abs=float(np.max(np.abs(equiv-(updated@q+3))))))
    assert sum(r['supported'] for r in records)==7 and len(records)==8
    write_json(root/'preflight.json',dict(complete=True,records=records,parameters_sha256=sha256(parameters)))
    hashes=dict(previous['hashes'])
    for path in [baseline/name for name in ['lock.json','report.json','audit.json','pipeline_exit.json']]+[parameters,root/'preflight.json']:
        hashes[str(path)]=sha256(path)
    for folder in [baseline/'cases',root/'code']:
        for path in folder.rglob('*'):
            if path.is_file() and path.suffix in ['.py','.md','.json','.npz','.pt']:hashes[str(path)]=sha256(path)
    for name in ['anchored_geometry.py','anchored_tail.py','articulated_output.py','calibrated_connection_objective.py']:
        old={h for p,h in previous['hashes'].items() if Path(p).name==name}
        assert old=={sha256(root/'code/src/fastglycan'/name)}
    write_json(root/'lock.json',dict(source=previous['source'],baseline=str(baseline),calibration=previous['calibration'],
        reference_templates=str(parameters),hashes=hashes,reference_contract='calibrated_c4_ideal_reference_v1',
        arms=['native_ref','ideal_ref'],planned=32,supported=28,reused_controls=14,newly_computed_solves=14,
        seeds=[12345,54321],workers=2,timeout_seconds=900,device='cpu',dtype='float64',joint_iterations=180,
        scope='whole CCD ideal interior output templates only; native termini, input and scoring topology unchanged'))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ['root','baseline','parameters']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();prepare_ideal_reference_trial(a.root.resolve(),a.baseline.resolve(),a.parameters.resolve())
