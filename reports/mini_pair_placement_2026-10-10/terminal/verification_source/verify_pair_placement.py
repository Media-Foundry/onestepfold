"""Rebuild each placement checkpoint and independently recompute residuals."""
import argparse
import json
from pathlib import Path
import time

import numpy as np
import torch

from fastglycan.pair_placement import PlacementBoundaries, placement_lock, placement_model
from fastglycan.pair_recovery_data import PairRecoveryData
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.reference_editor_multiref import editor_state_digest
from fastglycan.stage_pair_data import StagePairData
from run_recycle_lora import LoRARuntime
from verify_stage_pair_recovery import NumpyMoments


def verify_pair_placement(root, arm, seed, output):
    start=time.monotonic();lock=placement_lock(root);folder=root/'runs'/arm/str(seed)
    reports=[json.loads((folder/f'rank_{rank}/report.json').read_text()) for rank in range(6)]
    assert all(r['complete'] and r['steps']==128 for r in reports)
    output.mkdir(parents=True,exist_ok=False)
    rt=LoRARuntime(Path(lock['source']),str(output/'runtime'));b=rt.base
    data=PairRecoveryData(lock['build_root'],lock['cache_manifest_sha256'])
    stages=StagePairData(lock['stage_root'],lock['stage_manifest_sha256'])
    boundaries=PlacementBoundaries(lock['boundary_root'],lock['boundary_manifest_sha256'])
    references={pi:boundaries.reference(pi,arm) for pi in b.references}
    model=placement_model(rt.model,arm,seed).eval().requires_grad_(False)
    native_hash=editor_state_digest(rt.model);checks=[];objectives=[];forwards=0
    with torch.no_grad():
        for step in (0,32,128):
            ev=json.loads((folder/f'evaluation_{step}.json').read_text())
            assert ev['complete'] and ev['step']==step and len(ev['latent'])==48
            assert sha256(folder/ev['checkpoint'])==ev['sha256']
            cp=torch.load(folder/ev['checkpoint'],map_location='cpu',weights_only=True)
            assert cp['training_lock_sha256']==sha256(root/'training_lock.json')
            assert cp['config']==model.config
            model.load_state_dict(cp['state_dict'],strict=True);train_raw=[]
            for record in ev['latent']:
                site=b.sites[record['site']];pi,pos=site['parent_index'],site['position_zero_based']
                old=b.aa.index(site['original_aa']);ref=rt.prefixes[pi][0][1]
                anchor=model.prepare_reference(b.references[pi],references[pi],ref,pos,old)
                moments=NumpyMoments();residual={};errors=[]
                for aa in site['candidates']:
                    label=b.label(pi,pos,aa);base,target=data.base(label),data.target(label)
                    boundary=boundaries.candidate(label) if arm=='early' else stages.load(label,training=False)[0]
                    result=model(base,boundary,ref,pos,old,b.aa.index(aa),anchor=anchor)
                    assert result[0] is base[0] and result[1] is base[1];forwards+=1
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
                write_json(output/'progress.json',dict(complete=False,checks=len(checks),seconds=time.monotonic()-start))
                print('PLACEMENT_VERIFY',arm,seed,step,record['site'],flush=True)
            objectives.append(dict(step=step,raw=float(np.mean(train_raw)),checkpoint_sha256=ev['sha256']))
            for row in ev['predictions']:assert sha256(folder/row['path'])==row['sha256']
    assert forwards==2736 and len(checks)==144
    if arm=='early':model.continuation.check_unchanged()
    assert editor_state_digest(rt.model)==native_hash
    assert b.counts==dict(c4=0,input_embedder=0,recycle=0,s1=0,updates=0)
    rt.finish()
    result=dict(complete=True,arm=arm,seed=seed,checks=checks,objectives=objectives,
        feature_forwards=forwards,reference_forwards=144,counts=b.counts,seconds=time.monotonic()-start,
        method='fresh native model and full checkpoint replay; independent NumPy FP64 residuals',
        training_lock_sha256=sha256(root/'training_lock.json'),verifier_sha256=sha256(Path(__file__)))
    write_json(output/'tensor_verification.json',result)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--arm',choices=['late','early'],required=True);p.add_argument('--seed',type=int,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    verify_pair_placement(a.root,a.arm,a.seed,a.output)
