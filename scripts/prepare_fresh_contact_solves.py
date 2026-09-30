#!/usr/bin/env python3
"""Lock two freshly solved arms, preserving the previously frozen method."""
import argparse
import json
from pathlib import Path

import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.articulated_output import ArticulatedOutput
from fastglycan.anchored_geometry import PoseVariables
from fastglycan.hybrid_geometry import GeometryTopology
from fastglycan.ideal_output_reference import ideal_output_reference
from fastglycan.calibrated_connection_objective import CalibratedConnectionObjective
from fastglycan.raw_contact_objective import RawContactObjective
from run_projection_joint_start import buffer_digest


def prepare_fresh_contact_solves(root, predictions, method):
    torch.set_num_threads(1)
    assert not (root/'lock.json').exists()
    old=json.loads((method/'lock.json').read_text())
    assert old['objective_contract']=='calibrated_c4_raw_contact_v1'
    runtime=json.loads((predictions/'runtime_lock.json').read_text())
    accepted=json.loads((predictions/'raw_acceptance.json').read_text())
    assert accepted['complete'] and len(accepted['predictions'])==16
    assert accepted['runtime_lock_sha256']==sha256(predictions/'runtime_lock.json')
    assert runtime['seeds']==[400009,400031]
    assert json.loads((predictions/'pipeline_exit.json').read_text())['returncodes']==[0,0]
    assert json.loads((predictions/'resolved_runtime_audit.json').read_text())['verified']
    for path,digest in {**runtime['source_hashes'],**runtime['input_hashes']}.items():assert sha256(Path(path))==digest
    for name in ['anchored_geometry.py','anchored_tail.py','articulated_output.py',
        'articulated_reference.py','calibrated_connection_objective.py','ideal_output_reference.py',
        'raw_contact_objective.py','hybrid_geometry.py','geometry_repair.py']:
        actual=root/'code/src/fastglycan'/name
        assert sha256(actual)==sha256(method/'code/src/fastglycan'/name)
    source=Path(runtime['source']);rows=json.loads((source/'selection.json').read_text());assert len(rows)==8
    hashes=dict(runtime['input_hashes'])
    for name in ['calibration','reference_templates']:
        path=Path(old[name]);assert sha256(path)==old['hashes'][str(path)];hashes[str(path)]=sha256(path)
    for name in ['runtime_lock.json','raw_acceptance.json','pipeline_exit.json','resolved_runtime_audit.json']:
        hashes[str(predictions/name)]=sha256(predictions/name)
    hashes.update({str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.md']})
    templates=json.loads(Path(old['reference_templates']).read_text())['records']
    calibration=json.loads(Path(old['calibration']).read_text());checks=[]
    for item in rows:
        packet=source/'chemistry'/item['group_id'];mapping=dict(np.load(packet/'mapping.npz'))
        assert mapping['mask'].all()
        atoms=torch.load(packet/'native.pt',map_location='cpu',weights_only=False)['atoms']
        names,residues=mapping['atom_names'],mapping['residue_ids']
        top=GeometryTopology(atoms,mapping['reference'])
        anchors=np.array([[int(np.flatnonzero((residues==i)&(names==n))[0]) for n in ['N','CA','C','O']]
            for i in range(1,len(item['sequence'])+1)])
        reference,_=ideal_output_reference(mapping['reference'],names,residues,item['sequence'],
            json.loads((packet/'variants.json').read_text()),templates)
        for seed in runtime['seeds']:
            path=source/'data'/item['group_id']/f'native_{seed}.npy'
            entry=next(x for x in accepted['predictions'] if x['group_id']==item['group_id'] and x['seed']==seed)
            assert sha256(path)==entry['sha256'];hashes[str(path)]=sha256(path)
            raw=torch.tensor(np.load(path).astype(np.float64))
            adapter=ArticulatedOutput(reference,names,residues,item['sequence'],json.loads((packet/'variants.json').read_text())).double()
            left,right=PoseVariables(adapter,raw),PoseVariables(adapter,raw)
            assert torch.equal(left(),right()) and buffer_digest(left)==buffer_digest(right)
            args=(raw,anchors,item['sequence'],top.pairs,top.radii)
            base=CalibratedConnectionObjective(*args,calibration)
            candidate=RawContactObjective(*args,calibration,residues)
            cb=dict(candidate.named_buffers())
            assert all(torch.equal(value,cb[name]) for name,value in base.named_buffers())
            assert float(candidate.contacts(raw))==0
            checks.append(dict(group_id=item['group_id'],seed=seed,chart_sha256=buffer_digest(left),
                base_objective_sha256=buffer_digest(base),pairs=len(candidate.contacts.contact_pairs),
                exact_start=True,raw_sha256=sha256(path)))
    write_json(root/'preflight.json',dict(verified=16,checks=checks))
    hashes[str(root/'preflight.json')]=sha256(root/'preflight.json')
    write_json(root/'lock.json',dict(source=str(source),baseline=None,calibration=old['calibration'],
        reference_templates=old['reference_templates'],hashes=hashes,
        objective_contract='calibrated_c4_raw_contact_v1',confirmation_contract='fresh_contact_v1',
        prediction_contract='c4_s1_confirmation_v1',arms=['zero','contact'],seeds=runtime['seeds'],
        planned=32,supported=32,workers=2,timeout_seconds=900,device='cpu',dtype='float64',
        joint_iterations=180,scope='fresh8x2; both arms new ZERO-start solves; all method parameters frozen'))
    print('Locked32 new solves,16 exact paired starts',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ['root','predictions','method']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();prepare_fresh_contact_solves(a.root,a.predictions,a.method)
