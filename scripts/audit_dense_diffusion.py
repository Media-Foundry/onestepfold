#!/usr/bin/env python3
"""Audit dense native checkpoint schema, scope, optimizer and identical exposure budgets."""
import argparse
import json
import math
from pathlib import Path
import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256, write_json


def audit_dense_diffusion(root):
    lock=json.loads((root/'lock.json').read_text());execution=json.loads((root/'execution.json').read_text())
    assert execution['complete'] and all(w['exit_code']==0 for w in execution['workers'])
    for p,d in lock['hashes'].items():assert sha256(Path(p))==d
    initials=[];checkpoints={};summary={}
    for arm in lock['arms']:
        folder=root/arm;r=json.loads((folder/'report.json').read_text())
        assert r['complete'] and r['updates']==512 and r['exposures']==2048 and not r['validation_read']
        assert r['counts']==dict(pairformer=0,diffusion=2048) and r['lock_sha256']==sha256(root/'lock.json')
        assert r['selected_names']==lock['preflights'][arm]['selected_names']
        assert r['excluded_parameters_unchanged']==1613-r['selected_tensors']
        assert sha256(folder/'initial_fingerprints.json')==r['initial_sha256']
        initials.append(json.loads((folder/'initial_fingerprints.json').read_text()));assert len(initials[-1])==1613
        rows=[json.loads(s) for s in (folder/'history.jsonl').read_text().splitlines()]
        assert len(rows)==2048 and sha256(folder/'history.jsonl')==r['history_sha256']
        for i,(x,y) in enumerate(zip(rows,lock['order']),1):
            assert x['exposure']==i and all(x[k]==y[k] for k in ['epoch','group_id','seed'])
            assert set(x['parts'])==set(lock['weights']) and all(math.isfinite(v) for v in x['parts'].values())
            weighted=sum(x['parts'][k]*lock['weights'][k] for k in x['parts'])
            assert abs(weighted-x['loss'])<=1e-5*max(1,abs(weighted))
            if i%4==0:
                u=i//4;lr=1e-5*u/32 if u<=32 else 1e-6+.5*9e-6*(1+math.cos(math.pi*(u-32)/480))
                assert x['update']==u and abs(x['lr']-lr)<1e-18 and math.isfinite(x['unclipped_accumulated_grad_norm'])
            else:assert 'update' not in x
        p=folder/'update_0512.pt';assert sha256(p)==r['terminal_sha256']
        state=torch.load(p,map_location='cpu',weights_only=False)
        assert state['schema']=='native_dense_diffusion_v1' and state['arm']==arm
        assert state['update']==512 and state['exposures']==2048 and state['lock_sha256']==sha256(root/'lock.json')
        assert list(state['trained'])==r['selected_names'] and len(state['optimizer']['state'])==r['selected_tensors']
        assert all(torch.isfinite(v).all() for v in state['trained'].values())
        assert all(int(v['step'])==512 for v in state['optimizer']['state'].values())
        assert sum(v.numel() for v in state['trained'].values())==r['trainable_parameters']
        groups=state['optimizer']['param_groups'];assert len(groups)==1
        assert groups[0]['betas']==(.9,.999) and groups[0]['eps']==1e-8 and groups[0]['weight_decay']==0
        assert abs(groups[0]['lr']-1e-6)<1e-18
        checkpoints[arm]=dict(path=str(p),sha256=sha256(p));del state
        epochs=[]
        for epoch in range(1,17):
            part=rows[(epoch-1)*128:epoch*128]
            epochs.append(dict(epoch=epoch,mean_loss=float(np.mean([x['loss'] for x in part])),
                parts={k:float(np.mean([x['parts'][k] for x in part])) for k in lock['weights']}))
        summary[arm]=dict(seconds=r['seconds'],peak_gpu_bytes=r['peak_gpu_bytes'],epochs=epochs,
            clipped_updates=sum(x.get('unclipped_accumulated_grad_norm',0)>1 for x in rows))
    assert initials[0]==initials[1]
    write_json(root/'training_audit.json',dict(complete=True,lock_sha256=sha256(root/'lock.json'),
        checkpoints=checkpoints,summary=summary,identical_public_initialization=True,identical_order=True,
        terminal_only=True,validation_not_used=True,script_sha256=sha256(Path(__file__))))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args()
    torch.set_num_threads(1);audit_dense_diffusion(a.root)
