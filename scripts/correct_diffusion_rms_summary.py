#!/usr/bin/env python3
"""Preserve the frozen report and correct only RMSD's worst-tail orientation."""
import argparse
import copy
import json
from pathlib import Path

import numpy as np
from fastglycan.paired_teacher_protocol import sha256, write_json


def correct_diffusion_rms_summary(source,destination,patch):
    old=json.loads(source.read_text());new=copy.deepcopy(old);changes=[]
    for role,summary in old['summary'].items():
        rows=[r for r in old['records'] if r['role']==role];groups=sorted({r['group_id'] for r in rows})
        for model in summary['models']:
            values=np.array([np.mean([r['ca_aligned_rmsd'] for r in rows if r['group_id']==g and r['model']==model]) for g in groups])
            k=max(1,int(np.ceil(.05*len(values))));before=summary['models'][model]['quality_protein_means']['ca_aligned_rmsd']['worst5_mean']
            assert abs(before-np.sort(values)[:k].mean())<1e-12
            after=float(np.sort(values)[-k:].mean());assert after>=before
            new['summary'][role]['models'][model]['quality_protein_means']['ca_aligned_rmsd']['worst5_mean']=after
            changes.append(dict(role=role,model=model,before=before,after=after,proteins_in_tail=k))
    assert new['records']==old['records'] and new['paired']==old['paired']
    assert len(changes)==8
    write_json(destination,new)
    write_json(patch,dict(source_sha256=sha256(source),corrected_sha256=sha256(destination),changes=changes,
        unchanged='all raw records, all paired contrasts, all means, lDDT tails and chemical diagnostics',
        reason='RMSD lower is better: worst tail is the largest 5%, not the smallest 5%',
        script_sha256=sha256(Path(__file__)),no_new_predictions=True))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--destination',type=Path,required=True);p.add_argument('--patch',type=Path,required=True);a=p.parse_args()
    correct_diffusion_rms_summary(a.source,a.destination,a.patch)
