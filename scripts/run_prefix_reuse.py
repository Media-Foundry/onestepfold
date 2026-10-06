"""Matched-depth WT-prefix reuse; native cold references and hard candidate inputs."""
import argparse,json,time,random,itertools
from pathlib import Path
import numpy as np
import torch
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.native_budget import screen_native
from fastglycan.context_replication import AA,NOISES,native_sequences
from fastglycan.hip_device_policy import guarded_hip_runtime
from fastglycan.models.prefix_recycle import prefix_recycle_pairformer,capture_rng_state,restore_rng_state
from run_native_budget import prepare_native_budget,verify_native_budget

ARMS=(2,4,22,31)
ARM_NAMES={2:"cold_C2",4:"cold_C4",22:"WT2_Target2",31:"WT3_Target1"}


def load(p):return json.loads(Path(p).read_text())


def prepare_prefix_reuse(root):
    prepare_native_budget(root)
    lock=load(root/'lock.json');previous=root.parent/'native_budget_v1_20261005'
    assert load(previous/'execution.json')['complete'] and load(previous/'independent_audit.json')['complete']
    lock.update(arms=list(ARMS),arm_names=ARM_NAMES,cycles=None,
        expected=dict(sequences=693,conditioning=2763,recycle=6246,s1=11052,coordinate_replays=2772,source_replays=36),
        integrity_cases=18,logical_depth=4,prefix_only_token_state=True)
    for name in ['lock.json','execution.json','independent_audit.json']:
        lock['asset_hashes'][str(previous/name)]=sha256(previous/name)
    write_json(root/'lock.json',lock)


def verify_prefix_reuse(root):return verify_native_budget(root)


def setup_prefix_model(root,index,label):
    runtime=guarded_hip_runtime();lock=verify_prefix_reuse(root)
    for p,h in lock['prior_lock']['weights_sha256'].items():assert sha256(Path(p))==h
    out=root/f'{label}_{index}';out.mkdir(exist_ok=False)
    t=time.monotonic();runner=rt.runner_setup(out/'work');runner.configs.dtype='fp32';model=runner.model.eval().requires_grad_(False)
    torch.serialization.add_safe_globals([argparse.Namespace])
    from protenix.data.esm.compute_esm import load_esm_model
    esm,alphabet=load_esm_model('esm2-3b',local_esm_dir=runner.configs.load_checkpoint_dir);esm.eval().requires_grad_(False)
    torch.cuda.synchronize()
    return runtime,lock,out,model,esm,alphabet,time.monotonic()-t


def prefix_features(model,esm,alphabet,seq,inventory):
    from fastglycan.models.soft_sequence_chart import native_sequence_features,device_tree
    from fastglycan.models.differentiable_mini import prepare_atom_pairs
    from run_context_replication import inventory_of
    t=time.monotonic();raw,atoms=native_sequence_features(seq);actual=inventory_of(seq,raw,atoms)
    assert all(np.array_equal(actual[k],inventory[k]) for k in actual)
    native_time=time.monotonic()-t;t=time.monotonic()
    f=prepare_atom_pairs(model.relative_position_encoding.generate_relp(device_tree(raw,'cuda')))
    torch.cuda.synchronize();prepare_time=time.monotonic()-t;t=time.monotonic()
    tokens=alphabet.get_batch_converter()([('hard',seq)])[2].cuda()
    f['esm_token_embedding']=esm(tokens,repr_layers=[esm.num_layers],return_contacts=False)['representations'][esm.num_layers][0,1:-1]
    torch.cuda.synchronize()
    return f,atoms,dict(native_seconds=native_time,device_atom_seconds=prepare_time,esm_seconds=time.monotonic()-t)


def rng_fingerprint():
    import hashlib,pickle
    return hashlib.sha256(pickle.dumps((random.getstate(),np.random.get_state(),torch.get_rng_state().numpy().tobytes(),[x.cpu().numpy().tobytes() for x in torch.cuda.get_rng_state_all()]))).hexdigest()


def gate_prefix_reuse(root,index):
    from fastglycan.models.differentiable_mini import full_recycle_pairformer
    runtime,lock,out,model,esm,alphabet,load_time=setup_prefix_model(root,index,'gate')
    records=[]
    with torch.no_grad():
        for pi in lock['assignments'][index]:
            cases=list(native_sequences(lock['prior_lock']['rows'][pi],pi))[:2]
            for label,seq,pos,aa in cases:
                inv=dict(np.load(lock['native'][label]['path']));f,atoms,_=prefix_features(model,esm,alphabet,seq,inv)
                initial_rng=capture_rng_state();before=rng_fingerprint();trace=[];hooks=[];entries={}
                for module_name in ['input_embedder','template_embedder','msa_module','pairformer_stack']:
                    module=getattr(model,module_name)
                    hooks.append(module.register_forward_pre_hook(lambda m,a,n=module_name:entries.__setitem__(n,rng_fingerprint())))
                    hooks.append(module.register_forward_hook(lambda m,a,o,n=module_name:trace.append(dict(module=n,rng_changed=rng_fingerprint()!=entries[n]))))
                exact=full_recycle_pairformer(model,f,N_cycle=4,inplace_safe=False,mc_dropout=False);after=rng_fingerprint()
                for h in hooks:h.remove()
                restore_rng_state(initial_rng)
                snapshots={};snapshot_rng={};new=prefix_recycle_pairformer(model,f,4,capture_cycles=(2,3),snapshots=snapshots,snapshot_rng=snapshot_rng)
                assert rng_fingerprint()==after,(label,'capture RNG replay mismatch')
                assert all(torch.equal(x,y) for x,y in zip(exact,new)),(label,'zero C4 mismatch')
                checks=[]
                for depth in [2,3]:
                    cached=tuple(t.clone() for t in snapshots[depth])
                    result=prefix_recycle_pairformer(model,f,4-depth,initial_state=snapshots[depth],initial_rng=snapshot_rng[depth])
                    assert rng_fingerprint()==after,(label,'continuation RNG replay mismatch')
                    assert all(torch.equal(x,y) for x,y in zip(exact,result)),(label,depth,'split mismatch')
                    assert all(torch.equal(x,y) for x,y in zip(cached,snapshots[depth])),(label,'cache modified')
                    checks.append(depth)
                records.append(dict(parent_index=pi,label=label,role='WT' if pos is None else 'target_audit_only',zero_C4_bitwise=True,split_bitwise=checks,rng_restored_exactly=True,native_rng_changed=before!=after,rng_trace=trace))
                del f,atoms,exact,new,result,snapshots,cached
    write_json(out/'report.json',dict(complete=True,runtime=runtime,records=records,model_load_seconds=load_time))


def infer_prefix_reuse(root,index):
    from fastglycan.models.differentiable_mini import full_recycle_pairformer,diffusion_from_conditioning
    from fastglycan.functional_response_rank import pack_conditioning
    from fastglycan.hybrid_proposals import identity_noise
    from fastglycan.adapter_supervision import build_adapter_supervision
    from fastglycan.backbone_sequence_task import backbone_target_pairs
    for i in range(4):assert load(root/f'gate_{i}/report.json')['complete']
    runtime,lock,out,model,esm,alphabet,model_load=setup_prefix_model(root,index,'worker');old=lock['prior_lock'];start=time.monotonic()
    counts=dict(conditioning=0,recycle=0,s1=0,coordinate_replays=0,source_replays=0)
    hooks=[model.pairformer_stack.register_forward_hook(lambda *a:counts.__setitem__('recycle',counts['recycle']+1)),model.diffusion_module.register_forward_hook(lambda *a:counts.__setitem__('s1',counts['s1']+1))]
    report=dict(complete=False,runtime=runtime,model_load_seconds=model_load,records=[],sources=[],parent_setup=[],counts=counts)
    orders=list(itertools.permutations(ARMS))
    with torch.no_grad():
        for pi in lock['assignments'][index]:
            t=time.monotonic();g=old['gt'][str(pi)];assert sha256(Path(g['path']))==g['sha256'];gt=dict(np.load(g['path']));ca=gt['atom_names']=='CA'
            pairs,distances=backbone_target_pairs(gt['coordinates'][ca],gt['mask'][ca]);report['parent_setup'].append(dict(parent_index=pi,seconds=time.monotonic()-t))
            wt_snapshots={};wt_rng={};snapshot_guard=None
            for si,(label,seq,pos,aa) in enumerate(native_sequences(old['rows'][pi],pi)):
                item=lock['native'][label];assert sha256(Path(item['path']))==item['sha256'];inv=dict(np.load(item['path']));arch=lock['archives'][label]
                arms=('source',2,4) if pos is None else orders[(pi*77+si)%len(orders)]
                for arm in arms:
                    torch.cuda.synchronize();begin=time.monotonic();f,atoms,timing=prefix_features(model,esm,alphabet,seq,inv)
                    t=time.monotonic()
                    if arm=='source':
                        c=prefix_recycle_pairformer(model,f,4,capture_cycles=(2,3),snapshots=wt_snapshots,snapshot_rng=wt_rng)
                    elif arm in (2,4):
                        c=full_recycle_pairformer(model,f,N_cycle=arm,inplace_safe=False,mc_dropout=False)
                    else:
                        depth=2 if arm==22 else 3
                        c=prefix_recycle_pairformer(model,f,4-depth,initial_state=wt_snapshots[depth],initial_rng=wt_rng[depth])
                    torch.cuda.synchronize();timing['trunk_seconds']=time.monotonic()-t;counts['conditioning']+=1;t=time.monotonic()
                    assert all(torch.isfinite(x).all() and x.dtype==torch.float32 for x in c)
                    xyz=np.stack([diffusion_from_conditioning(model,f,identity_noise(atoms,seed,device='cuda'),pack_conditioning(c),steps=1).squeeze(0).cpu().numpy() for seed in NOISES])
                    torch.cuda.synchronize();timing['decode_4noise_seconds']=time.monotonic()-t;assert np.isfinite(xyz).all();t=time.monotonic()
                    labs=build_adapter_supervision(dict(inv,coordinates=xyz[0],mask=np.ones(len(xyz[0]),bool)),inv['bonds'],seq)
                    scores=[screen_native(x,inv,labs,pairs,distances) for x in xyz];timing['screen_score_seconds']=time.monotonic()-t;t=time.monotonic()
                    file=out/f'{label}_{arm}.npz';np.savez_compressed(file,coordinates=xyz,seeds=NOISES)
                    timing['coordinate_write_seconds']=time.monotonic()-t;timing['total_seconds']=time.monotonic()-begin;t=time.monotonic();replay=False
                    if arm in ('source',4):
                        assert sha256(Path(arch['path']))==arch['sha256'];assert np.array_equal(np.load(arch['path'])['coordinates'],xyz),(label,'C4 replay')
                        counts['source_replays' if arm=='source' else 'coordinate_replays']+=4;replay=True
                    if arm=='source':snapshot_guard={k:tuple(x.clone() for x in state) for k,state in wt_snapshots.items()}
                    for k,state in wt_snapshots.items():
                        assert all(torch.equal(x,y) for x,y in zip(state,snapshot_guard[k])),(label,'shared prefix mutated')
                    timing['audit_replay_seconds']=time.monotonic()-t
                    rec=dict(parent_index=pi,label=label,position=pos,aa=aa,cycles=arm,coordinates=dict(path=str(file),sha256=sha256(file)),scores=scores,archive_bitwise_replay=replay,timing=timing)
                    if arm=='source':
                        rec['prefix_bytes']=sum(x.numel()*x.element_size() for state in wt_snapshots.values() for x in state)
                        report['sources'].append(rec)
                        # Both methods use the same once-computed WT baseline; each cost ledger pays it once.
                        for a in [22,31]:report['records'].append(dict(rec,cycles=a,wt_shared_source=True))
                    else:report['records'].append(rec)
                    del f,c,atoms,labs
                report.update(active=label,seconds=time.monotonic()-start,counts=dict(counts));write_json(out/'report.json',report)
            del wt_snapshots,snapshot_guard
    n=len(lock['assignments'][index]);assert counts==dict(conditioning=n*307,recycle=n*694,s1=n*1228,coordinate_replays=n*308,source_replays=n*4),counts
    for h in hooks:h.remove()
    report.update(complete=True,seconds=time.monotonic()-start,peak_allocated_bytes=torch.cuda.max_memory_allocated());write_json(out/'report.json',report)


def score_prefix_reuse(root,index):
    from fastglycan.functional_response_rank import prepare_fidelity_pairs,response_structure_metrics,fidelity_lddt
    from fastglycan.multicontext_response import noise_selection
    torch.set_num_threads(1);lock=verify_prefix_reuse(root);old=lock['prior_lock'];run=load(root/f'worker_{index}/report.json');assert run['complete']
    by={(r['label'],r['cycles']):r for r in run['records']};structures=[];sites=[];wt_gt=[]
    for pi in lock['assignments'][index]:
        endpoints={};gt=dict(np.load(old['gt'][str(pi)]['path']))
        for label,seq,pos,aa in native_sequences(old['rows'][pi],pi):
            inv=dict(np.load(lock['native'][label]['path']));ca=np.flatnonzero(inv['atom_names']=='CA');res=inv['residue_ids']
            exact_record=by[label,4];assert sha256(Path(exact_record['coordinates']['path']))==exact_record['coordinates']['sha256'];exact=np.load(exact_record['coordinates']['path'])['coordinates']
            caches=[(prepare_fidelity_pairs(y,res),prepare_fidelity_pairs(y[ca],res[ca])) for y in exact]
            for cycle in ARMS:
                r=by[label,cycle];assert sha256(Path(r['coordinates']['path']))==r['coordinates']['sha256'];co=np.load(r['coordinates']['path'])['coordinates'];endpoints[label,cycle]=r['scores']
                for ni,(x,y) in enumerate(zip(co,exact)):
                    local=np.arange(len(ca)) if pos is None else np.flatnonzero(np.linalg.norm(y[ca]-y[ca[pos]],axis=1)<=10)
                    m=response_structure_metrics(x,y,ca,local,caches[ni]);geo=r['scores'][ni]['geometry'];ref=exact_record['scores'][ni]['geometry']
                    structures.append(dict(parent_index=pi,label=label,position=pos,aa=aa,cycles=cycle,noise=NOISES[ni],role='stress' if old['rows'][pi]['pdb_id'].lower()=='2v66' else 'development',
                        geometry=geo,new_failure=ref['zero_severe_strict_checked_chirality'] and not geo['zero_severe_strict_checked_chirality'],repaired_failure=not ref['zero_severe_strict_checked_chirality'] and geo['zero_severe_strict_checked_chirality'],**m))
                    if pos is None:
                        assert np.array_equal(gt['atom_names'],inv['atom_names']) and np.array_equal(gt['residue_ids'],res)
                        obs=np.flatnonzero(gt['mask']);oc=ca[gt['mask'][ca]]
                        wt_gt.append(dict(parent_index=pi,cycles=cycle,noise=NOISES[ni],all_atom_lddt=fidelity_lddt(x[obs],prepare_fidelity_pairs(gt['coordinates'][obs],res[obs])),ca_lddt=fidelity_lddt(x[oc],prepare_fidelity_pairs(gt['coordinates'][oc],res[oc]))))
        for source,pos in old['rows'][pi]['sites'].items():
            wt=AA.index(old['rows'][pi]['sequence'][pos]);ids=[a for a in range(20) if a!=wt];names=[AA[a] for a in ids];mat={}
            for cycle in ARMS:
                parent=np.array([s['task'] for s in endpoints[f'p{pi}_wt',cycle]])
                mat[cycle]=np.array([[endpoints[f'p{pi}_s{pos+1}_{a}',cycle][ni]['task']-parent[ni] for a in names] for ni in range(4)])
            for cycle in ARMS:
                selection=noise_selection(mat[4],mat[cycle],names);chosen=selection['cross_noise']['student_old_choice'];label=f'p{pi}_s{pos+1}_{chosen}'
                sites.append(dict(parent_index=pi,pdb_id=old['rows'][pi]['pdb_id'],position=pos,source_aa=source,cycles=cycle,role='stress' if old['rows'][pi]['pdb_id'].lower()=='2v66' else 'development',
                    selection=selection,selected_actual_geometry=[s['geometry'] for s in endpoints[label,cycle]],selected_C4_geometry=[s['geometry'] for s in endpoints[label,4]],
                    selected_actual_task=[s['task'] for s in endpoints[label,cycle]]))
    write_json(root/f'score_{index}.json',dict(complete=True,structures=structures,sites=sites,wt_gt=wt_gt))


def collect_prefix_reuse(root):
    lock=verify_prefix_reuse(root);structures=[];sites=[];wt_gt=[];timings=[]
    for i in range(4):
        s=load(root/f'score_{i}.json');r=load(root/f'worker_{i}/report.json');assert s['complete'] and r['complete']
        structures+=s['structures'];sites+=s['sites'];wt_gt+=s['wt_gt']
        for pi in lock['assignments'][i]:
            setup=next(p['seconds'] for p in r['parent_setup'] if p['parent_index']==pi)
            for cycle in ARMS:
                rs=[x for x in r['records'] if x['parent_index']==pi and x['cycles']==cycle];assert len(rs)==77
                sums={k:sum(x['timing'][k] for x in rs) for k in rs[0]['timing']}
                timings.append(dict(parent_index=pi,pdb_id=lock['prior_lock']['rows'][pi]['pdb_id'],cycles=cycle,sequences=77,
                                    model_load_seconds=r['model_load_seconds'],shared_setup_seconds=setup,resident_screen_seconds=sums['total_seconds']+setup,
                                    first_use_screen_seconds=sums['total_seconds']+setup+r['model_load_seconds'],**sums))
    assert len(structures)==11088 and len(sites)==144
    write_json(root/'report.json',dict(complete=True,structures=structures,sites=sites,wt_gt=wt_gt,timings=timings,model_promoted=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--mode',required=True);p.add_argument('--index',type=int,default=0);a=p.parse_args()
    if a.mode=='prepare':prepare_prefix_reuse(a.root)
    elif a.mode=='gate':gate_prefix_reuse(a.root,a.index)
    elif a.mode=='infer':infer_prefix_reuse(a.root,a.index)
    elif a.mode=='score':score_prefix_reuse(a.root,a.index)
    elif a.mode=='collect':collect_prefix_reuse(a.root)
    else:raise ValueError(a.mode)
