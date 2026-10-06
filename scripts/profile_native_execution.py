"""Read-only native C4 profiling; no output/cache/precision modifications."""
import argparse,cProfile,gzip,json,pstats,time
from pathlib import Path
import numpy as np
import torch
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.context_replication import native_sequences,NOISES
from fastglycan.native_budget import screen_native
from fastglycan.hip_device_policy import guarded_hip_runtime
from fastglycan.execution_profile import StageRecorder,leaf_inventory,compare_inventory,operator_table


def load(p):return json.loads(Path(p).read_text())


def profile_native_execution(root):
    from fastglycan.models.soft_sequence_chart import native_sequence_features,device_tree
    from fastglycan.models.differentiable_mini import full_recycle_pairformer,prepare_atom_pairs,diffusion_from_conditioning
    from fastglycan.functional_response_rank import pack_conditioning
    from fastglycan.hybrid_proposals import identity_noise
    from fastglycan.adapter_supervision import build_adapter_supervision
    from fastglycan.backbone_sequence_task import backbone_target_pairs
    from run_context_replication import inventory_of
    from run_prefix_reuse import rng_fingerprint
    runtime=guarded_hip_runtime();prior=root.parent/'native_budget_v1_20261005';old=load(prior/'lock.json')
    assert load(prior/'execution.json')['complete'] and load(prior/'independent_audit.json')['complete']
    cases=[]
    for pi in old['parents']:
        for label,seq,pos,aa in list(native_sequences(old['prior_lock']['rows'][pi],pi))[:2]:
            cases.append(dict(parent_index=pi,label=label,sequence=seq,position=pos,aa=aa,trace=pos is not None and pi in [0,13,28,8]))
    assert len(cases)==18 and sum(c['trace'] for c in cases)==4
    assets={str(prior/'lock.json'):sha256(prior/'lock.json')}
    assets.update(old['prior_lock']['weights_sha256'])
    for p,h in assets.items():assert sha256(Path(p))==h
    code={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.md']}
    assert not (root/'lock.json').exists()
    write_json(root/'lock.json',dict(cases=cases,assets=assets,code=code,source_native_lock=old,role='profile_only_no_optimization',seeds=list(NOISES)))
    t=time.perf_counter();runner=rt.runner_setup(root/'work');runner.configs.dtype='fp32';model=runner.model.eval().requires_grad_(False)
    torch.serialization.add_safe_globals([argparse.Namespace])
    from protenix.data.esm.compute_esm import load_esm_model
    esm,alphabet=load_esm_model('esm2-3b',local_esm_dir=runner.configs.load_checkpoint_dir);esm.eval().requires_grad_(False)
    torch.cuda.synchronize();load_seconds=time.perf_counter()-t
    counts=dict(c4=0,recycle=0,s1=0,replayed_outputs=0)
    hooks=[model.pairformer_stack.register_forward_hook(lambda *a:counts.__setitem__('recycle',counts['recycle']+1)),model.diffusion_module.register_forward_hook(lambda *a:counts.__setitem__('s1',counts['s1']+1))]
    report=dict(complete=False,runtime=runtime,model_load_seconds=load_seconds,records=[],dependencies=[],cache_diagnostics=[],profiles=[],parent_setup=[],counts=counts)
    t0=time.perf_counter();wt_inventory={};root.joinpath('coordinates').mkdir();root.joinpath('traces').mkdir()
    with torch.no_grad():
        for item in cases:
            pi=item['parent_index'];label=item['label'];seq=item['sequence'];pos=item['position']
            t=time.perf_counter();ni=old['native'][label];assert sha256(Path(ni['path']))==ni['sha256'];inv=dict(np.load(ni['path']))
            gi=old['prior_lock']['gt'][str(pi)];assert sha256(Path(gi['path']))==gi['sha256'];gt=dict(np.load(gi['path']));ca=gt['atom_names']=='CA'
            pairs,distances=backbone_target_pairs(gt['coordinates'][ca],gt['mask'][ca]);archive=old['archives'][label]
            assert sha256(Path(archive['path']))==archive['sha256'];reference=np.load(archive['path'])['coordinates']
            report['parent_setup'].append(dict(label=label,seconds=time.perf_counter()-t))

            def one(kind,sync=False,annotate=False):
                stages=StageRecorder(torch.cuda.synchronize if sync else None,annotate)
                torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats();begin=time.perf_counter()
                with stages.stage('native_features'):
                    raw,atoms=native_sequence_features(seq);actual=inventory_of(seq,raw,atoms)
                    assert all(np.array_equal(actual[k],inv[k]) for k in actual)
                with stages.stage('host_to_device'):device=device_tree(raw,'cuda')
                with stages.stage('relative_and_atom_preparation'):f=prepare_atom_pairs(model.relative_position_encoding.generate_relp(device))
                with stages.stage('esm'):
                    tokens=alphabet.get_batch_converter()([('hard',seq)])[2].cuda()
                    f['esm_token_embedding']=esm(tokens,repr_layers=[esm.num_layers],return_contacts=False)['representations'][esm.num_layers][0,1:-1]
                with stages.stage('C4_native_trunk'):c=full_recycle_pairformer(model,f,N_cycle=4,inplace_safe=False,mc_dropout=False)
                counts['c4']+=1;xyz=[]
                for j,seed in enumerate(NOISES):
                    with stages.stage(f'S1_noise_{j}'):
                        x=diffusion_from_conditioning(model,f,identity_noise(atoms,seed,device='cuda'),pack_conditioning(c),steps=1).squeeze(0)
                    with stages.stage(f'host_transfer_{j}'):xyz.append(x.cpu().numpy())
                xyz=np.stack(xyz)
                with stages.stage('geometry_label_setup'):labs=build_adapter_supervision(dict(inv,coordinates=xyz[0],mask=np.ones(len(xyz[0]),bool)),inv['bonds'],seq)
                with stages.stage('task_and_geometry'):scores=[screen_native(x,inv,labs,pairs,distances) for x in xyz]
                with stages.stage('coordinate_write'):
                    file=root/'coordinates'/f'{label}_{kind}.npz';np.savez_compressed(file,coordinates=xyz,seeds=NOISES)
                torch.cuda.synchronize();elapsed=time.perf_counter()-begin;peak=torch.cuda.max_memory_allocated()
                assert np.array_equal(reference,xyz),(label,kind,'C4 replay mismatch');counts['replayed_outputs']+=4
                report['records'].append(dict(label=label,parent_index=pi,kind=kind,wall_seconds=elapsed,stages=stages.seconds,stage_gpu_synchronized=sync,annotated=annotate,
                    peak_allocated_bytes=peak,atom_count=len(xyz[0]),length=len(seq),replay_bitwise=True,coordinates=dict(path=str(file),sha256=sha256(file)),scores=scores))
                return raw,f,c

            if item==cases[0]:
                result=one('first_invocation');del result
            result=one('warmup');del result
            for repeat in range(3):
                result=one(f'steady_{repeat}');del result
            raw,f,c=one('stage_breakdown',sync=True)
            observed=leaf_inventory(dict(raw=raw,prepared=f,conditioning=dict(s_inputs=c[0],s=c[1],z=c[2])))
            dependency=dict(label=label,leaves=observed)
            if pos is None:wt_inventory[pi]=observed
            else:dependency['compared_to_WT']=compare_inventory(wt_inventory[pi],observed)
            report['dependencies'].append(dependency)
            module=model.diffusion_module;names=('ref_pos','ref_charge','ref_mask','ref_element','ref_atom_name_chars','atom_to_token_idx','d_lm','v_lm','pad_info')
            cache_ref=None;times=[];initial_rng=rng_fingerprint()
            for repeat in range(4):
                torch.cuda.synchronize();t=time.perf_counter();pair_z=module.diffusion_conditioning.prepare_cache(f['relp'],c[2],False)
                torch.cuda.synchronize();pair_time=time.perf_counter()-t;t=time.perf_counter()
                atom=module.atom_attention_encoder.prepare_cache(**{k:f[k] for k in names},r_l=True,z=pair_z,inplace_safe=False)
                torch.cuda.synchronize();atom_time=time.perf_counter()-t
                observed_cache=leaf_inventory(dict(pair_z=pair_z,atom=atom))
                if cache_ref is None:cache_ref=observed_cache
                else:assert observed_cache==cache_ref,(label,'cache not identical')
                assert rng_fingerprint()==initial_rng,(label,'cache advances RNG')
                times.append(dict(pair_seconds=pair_time,atom_seconds=atom_time))
                del pair_z,atom
            report['cache_diagnostics'].append(dict(label=label,repeats=4,bitwise_equal=True,rng_unchanged=True,times=times,output_inventory=cache_ref))
            del raw,f,c
            if item['trace']:
                supported=torch.profiler.supported_activities();activities=[torch.profiler.ProfilerActivity.CPU]
                if torch.profiler.ProfilerActivity.CUDA in supported:activities.append(torch.profiler.ProfilerActivity.CUDA)
                with torch.profiler.profile(activities=activities,record_shapes=True,profile_memory=True,with_stack=False) as prof:
                    result=one('torch_profile',annotate=True);del result
                trace=root/'traces'/f'{label}.json';prof.export_chrome_trace(str(trace));table=operator_table(prof)
                device_events=sum(1 for e in prof.events() if str(e.device_type).endswith('CUDA'))
                report['profiles'].append(dict(label=label,activities=list(map(str,activities)),device_events=device_events,gpu_attribution_available=device_events>0,operators=table,trace=dict(path=str(trace),sha256=sha256(trace))))
                del prof
                cp=cProfile.Profile();cp.enable();result=one('cpu_profile');cp.disable();del result
                cp.dump_stats(str(root/'traces'/f'{label}.pstats'));stats=pstats.Stats(cp);rows=[]
                for (file,line,name),(primitive,total,own,cumulative,callers) in stats.stats.items():
                    rows.append(dict(file=file,line=line,name=name,primitive_calls=primitive,calls=total,self_seconds=own,cumulative_seconds=cumulative))
                write_json(root/'traces'/f'{label}_cpu.json',sorted(rows,key=lambda x:x['self_seconds'],reverse=True))
            report.update(counts=dict(counts),seconds=time.perf_counter()-t0,active=label);write_json(root/'report.json',report)
    for h in hooks:h.remove()
    assert counts==dict(c4=99,recycle=396,s1=396,replayed_outputs=396),counts
    for p,h in assets.items():assert sha256(Path(p))==h
    for p,h in code.items():assert sha256(Path(p))==h
    report.update(complete=True,counts=counts,seconds=time.perf_counter()-t0);write_json(root/'report.json',report)
    write_json(root/'execution_checks.json',dict(complete=True,counts=counts,all_coordinates_bitwise=True,dependency_cases=18,cache_repetitions=72,operator_traces=4,optimizer_updates=0))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();started=time.perf_counter()
    try:
        profile_native_execution(a.root)
        from audit_native_execution import audit_native_execution
        audit_native_execution(a.root)
        write_json(a.root/'execution.json',dict(complete=True,seconds=time.perf_counter()-started))
    except BaseException as e:
        write_json(a.root/'execution.json',dict(complete=False,error=repr(e),seconds=time.perf_counter()-started));raise
