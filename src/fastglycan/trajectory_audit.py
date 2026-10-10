"""Frozen Mini trajectory replay, legal transport baseline and separate labels."""
import json
from pathlib import Path
import random
import time

import numpy as np
import torch

from fastglycan.models.compensated_recycle import initialize_cached_recycle, native_recycle_step
from fastglycan.models.prefix_recycle import capture_rng_state, restore_rng_state
from fastglycan.models.recycle_trajectory import (
    capture_recycle_trajectory, finish_transferred_candidate, same_rng,
)
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.response_moments import ResponseMoments


def read_trajectory_lock(root):
    root=Path(root);lock=json.loads((root/'trajectory_lock.json').read_text())
    assert lock['arms']==['exact','cold_c2','wt_progress'] and lock['updates']==0
    assert lock['shards']==2 and lock['rng_seed']==281001
    assert sha256(root/'protocol.md')==lock['protocol_sha256']
    for name,digest in lock['code'].items():
        assert sha256(root/'code'/name)==digest,name
    assert sha256(Path(lock['source'])/'lora_lock.json')==lock['source_lock_sha256']
    return lock


def _save_trajectory_tensor(root, relative, value):
    path=root/relative;path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():raise FileExistsError(path)
    torch.save(value,path)
    return dict(path=relative,sha256=sha256(path),bytes=path.stat().st_size)


def run_trajectory_audit(root, shard, runtime_factory):
    root=Path(root);lock=read_trajectory_lock(root);begin=time.monotonic()
    assert 0<=shard<lock['shards']
    runtime=runtime_factory(Path(lock['source']),str(root/f'work_{shard}'))
    base=runtime.base;model=runtime.model
    assert len(base.plan['parents'])==24 and len(base.plan['sites'])==48
    assert sha256(base.root/'plan.json')==lock['plan_sha256']
    coordinates=root/'coordinates';coordinates.mkdir(exist_ok=True)
    report=dict(complete=False,shard=shard,phase='reference_replay',rows=[],sites=[],
                references=[],labels=[],candidate_errors=[],latent=[],replay_checks=0,
                candidate_isolation_checks=[])
    references={};isolation_parents=set()
    with torch.no_grad():
        for parent in base.plan['parents']:
            pi=parent['parent_index']
            if pi%lock['shards']!=shard:continue
            random.seed(lock['rng_seed']+pi);np.random.seed(lock['rng_seed']+pi)
            torch.manual_seed(lock['rng_seed']+pi);torch.cuda.manual_seed_all(lock['rng_seed']+pi)
            initial_rng=capture_rng_state()
            item=base.item(pi);reference=base.references[pi]
            initialization=initialize_cached_recycle(model,item['features'],reference[0])
            states,rngs=capture_recycle_trajectory(model,item['features'],initialization,initial_rng)
            assert all(torch.equal(a,b) for a,b in zip(states[4],reference[1:])),(pi,'WT C4')
            old3,_=runtime.prefixes[pi]
            assert all(torch.equal(a,b) for a,b in zip(states[3],old3)),(pi,'archived WT3')
            # Interleaving must not affect a true split continuation.
            torch.rand(17,device='cuda')
            state=states[1]
            for cycle in (2,3,4):
                state=native_recycle_step(model,item['features'],initialization,state,rng=rngs[cycle-1])
                assert all(torch.equal(a,b) for a,b in zip(state,states[cycle]))
            assert same_rng(capture_rng_state(),rngs[4])
            predicted3,final=finish_transferred_candidate(model,item['features'],initialization,
                states[1],states[1],states[3],rngs[3])
            assert all(torch.equal(a,b) for a,b in zip(predicted3,states[3]))
            assert all(torch.equal(a,b) for a,b in zip(final,reference[1:]))
            for noise in (0,1):
                assert torch.equal(base.decode(item,(reference[0],*final),noise),item['teacher'][noise])
            record=_save_trajectory_tensor(root,f'references/{pi}.pt',dict(
                parent=pi,reference1=tuple(x.cpu() for x in states[1]),
                reference3=tuple(x.cpu() for x in states[3]),rng3=rngs[3],initial_rng=initial_rng))
            report['references'].append(dict(parent=pi,**record))
            references[pi]=(states,rngs,initial_rng)
            report['seconds']=time.monotonic()-begin;write_json(root/f'shard_{shard}.json',report)

        report['phase']='candidate_replay'
        for site in base.plan['sites']:
            pi=site['parent_index'];position=site['position_zero_based']
            if pi not in references:continue
            wt,wt_rng,initial_rng=references[pi]
            before={field:ResponseMoments() for field in ('s','z')}
            after={arm:{field:ResponseMoments() for field in ('s','z')}
                   for arm in ('cold_c2','wt_progress')}
            isolation=None
            for aa in site['candidates']:
                item=base.item(pi,position,aa);label=item['label']
                archived_path=base.store.path(pi,label,'conditioning.pt')
                archive=torch.load(archived_path,map_location='cpu',weights_only=False)['conditioning']
                inputs=runtime.candidate_input(item)
                assert torch.equal(inputs.cpu(),archive[0])
                initialization=initialize_cached_recycle(model,item['features'],inputs)
                states,rngs=capture_recycle_trajectory(model,item['features'],initialization,initial_rng)
                assert all(torch.equal(a.cpu(),b) for a,b in zip(states[4],archive[1:])),(label,'C4')
                assert same_rng(rngs[3],wt_rng[3]),(label,'candidate/WT boundary RNG differs')
                # Teacher state and RNG are used only by this independent replay check.
                restored=native_recycle_step(model,item['features'],initialization,states[3],rng=rngs[3])
                assert all(torch.equal(a,b) for a,b in zip(restored,states[4])),(label,'3+1')
                assert same_rng(capture_rng_state(),rngs[4])
                report['replay_checks']+=1
                # Prediction inputs exclude states2/3/4 and target RNG.
                predicted3,final=finish_transferred_candidate(model,item['features'],initialization,
                    states[1],wt[1],wt[3],wt_rng[3])
                if pi not in isolation_parents and isolation is None:
                    isolation=(item,initialization,states[1],predicted3,final)
                observed={}
                for field,p,t,w,p4,t4 in zip(('s','z'),predicted3,states[3],wt[3],final,states[4]):
                    before[field].add(p-w,t-w)
                    e3=float((p.double()-t.double()).square().mean())
                    e4=float((p4.double()-t4.double()).square().mean())
                    observed[field]=dict(before_mse=e3,after_mse=e4,
                        finite_error_norm_gain=(e4/e3)**.5 if e3>1e-24 else None,
                        tiny_denominator=e3<=1e-24)
                report['candidate_errors'].append(dict(label=label,site=site['site_key'],
                    parent=pi,role=site['role_n15'],states=observed))
                for arm,state in [('exact',states[4]),('cold_c2',states[2]),('wt_progress',final)]:
                    xyz=np.stack([base.decode(item,(inputs,*state),noise).cpu().numpy() for noise in (0,1)])
                    assert np.isfinite(xyz).all()
                    if arm=='exact':assert np.array_equal(xyz,item['teacher'].cpu().numpy()),label
                    else:
                        for field,p,t,w in zip(('s','z'),state,states[4],wt[4]):
                            after[arm][field].add(p-w,t-w)
                    path=coordinates/f'{arm}_{label}.npz';assert not path.exists()
                    np.savez_compressed(path,coordinates=xyz)
                    report['rows'].append(dict(arm=arm,label=label,path=str(path.relative_to(root)),sha256=sha256(path)))
                inp=_save_trajectory_tensor(root,f'candidate_inputs/{label}.pt',dict(
                    label=label,role=site['role_n15'],candidate1=tuple(x.cpu() for x in states[1])))
                target=_save_trajectory_tensor(root,f'target_labels/{label}.pt',dict(
                    label=label,role=site['role_n15'],target3=tuple(x.cpu() for x in states[3]),
                    verified_target4_sha256=sha256(archived_path)))
                report['labels'].append(dict(label=label,input=inp,target=target))
                del archive,states,rngs,restored,final,predicted3,initialization
            if isolation is not None:
                # Repeat the first candidate after the other18 candidates/decodes.
                first_item,first_init,first_state,expected3,expected4=isolation
                repeated3,repeated4=finish_transferred_candidate(model,first_item['features'],
                    first_init,first_state,wt[1],wt[3],wt_rng[3])
                assert all(torch.equal(a,b) for a,b in zip(repeated3,expected3))
                assert all(torch.equal(a,b) for a,b in zip(repeated4,expected4))
                record=next(r for r in report['rows'] if r['arm']=='wt_progress'
                            and r['label']==first_item['label'])
                with np.load(root/record['path']) as stored:
                    for noise in (0,1):
                        replay=base.decode(first_item,(first_init.inputs,*repeated4),noise)
                        assert np.array_equal(replay.cpu().numpy(),stored['coordinates'][noise])
                isolation_parents.add(pi)
                report['candidate_isolation_checks'].append(first_item['label'])
                del isolation,first_init,first_state,expected3,expected4,repeated3,repeated4,replay
            report['latent'].append(dict(site=site['site_key'],pdb=site['pdb_id'],parent=pi,
                role=site['role_n15'],before={f:m.result() for f,m in before.items()},
                after={arm:{f:m.result() for f,m in fields.items()} for arm,fields in after.items()}))
            report['sites'].append(site['site_key']);report['seconds']=time.monotonic()-begin
            write_json(root/f'shard_{shard}.json',report)
            print('TRAJECTORY_SITE',shard,site['site_key'],base.counts,flush=True)
        #24parents/48sites split by parent parity,38mutants per parent.
        assert len(report['references'])==12 and len(report['sites'])==24
        assert report['replay_checks']==456 and len(report['rows'])==1368
        assert len(report['candidate_isolation_checks'])==12
        assert base.counts['recycle']==456*6+12*9
        assert base.counts['s1']==456*6+12*4 and base.counts['updates']==0
        for record in report['references']:
            saved=torch.load(root/record['path'],map_location='cpu',weights_only=False)
            current=references[record['parent']][0]
            for cycle in (1,3):
                assert all(torch.equal(a.cpu(),b) for a,b in zip(current[cycle],saved[f'reference{cycle}']))
    runtime.finish();read_trajectory_lock(root)
    report.update(complete=True,phase='complete',seconds=time.monotonic()-begin,
                  counts=base.counts,runtime=base.runtime,peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                  lock_sha256=sha256(root/'trajectory_lock.json'))
    write_json(root/f'shard_{shard}.json',report)
