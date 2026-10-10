"""Re-forward every fixed checkpoint and independently check residual metrics."""
import argparse
import json
from pathlib import Path
import time

import numpy as np
import torch

from fastglycan.anchor_training import load_anchor_boundaries
from fastglycan.models.anchored_pair_recovery import ReferenceAnchoredPairRecovery
from fastglycan.pair_recovery_data import PairRecoveryData
from fastglycan.stage_pair_data import StagePairData
from fastglycan.stage_fullbatch import parameter_digest
from fastglycan.paired_teacher_protocol import sha256, write_json
from run_recycle_lora import LoRARuntime
from verify_stage_pair_recovery import NumpyMoments


def verify_anchor_training(root, seed):
    begin=time.monotonic();lock=json.loads((root/'training_lock.json').read_text())
    for name,digest in lock['code'].items(): assert sha256(root/'code'/name)==digest,name
    assert sha256(root/'protocol.md')==lock['protocol_sha256']
    folder=root/'runs/anchor'/str(seed);report=json.loads((folder/'report.json').read_text())
    assert report['complete'] and report['gradient_passes']==128
    assert report['training_lock_sha256']==sha256(root/'training_lock.json')
    assert report['training_counts']==dict(forwards=65664,backwards=65664,gradient_passes=128,
        reference_forwards=3456,reference_backwards=3456)
    assert report['native_counts']==dict(c4=0,input_embedder=0,recycle=0,s1=7296,updates=0)
    assert report['evaluation_reference_forwards']==144 and report['isolation_reference_forwards']==2
    assert sha256(folder/'history.jsonl')==report['history_sha256']
    history=[json.loads(row) for row in (folder/'history.jsonl').read_text().splitlines()]
    gradients=[r for r in history if r['kind']=='gradient'];updates=[r for r in history if r['kind']=='update']
    assert [r['gradient_pass'] for r in gradients]==list(range(1,129))
    assert len(updates)==report['optimizer_calls']==128 and sum(r['calls'] for r in updates)==128
    assert sum(int(r['changed']) for r in updates)==report['changed_updates']
    for row in gradients:
        assert {r['site'] for r in row['sites']}==set(lock['train_sites'])
        for key in ('raw','common','centered'):
            assert np.isclose(row[key],np.mean([r[key] for r in row['sites']]),rtol=1e-12,atol=1e-12)
        assert np.isclose(row['raw'],row['common']+row['centered'],rtol=1e-10,atol=1e-10)
    rt=LoRARuntime(Path(lock['source']),str(folder/'verification_work'));b=rt.base
    data=PairRecoveryData(lock['build_root'],lock['cache_manifest_sha256'])
    stages=StagePairData(lock['stage_root'],lock['stage_manifest_sha256'])
    boundaries=load_anchor_boundaries(lock,'cuda')
    model=ReferenceAnchoredPairRecovery(list(rt.model.pairformer_stack.blocks[-2:]),seed).cuda().eval().requires_grad_(False)
    checks,objectives=[],[];forwards=0;reference_forwards=0
    with torch.no_grad():
        for step in lock['checkpoints']:
            ev=json.loads((folder/f'evaluation_{step}.json').read_text())
            assert ev['complete'] and ev['gradient_passes']==step
            assert sha256(folder/ev['checkpoint'])==ev['sha256']
            checkpoint=torch.load(folder/ev['checkpoint'],map_location='cpu',weights_only=False)
            assert checkpoint['training_lock_sha256']==sha256(root/'training_lock.json')
            model.load_state_dict(checkpoint['state_dict'],strict=True)
            digest=parameter_digest(model.parameters());train_raw=[]
            for record in ev['latent']:
                site=b.sites[record['site']];pi,pos=site['parent_index'],site['position_zero_based']
                old=b.aa.index(site['original_aa']);ref=rt.prefixes[pi][0][1]
                anchor=model.prepare_reference(b.references[pi],boundaries[pi],ref,pos,old)
                reference_forwards+=1
                moments=NumpyMoments();residual={};errors=[]
                for aa in site['candidates']:
                    label=b.label(pi,pos,aa);base,target=data.base(label),data.target(label)
                    boundary=stages.load(label,training=False)[0]
                    result=model(base,boundary,ref,pos,old,b.aa.index(aa),anchor=anchor)
                    assert result[0] is base[0] and result[1] is base[1]
                    forwards+=1
                    if step==0:assert torch.equal(result[2],base[2])
                    moments.add(result[2]-base[2],target-base[2]);residual[aa]=(result[2]-base[2]).cpu()
                    if site['role_n15']=='train':
                        error=result[2].cpu().numpy().astype(np.float64)-target.cpu().numpy().astype(np.float64)
                        errors.append(float(np.mean(error**2))/lock['site_scale_squared'][record['site']])
                moments.check(record['moments'])
                if errors:train_raw.append(float(np.mean(errors)))
                if step==128:
                    mismatch=NumpyMoments()
                    for i,aa in enumerate(site['candidates']):
                        label=b.label(pi,pos,aa);base,target=data.base(label),data.target(label)
                        z=base[2]+residual[site['candidates'][(i+1)%19]].cuda()
                        mismatch.add(z-base[2],target-base[2])
                    mismatch.check(record['mismatch'])
                checks.append(dict(step=step,site=record['site']))
            objective=float(np.mean(train_raw))
            matches=[r for r in gradients if r['parameter_sha256']==digest]
            for row in matches:assert np.isclose(objective,row['raw'],rtol=2e-8,atol=1e-10)
            objectives.append(dict(step=step,objective=objective,matched_gradient_records=len(matches),parameter_sha256=digest))
            for prediction in ev['predictions']:assert sha256(folder/prediction['path'])==prediction['sha256']
    rt.finish()
    assert b.counts==dict(c4=0,input_embedder=0,recycle=0,s1=0,updates=0)
    assert forwards==2736 and reference_forwards==144 and len(checks)==144
    write_json(folder/'tensor_verification.json',dict(complete=True,checks=checks,objectives=objectives,
        feature_forwards=forwards,reference_forwards=reference_forwards,counts=b.counts,
        seconds=time.monotonic()-begin,method='independent NumPy FP64 and full checkpoint re-forward',
        verifier_sha256=sha256(Path(__file__))))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--seed',type=int,required=True);args=parser.parse_args()
    verify_anchor_training(args.root,args.seed)
