"""Finite matched placement fits, using the validated ordered site reduction."""
from collections import Counter
import ctypes
from datetime import timedelta
import json
import os
from pathlib import Path
import time
import traceback

import numpy as np
import torch
import torch.distributed as dist

from fastglycan.anchor_training import AnchoredFullBatchTrainer
from fastglycan.native_parallel_audit import assert_tree_equal, cpu_snapshot
from fastglycan.pair_placement import PlacementBoundaries, placement_lock, placement_model
from fastglycan.pair_recovery_data import PairRecoveryData
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.reference_editor_multiref import editor_state_digest
from fastglycan.response_moments import ResponseMoments
from fastglycan.site_parallel import local_anchor_gradients, synchronized_anchor_step
from fastglycan.stage_fullbatch import parameter_digest
from fastglycan.stage_pair_data import StagePairData


def run_placement(root, arm, seed, mode, runtime_factory, launch):
    root=Path(root);lock=placement_lock(root);rank,world,address=launch
    assert world==6 and mode in ('audit','train')
    assert seed in lock['seeds'] and arm in lock['arms']
    if mode=='audit':assert arm=='early' and seed==272001
    if mode=='train':
        accepted=json.loads((root/'parallel_gate.json').read_text())
        assert accepted['complete'] and accepted['bitwise_steps']==[1,2]
        assert accepted['lock_sha256']==sha256(root/'training_lock.json')
    folder=root/'parallel_gate' if mode=='audit' else root/'runs'/arm/str(seed)
    # Every rank owns a distinct report/runtime directory.
    folder.mkdir(parents=True,exist_ok=True)
    worker=folder/f'rank_{rank}';worker.mkdir(exist_ok=False)
    start=time.monotonic();handles=[];counts=Counter()
    report=dict(complete=False,phase='loading',arm=arm,seed=seed,mode=mode,rank=rank,
        steps=0,checkpoints=[],lock_sha256=sha256(root/'training_lock.json'))

    def save():
        report.update(seconds=time.monotonic()-start,counts=dict(counts))
        write_json(worker/'report.json',report)
        print('PLACEMENT_STATE',mode,arm,seed,rank,report['phase'],report['steps'],flush=True)

    try:
        save();torch.set_num_threads(1);torch.cuda.set_device(0)
        assert torch.cuda.device_count()==1 and os.environ['HIP_VISIBLE_DEVICES']==str(rank)
        hip=ctypes.CDLL('/opt/rocm/lib/libamdhip64.so');bus=ctypes.create_string_buffer(64)
        hip.hipDeviceGetPCIBusId.argtypes=[ctypes.c_char_p,ctypes.c_int,ctypes.c_int]
        assert hip.hipDeviceGetPCIBusId(bus,64,0)==0
        assert bus.value.decode().lower()==lock['pci_buses'][rank].lower()
        rt=runtime_factory(Path(lock['source']),str(worker/'runtime'));b=rt.base
        from protenix.utils.distributed import DIST_WRAPPER
        assert DIST_WRAPPER.rank==DIST_WRAPPER.local_rank==0 and DIST_WRAPPER.world_size==1
        assert not dist.is_initialized() and torch.__version__==lock['torch_version']
        net=placement_model(rt.model,arm,seed).train()
        native_hash=editor_state_digest(rt.model)
        assert editor_state_digest(net)==lock['placement_initial_hashes'][f'{arm}_{seed}']
        if arm=='early':assert net.continuation.initial_digest==lock['frozen_digest']
        data=PairRecoveryData(lock['build_root'],lock['cache_manifest_sha256'])
        stages=StagePairData(lock['stage_root'],lock['stage_manifest_sha256'])
        boundaries=PlacementBoundaries(lock['boundary_root'],lock['boundary_manifest_sha256'])
        reference_pairs={pi:value[0][1] for pi,value in rt.prefixes.items()}
        reference_boundaries={pi:boundaries.reference(pi,arm) for pi in b.references}
        keys=lock['train_sites'];sites=[b.sites[key] for key in keys]
        assert len(keys)==27 and all(s['role_n15']=='train' for s in sites)
        indices=list(range(rank,len(keys),world))
        needed=range(len(keys)) if mode=='audit' and rank==0 else indices
        resident={};byte_count=0
        for index in needed:
            for aa in sites[index]['candidates']:
                label=b.label(sites[index]['parent_index'],sites[index]['position_zero_based'],aa)
                base=data.base(label)
                boundary=boundaries.candidate(label) if arm=='early' else stages.load(label,training=False)[0]
                target=data.target(label);resident[label]=(base,boundary,target)
                byte_count+=sum(t.numel()*t.element_size() for t in (*base,boundary,target))
                assert byte_count<=lock['resident_tensor_byte_cap']

        def fetch(site,aa):
            assert site['site_key'] in keys and site['role_n15']=='train'
            return resident[b.label(site['parent_index'],site['position_zero_based'],aa)]

        def forbid(*args):raise AssertionError('native trunk or input encoder forbidden in placement fit')
        def decoder_guard(*args):
            if report['phase']!='evaluation':raise AssertionError('S1 is evaluation-only')
        handles=[rt.model.pairformer_stack.register_forward_pre_hook(forbid),
                 rt.model.input_embedder.register_forward_pre_hook(forbid),
                 rt.model.diffusion_module.register_forward_pre_hook(decoder_guard)]
        args=(net,sites,fetch,reference_pairs,b.aa,lock['site_scale_squared'],b.references,reference_boundaries)
        trainer=AnchoredFullBatchTrainer(*args) if rank==0 and mode=='audit' else None
        dist.init_process_group('gloo',init_method=address,rank=rank,world_size=world,timeout=timedelta(seconds=1200))
        report.update(cache_bytes=byte_count,local_sites=[keys[i] for i in indices],loading_seconds=time.monotonic()-start)
        dist.barrier();torch.cuda.reset_peak_memory_stats();save()

        def parallel_step(optimizer):
            local,error=[],None
            try:
                local=local_anchor_gradients(*args,indices=indices)
                for record in local:
                    counts.update({k:record['counts'][k] for k in ('forwards','backwards','reference_forwards','reference_backwards')})
            except Exception as failure:error=repr(failure)
            return synchronized_anchor_step(net,local,keys,optimizer,local_error=error)

        def optimizer_new():
            return torch.optim.AdamW(net.parameters(),lr=1e-4,weight_decay=1e-4,eps=1e-8) if rank==0 else None

        if mode=='audit':
            initial=cpu_snapshot(net.state_dict());expected={};times=[]
            for method in ('serial','parallel'):
                net.load_state_dict(initial);net.zero_grad(set_to_none=True);optimizer=optimizer_new()
                for step in (1,2):
                    report['phase']=method;report['steps']=step;save()
                    dist.barrier();torch.cuda.synchronize();begin=time.monotonic()
                    if method=='serial':
                        if rank==0:
                            objective=trainer.objective();gradient=trainer.last_gradient
                            objective={k:objective[k] for k in ('raw','common','centered','sites')}
                            torch.nn.utils.clip_grad_norm_(net.parameters(),1.,error_if_nonfinite=True);optimizer.step()
                            counts.update(forwards=513,backwards=513,reference_forwards=27,reference_backwards=27)
                    else:
                        result=parallel_step(optimizer);gradient=result['gradient']
                        objective={k:result['summary'][k] for k in ('raw','common','centered','sites')}
                    torch.cuda.synchronize();dist.barrier();seconds=time.monotonic()-begin
                    times.append(dict(method=method,step=step,seconds=seconds))
                    if rank==0:
                        snapshot=dict(gradient=gradient.clone(),objective=objective,
                            model=cpu_snapshot(net.state_dict()),optimizer=cpu_snapshot(optimizer.state_dict()))
                        torch.save(snapshot,folder/f'{method}_{step}.pt')
                        if method=='serial':expected[step]=snapshot
                        else:assert_tree_equal(snapshot,expected[step])
                    dist.barrier()
                del optimizer
            if rank==0:
                write_json(root/'parallel_gate.json',dict(complete=True,bitwise_steps=[1,2],times=times,
                    lock_sha256=sha256(root/'training_lock.json'),training_started=False,
                    snapshots={p.name:sha256(p) for p in folder.glob('*.pt')}))
        else:
            optimizer=optimizer_new()
            if rank==0:
                (folder/'coordinates').mkdir(exist_ok=False);(folder/'checkpoints').mkdir(exist_ok=False)
            dist.barrier()

            def evaluate(step):
                report['phase']='evaluation';save();net.eval();begin=time.monotonic()
                rows,latent=[],[]
                with torch.no_grad():
                    for index,key in enumerate(lock['eval_sites']):
                        if index%world!=rank:continue
                        site=b.sites[key];pi,pos=site['parent_index'],site['position_zero_based']
                        old=b.aa.index(site['original_aa']);ref=reference_pairs[pi]
                        anchor=net.prepare_reference(b.references[pi],reference_boundaries[pi],ref,pos,old)
                        counts['evaluation_reference_forwards']+=1
                        moments,mismatch,residual=ResponseMoments(),ResponseMoments(),{}
                        first=None
                        for aa in site['candidates']:
                            label=b.label(pi,pos,aa);base=data.base(label)
                            boundary=boundaries.candidate(label) if arm=='early' else stages.load(label,training=False)[0]
                            conditioning=net(base,boundary,ref,pos,old,b.aa.index(aa),anchor=anchor)
                            counts['evaluation_forwards']+=1
                            assert conditioning[0] is base[0] and conditioning[1] is base[1]
                            if step==0:
                                assert torch.count_nonzero(anchor.drift)==0 and torch.equal(conditioning[2],base[2])
                            moments.add(conditioning[2]-base[2],data.target(label)-base[2])
                            residual[aa]=(conditioning[2]-base[2]).cpu()
                            if first is None:first=(aa,conditioning[2].clone())
                            item=b.item(pi,pos,aa)
                            xyz=np.stack([b.decode(item,conditioning,ni).cpu().numpy() for ni in (0,1)])
                            assert np.isfinite(xyz).all()
                            if step==0:
                                rec=rt.preflight['baseline'][label];path=Path(rt.lock['native_root'])/rec['path']
                                assert sha256(path)==rec['sha256']
                                assert np.array_equal(xyz,np.load(path)['coordinates']),label
                            path=folder/'coordinates'/f'{step}_correct_{label}.npz';np.savez_compressed(path,coordinates=xyz)
                            rows.append(dict(path=str(path.relative_to(folder)),sha256=sha256(path),label=label,arm='correct'))
                        # Querying other candidates must not alter the first candidate.
                        aa,expected=first;label=b.label(pi,pos,aa);base=data.base(label)
                        boundary=boundaries.candidate(label) if arm=='early' else stages.load(label,training=False)[0]
                        replay=net(base,boundary,ref,pos,old,b.aa.index(aa),anchor=anchor)
                        assert torch.equal(replay[2],expected)
                        assert net(b.references[pi],reference_boundaries[pi],ref,pos,old,old,anchor=anchor) is b.references[pi]
                        counts['isolation_forwards']+=1
                        if step==lock['gradient_budget']:
                            for i,aa in enumerate(site['candidates']):
                                donor=site['candidates'][(i+1)%19];label=b.label(pi,pos,aa);base=data.base(label)
                                conditioning=(base[0],base[1],base[2]+residual[donor].cuda())
                                mismatch.add(conditioning[2]-base[2],data.target(label)-base[2])
                                item=b.item(pi,pos,aa)
                                xyz=np.stack([b.decode(item,conditioning,ni).cpu().numpy() for ni in (0,1)])
                                assert np.isfinite(xyz).all()
                                path=folder/'coordinates'/f'{step}_mismatched_{label}.npz';np.savez_compressed(path,coordinates=xyz)
                                rows.append(dict(path=str(path.relative_to(folder)),sha256=sha256(path),label=label,arm='mismatched',donor=donor))
                        latent.append(dict(site=key,pdb=site['pdb_id'],parent=pi,role=site['role_n15'],
                            moments=moments.result(),mismatch=mismatch.result() if mismatch.n else None))
                        print('PLACEMENT_EVAL',arm,seed,step,rank,key,flush=True)
                gathered=[None]*world if rank==0 else None
                dist.gather_object(dict(predictions=rows,latent=latent),gathered,dst=0)
                if rank==0:
                    cp=folder/'checkpoints'/f'{step}.pt'
                    torch.save(dict(state_dict=cpu_snapshot(net.state_dict()),optimizer=cpu_snapshot(optimizer.state_dict()),
                        step=step,config=net.config,training_lock_sha256=sha256(root/'training_lock.json')),cp)
                    historical=None
                    if arm=='late':
                        oldpath=Path(lock['previous_root'])/'runs/anchor'/str(seed)/'checkpoints'/f'{step}.pt'
                        oldstate=torch.load(oldpath,map_location='cpu',weights_only=False)
                        assert_tree_equal(cpu_snapshot(net.state_dict()),oldstate['state_dict'])
                        assert_tree_equal(cpu_snapshot(optimizer.state_dict()),oldstate['optimizer'])
                        historical=dict(path=str(oldpath),sha256=sha256(oldpath),bitwise=True)
                    all_latent={r['site']:r for part in gathered for r in part['latent']}
                    predictions=[r for part in gathered for r in part['predictions']]
                    assert len(all_latent)==48 and len(predictions)==(1824 if step==128 else 912)
                    write_json(folder/f'evaluation_{step}.json',dict(complete=True,step=step,
                        latent=[all_latent[key] for key in lock['eval_sites']],predictions=predictions,
                        checkpoint=str(cp.relative_to(folder)),sha256=sha256(cp),historical=historical,
                        gradient_passes=step,optimizer_calls=step,seconds=time.monotonic()-begin))
                report['checkpoints'].append(step);net.train();report['phase']='training';save();dist.barrier()

            evaluate(0)
            history=(folder/'history.jsonl').open('x',buffering=1) if rank==0 else None
            try:
                for step in range(1,129):
                    dist.barrier();torch.cuda.synchronize();begin=time.monotonic()
                    result=parallel_step(optimizer)
                    torch.cuda.synchronize();dist.barrier();seconds=time.monotonic()-begin
                    report.update(steps=step,last_objective=result['summary']['raw'],last_centered=result['summary']['centered'])
                    if rank==0:
                        history.write(json.dumps(dict(step=step,summary=result['summary'],gradient_norm=result['gradient_norm'],
                            clipped=result['clipped'],parameter_sha256=result['parameter_sha256'],seconds=seconds))+'\n')
                    save()
                    if step in (32,128):evaluate(step)
            finally:
                if history:history.close()
            assert counts['forwards']==counts['backwards']==len(indices)*19*128
            assert counts['reference_forwards']==counts['reference_backwards']==len(indices)*128
            assert counts['evaluation_forwards']==456 and counts['evaluation_reference_forwards']==24
            assert counts['isolation_forwards']==24
            assert b.counts==dict(c4=0,input_embedder=0,recycle=0,s1=1216,updates=0)
        if arm=='early':
            net.continuation.check_unchanged();report['frozen_continuation_calls']=net.continuation.calls
        assert editor_state_digest(rt.model)==native_hash and all(p.grad is None for p in rt.model.parameters())
        for handle in handles:handle.remove()
        handles.clear();rt.finish()
        report.update(complete=True,phase='complete',native_counts=dict(b.counts),
            peak_allocated_bytes=torch.cuda.max_memory_allocated(),final_sha256=editor_state_digest(net))
        save();dist.barrier()
    except BaseException as error:
        report.update(phase='failed',error=repr(error),traceback=traceback.format_exc());save();raise
    finally:
        for handle in handles:handle.remove()
        if dist.is_initialized():dist.destroy_process_group()
