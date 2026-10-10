"""Independent CPU validation of the native gate and finite fitting ledger."""
from collections import Counter
import json
from pathlib import Path

import torch

from fastglycan.native_parallel_audit import assert_tree_equal
from fastglycan.pair_placement import placement_lock
from fastglycan.paired_teacher_protocol import sha256, write_json


def verify_parallel_gate(root):
    root=Path(root);placement_lock(root)
    result=json.loads((root/'parallel_gate.json').read_text())
    assert result['complete'] and result['bitwise_steps']==[1,2]
    reports=[json.loads((root/f'parallel_gate/rank_{rank}/report.json').read_text()) for rank in range(6)]
    assert all(r['complete'] and r['lock_sha256']==sha256(root/'training_lock.json') for r in reports)
    total=Counter()
    for r in reports:
        total.update(r['counts'])
        assert r['native_counts']==dict(c4=0,input_embedder=0,recycle=0,s1=0,updates=0)
    assert dict(total)==dict(forwards=2052,backwards=2052,reference_forwards=108,reference_backwards=108)
    for name,digest in result['snapshots'].items():assert sha256(root/'parallel_gate'/name)==digest
    for step in (1,2):
        values=[torch.load(root/f'parallel_gate/{method}_{step}.pt',map_location='cpu',weights_only=True) for method in ('serial','parallel')]
        assert_tree_equal(*values)
    report=dict(complete=True,bitwise_steps=[1,2],counts=dict(total),lock_sha256=sha256(root/'training_lock.json'))
    write_json(root/'parallel_gate_verification.json',report)
    return report


def verify_training_ledger(root):
    root=Path(root);lock=placement_lock(root);results=[]
    for arm,seed in lock['run_order']:
        folder=root/'runs'/arm/str(seed)
        reports=[json.loads((folder/f'rank_{rank}/report.json').read_text()) for rank in range(6)]
        assert all(r['complete'] and r['steps']==128 and r['checkpoints']==[0,32,128] for r in reports)
        assert len({r['final_sha256'] for r in reports})==1
        total=Counter();native=Counter()
        for r in reports:total.update(r['counts']);native.update(r['native_counts'])
        assert dict(total)==dict(forwards=65664,backwards=65664,reference_forwards=3456,
            reference_backwards=3456,evaluation_forwards=2736,evaluation_reference_forwards=144,isolation_forwards=144)
        assert dict(native)==dict(c4=0,input_embedder=0,recycle=0,s1=7296,updates=0)
        history=[json.loads(line) for line in (folder/'history.jsonl').read_text().splitlines()]
        assert [r['step'] for r in history]==list(range(1,129))
        for row in history:
            assert [s['site'] for s in row['summary']['sites']]==lock['train_sites']
            assert row['summary']['counts']['forwards']==513 and row['summary']['counts']['reference_forwards']==27
        for step in (0,32,128):
            ev=json.loads((folder/f'evaluation_{step}.json').read_text())
            assert ev['complete'] and ev['step']==step and len(ev['latent'])==48
            assert sha256(folder/ev['checkpoint'])==ev['sha256']
            cp=torch.load(folder/ev['checkpoint'],map_location='cpu',weights_only=True)
            assert cp['step']==step and cp['training_lock_sha256']==sha256(root/'training_lock.json')
            assert sum(t.numel() for t in cp['state_dict'].values())==1315332
            assert all(torch.isfinite(v).all() for v in cp['state_dict'].values())
            assert not any('continuation' in key for key in cp['state_dict'])
            for row in ev['predictions']:assert sha256(folder/row['path'])==row['sha256']
            summary=json.loads((folder/f'summary_{step}.json').read_text())
            assert summary['complete'] and summary['evaluation_sha256']==sha256(folder/f'evaluation_{step}.json')
            if arm=='late':
                original=Path(lock['previous_root'])/'runs/anchor'/str(seed)/'checkpoints'/f'{step}.pt'
                old=torch.load(original,map_location='cpu',weights_only=False)
                assert_tree_equal(cp['state_dict'],old['state_dict']);assert_tree_equal(cp['optimizer'],old['optimizer'])
        results.append(dict(arm=arm,seed=seed,complete=True,counts=dict(total),native_counts=dict(native),
                            history_sha256=sha256(folder/'history.jsonl')))
    result=dict(complete=True,runs=results,native_checkpoint_replay_pending=True,
                lock_sha256=sha256(root/'training_lock.json'))
    write_json(root/'ledger_verification.json',result)
    return result
