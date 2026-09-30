#!/usr/bin/env python3
"""Freeze a single raw-contact objective intervention and saved zero controls."""
import argparse
import json
from pathlib import Path

import numpy as np
import torch

from fastglycan.anchored_geometry import PoseVariables
from fastglycan.articulated_output import ArticulatedOutput
from fastglycan.hybrid_geometry import GeometryTopology
from fastglycan.raw_contact_objective import RawContactPreservation
from fastglycan.paired_teacher_protocol import sha256,write_json
from run_projection_joint_start import buffer_digest


def prepare_raw_contact_trial(root,baseline):
    torch.set_num_threads(1)
    assert not (root/'lock.json').exists()
    old=json.loads((baseline/'lock.json').read_text());audit=json.loads((baseline/'audit.json').read_text())
    assert old['reference_contract']=='calibrated_c4_ideal_reference_v1'
    assert audit['verified']==28 and audit['paired']==14 and audit['report_sha256']==sha256(baseline/'report.json')
    assert json.loads((baseline/'pipeline_exit.json').read_text())['returncode']==0
    hashes=dict(old['hashes'])
    for p,h in hashes.items():assert sha256(Path(p))==h
    for folder in [baseline/'cases',root/'code']:
        for path in folder.rglob('*'):
            if path.is_file() and path.suffix in ['.py','.md','.json','.npz','.pt']:hashes[str(path)]=sha256(path)
    for name in ['lock.json','report.json','audit.json','pipeline_exit.json']:
        hashes[str(baseline/name)]=sha256(baseline/name)
    for name in ['anchored_geometry.py','anchored_tail.py','articulated_output.py','articulated_reference.py','calibrated_connection_objective.py','ideal_output_reference.py']:
        assert {h for p,h in old['hashes'].items() if Path(p).name==name}=={sha256(root/'code/src/fastglycan'/name)}
    source=Path(old['source']);selection=json.loads((source/'selection.json').read_text());checks=[]
    for i in range(16):
        item=selection[i//2];packet=source/'chemistry'/item['group_id']
        if not json.loads((packet/'report.json').read_text())['passed']:
            checks.append(dict(index=i,supported=False));continue
        folder=baseline/'cases'/f'{2*i+1:02d}';row=json.loads((folder/'report.json').read_text())
        assert row['success'] and row['arm']=='ideal_ref' and row['seed']==[12345,54321][i%2]
        assert sha256(folder/'coordinates.npz')==row['coordinates_sha256']
        data=dict(np.load(folder/'coordinates.npz'));raw=torch.tensor(data['raw'])
        atoms=torch.load(packet/'native.pt',map_location='cpu',weights_only=False)['atoms']
        reference=np.load(packet/'mapping.npz')['reference'];top=GeometryTopology(atoms,reference)
        contacts=RawContactPreservation(raw,data['residue_ids'],top.pairs)
        adapter=ArticulatedOutput(data['output_reference'],data['atom_names'],data['residue_ids'],item['sequence'],json.loads((packet/'variants.json').read_text())).double()
        variables=PoseVariables(adapter,raw);err=float(np.max(np.abs(variables().detach().numpy()-data['start'])))
        assert err<1e-8 and buffer_digest(variables)==row['chart_sha256']
        assert float(contacts(raw))==0 and not contacts.contact_target.requires_grad
        checks.append(dict(index=i,supported=True,start_max_abs=err,pairs=len(contacts.contact_pairs),active_atoms=int((contacts.contact_degree>0).sum()),weight_sum=float(contacts.contact_weights.sum())))
    assert sum(c['supported'] for c in checks)==14
    write_json(root/'preflight.json',dict(verified=14,cases=checks))
    write_json(root/'lock.json',dict(source=str(source),baseline=str(baseline),calibration=old['calibration'],
        reference_templates=old['reference_templates'],hashes=hashes,objective_contract='calibrated_c4_raw_contact_v1',
        arms=['zero','contact'],seeds=[12345,54321],planned=32,supported=28,workers=2,timeout_seconds=900,
        device='cpu',dtype='float64',joint_iterations=180,weight=1.,delta=1.,raw_distance_min=4.,raw_distance_max_exclusive=15.,min_sequence_separation=5,
        screen='positive paired protein-mean AA and CA; no decrease of zero-severe/strict-chirality/raw-RMS count',
        scope='only add raw-only contact preservation outside rho; same whole-ideal zero chart and chemistry budget'))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ['root','baseline']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();prepare_raw_contact_trial(a.root,a.baseline)
