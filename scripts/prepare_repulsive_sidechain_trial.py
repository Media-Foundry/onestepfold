#!/usr/bin/env python3
"""Lock a single coupled objective against frozen whole-ideal and pure-fit assets."""
import argparse
import json
from pathlib import Path

from fastglycan.paired_teacher_protocol import sha256,write_json


def prepare_repulsive_sidechain_trial(root,baseline,pure):
    assert not (root/'lock.json').exists()
    previous=json.loads((pure/'lock.json').read_text());audit=json.loads((pure/'audit.json').read_text())
    assert previous['contract']=='fixed_backbone_sidechain_fit_v1' and previous['baseline']==str(baseline)
    assert audit['verified']==14 and audit['report_sha256']==sha256(pure/'report.json')
    assert json.loads((pure/'pipeline_exit.json').read_text())['returncode']==0
    hashes=dict(previous['hashes'])
    for path,h in hashes.items():assert sha256(Path(path))==h
    for folder in [pure/'cases',root/'code']:
        for path in folder.rglob('*'):
            if path.is_file() and path.suffix in ['.py','.md','.json','.npz','.pt']:hashes[str(path)]=sha256(path)
    for name in ['lock.json','report.json','audit.json','pipeline_exit.json']:
        path=pure/name;hashes[str(path)]=sha256(path)
    for name in ['anchored_geometry.py','articulated_output.py','articulated_reference.py','anchored_tail.py']:
        assert {h for p,h in previous['hashes'].items() if Path(p).name==name}=={sha256(root/'code/src/fastglycan'/name)}
    write_json(root/'lock.json',dict(baseline=str(baseline),pure_comparison=str(pure),source=previous['source'],hashes=hashes,
        contract='fixed_backbone_sidechain_repulsion_v1',planned=16,supported=14,seeds=[12345,54321],workers=2,
        max_iter=60,max_eval=90,timeout_seconds=900,device='cpu',dtype='float64',screen=previous['screen'],
        collision_weight=1.,pair_support='rotation-separated endpoints excluding axis; union across legal sidechain angles'))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ['root','baseline','pure']:p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();prepare_repulsive_sidechain_trial(a.root,a.baseline,a.pure)
