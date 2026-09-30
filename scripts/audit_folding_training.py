#!/usr/bin/env python3
"""Verify fixed continuation budgets, parameter provenance and training-only curves."""
import argparse
import collections
import json
import math
from pathlib import Path
import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.folding_scale import PARENT_SHA256


def audit_folding_training(root):
    torch.set_num_threads(1)
    lock=json.loads((root/'lock.json').read_text());release=json.loads((root/'release.json').read_text())
    assert release['lock_sha256']==sha256(root/'lock.json')
    assert release['preflight_sha256']==sha256(root/'preflight/report.json')
    for p,d in lock['hashes'].items():assert sha256(Path(p))==d
    starts=[];initial_predictions=[];summary={};checkpoints={}
    for arm in lock['arms']:
        folder=root/arm;r=json.loads((folder/'report.json').read_text())
        assert r['complete'] and r['updates']==2048 and r['exposures']==8192 and not r['validation_read']
        assert r['counts']==dict(pairformer=0,diffusion=8448)
        assert r['lock_sha256']==sha256(root/'lock.json') and r['selected_names']==lock['selected_names']
        assert r['excluded_parameters_unchanged'] is True
        assert sha256(folder/'initial_fingerprints.json')==r['initial_sha256']
        starts.append(json.loads((folder/'initial_fingerprints.json').read_text()))
        history=[json.loads(line) for line in (folder/'history.jsonl').read_text().splitlines()]
        assert len(history)==8192 and sha256(folder/'history.jsonl')==r['history_sha256']
        exposures=collections.Counter()
        for index,(x,y) in enumerate(zip(history,lock['orders'][arm]),1):
            assert x['exposure']==index and all(x[k]==y[k] for k in ['epoch','group_id','seed'])
            exposures[x['group_id']]+=1
            assert set(x['parts'])==set(lock['weights']) and all(math.isfinite(v) for v in x['parts'].values())
            weighted=sum(x['parts'][k]*lock['weights'][k] for k in x['parts'])
            assert abs(weighted-x['loss'])<=1e-5*max(1,abs(weighted))
            if index%4==0:
                u=index//4;lr=1e-5*u/64 if u<=64 else 1e-6+.5*9e-6*(1+math.cos(math.pi*(u-64)/(2048-64)))
                assert x['update']==u and abs(x['lr']-lr)<1e-18
                assert math.isfinite(x['unclipped_accumulated_grad_norm'])
            else:assert 'update' not in x
        assert set(exposures)==set(lock['arms'][arm])
        curves=[]
        for update in lock['probe_updates']:
            folder_probe=folder/f'probe_{update:04d}';probe=json.loads((folder_probe/'report.json').read_text())
            assert probe['role']=='train_probe_only' and probe['update']==update and len(probe['records'])==64
            assert {(x['group_id'],x['seed']) for x in probe['records']}=={(g,s) for g in lock['probe_groups'] for s in lock['training_seeds']}
            hashes={}
            for item in probe['records']:
                name=f'{item["group_id"]}_{item["seed"]}.npy';assert sha256(folder_probe/name)==item['sha256']
                x=np.load(folder_probe/name);assert np.isfinite(x).all() and x.ndim==2 and x.shape[1]==3
                hashes[name]=item['sha256']
            if update==0:initial_predictions.append(hashes)
            curves.append({k:v for k,v in probe.items() if k!='records'})
        p=folder/'update_2048.pt';assert sha256(p)==r['terminal_sha256']
        state=torch.load(p,map_location='cpu',weights_only=False)
        assert state['schema']=='folding_scale_continuation_v1' and state['arm']==arm
        assert state['parent_sha256']==PARENT_SHA256 and state['lock_sha256']==sha256(root/'lock.json')
        assert state['update']==2048 and state['exposures']==8192
        assert list(state['trained'])==lock['selected_names'] and len(state['optimizer']['state'])==288
        assert all(torch.isfinite(v).all() for v in state['trained'].values())
        assert all(int(v['step'])==2048 for v in state['optimizer']['state'].values())
        assert sum(v.numel() for v in state['trained'].values())==69777841
        group,=state['optimizer']['param_groups']
        assert group['betas']==(.9,.999) and group['eps']==1e-8 and group['weight_decay']==0 and group['lr']==1e-6
        checkpoints[arm]=dict(path=str(p),sha256=sha256(p));del state
        summary[arm]=dict(seconds=r['seconds'],peak_gpu_bytes=r['peak_gpu_bytes'],train_proteins=len(exposures),
            exposure_min=min(exposures.values()),exposure_max=max(exposures.values()),
            mean_loss_first512_exposures=float(np.mean([x['loss'] for x in history[:512]])),
            mean_loss_last512_exposures=float(np.mean([x['loss'] for x in history[-512:]])),
            clipped_updates=sum(x.get('unclipped_accumulated_grad_norm',0)>1 for x in history),curves=curves)
    assert starts[0]==starts[1]
    # Same initial input/weights must replay identically on the matched H100 backend.
    assert initial_predictions[0]==initial_predictions[1]
    write_json(root/'training_audit.json',dict(complete=True,lock_sha256=sha256(root/'lock.json'),
        checkpoints=checkpoints,summary=summary,identical_start=True,initial_probe_replay_exact=True,
        same_update_exposure_budget=True,different_data_orders=True,validation_not_used=True,
        script_sha256=sha256(Path(__file__)),scope='execution and TRAIN probes; no held-out quality conclusion'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    audit_folding_training(p.parse_args().root.resolve())
