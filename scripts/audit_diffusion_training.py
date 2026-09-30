#!/usr/bin/env python3
"""Verify fixed-budget training before releasing any held-out evaluation."""
import argparse
import json
import math
from pathlib import Path

import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256, write_json


def audit_diffusion_training(root):
    lock=json.loads((root/'lock.json').read_text());execution=json.loads((root/'execution.json').read_text())
    assert execution['complete'] and all(w['exit_code']==0 for w in execution['workers'])
    for path,digest in lock['hashes'].items():assert sha256(Path(path))==digest
    checkpoints={};histories={};initials=[];summary={}
    for arm in lock['arms']:
        report=json.loads((root/arm/'report.json').read_text())
        assert report['complete'] and report['updates']==512 and report['exposures']==2048
        assert report['counts']==dict(diffusion=2048,pairformer=0) and report['base_parameters_unchanged']==1613
        assert not report['validation_read'] and report['lock_sha256']==sha256(root/'lock.json')
        history=[json.loads(line) for line in (root/arm/'history.jsonl').read_text().splitlines()]
        assert len(history)==2048 and sha256(root/arm/'history.jsonl')==report['history_sha256']
        for i,(record,item) in enumerate(zip(history,lock['order']),1):
            assert record['exposure']==i and all(record[k]==item[k] for k in ['epoch','group_id','seed'])
            assert all(np.isfinite(v) for v in record['parts'].values()) and np.isfinite(record['loss'])
            expected=set(lock['loss_weights'])-({'teacher'} if arm=='gt' else set())
            assert set(record['parts'])==expected
            weighted=sum(record['parts'][k]*lock['loss_weights'][k] for k in record['parts'])
            assert abs(weighted-record['loss'])<=1e-5*max(1,abs(weighted))
            if i%4==0:
                update=i//4;lr=1e-5*update/32 if update<=32 else 1e-6+.5*9e-6*(1+math.cos(math.pi*(update-32)/480))
                assert record['update']==update and abs(record['lr']-lr)<1e-18
                assert np.isfinite(record['unclipped_accumulated_grad_norm'])
            else:assert 'update' not in record
        checkpoint=root/arm/'update_0512.pt';assert sha256(checkpoint)==report['terminal_sha256']
        state=torch.load(checkpoint,map_location='cpu',weights_only=False)
        assert state['update']==512 and state['exposures']==2048 and state['arm']==arm
        assert state['lock_sha256']==sha256(root/'lock.json') and state['rank']==8
        assert len(state['trained'])==56 and len(state['optimizer']['state'])==112
        assert all(int(v['step'])==512 for v in state['optimizer']['state'].values())
        assert all(torch.isfinite(v).all() for p in state['trained'].values() for v in p.values())
        initial=torch.load(root/arm/'initial.pt',map_location='cpu',weights_only=False);initials.append(initial)
        assert all(torch.count_nonzero(v['up'])==0 for v in initial.values())
        assert all(torch.count_nonzero(v['up'])>0 for v in state['trained'].values())
        checkpoints[arm]=dict(path=str(checkpoint),sha256=sha256(checkpoint));histories[arm]=report['history_sha256']
        epochs=[]
        for epoch in range(1,17):
            part=history[(epoch-1)*128:epoch*128]
            epochs.append(dict(epoch=epoch,mean_loss=float(np.mean([r['loss'] for r in part])),
                parts={k:float(np.mean([r['parts'][k] for r in part])) for k in part[0]['parts']},
                gradient_norm_mean=float(np.mean([r['unclipped_accumulated_grad_norm'] for r in part if 'update' in r]))))
        summary[arm]=dict(seconds=report['seconds'],peak_gpu_bytes=report['peak_gpu_bytes'],epochs=epochs)
    assert initials[0].keys()==initials[1].keys()
    assert all(torch.equal(initials[0][n][k],initials[1][n][k]) for n in initials[0] for k in initials[0][n])
    write_json(root/'training_audit.json',dict(complete=True,lock_sha256=sha256(root/'lock.json'),
        checkpoints=checkpoints,histories=histories,identical_initialization=True,summary=summary,
        terminal_only=True,validation_not_used=True,script_sha256=sha256(Path(__file__))))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args()
    torch.set_num_threads(1);audit_diffusion_training(a.root)
