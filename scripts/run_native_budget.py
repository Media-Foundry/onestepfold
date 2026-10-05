"""Matched real hard-candidate C1/C2/C4 screening; no trained surrogate."""
import argparse,json,time
from pathlib import Path
import numpy as np
import torch
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.native_budget import CYCLES,budget_parents,budget_order,screen_native
from fastglycan.context_replication import AA,NOISES,native_sequences
from fastglycan.hip_device_policy import guarded_hip_runtime


def load(p):return json.loads(Path(p).read_text())


def prepare_native_budget(root):
    assert not (root/'lock.json').exists()
    prior=root.parent/'context_replication_v1_20261005';old=load(prior/'lock.json');assert load(prior/'execution.json')['complete'] and load(prior/'independent_audit.json')['complete']
    parents=budget_parents(old['rows']);assignments=[[] for _ in range(4)];cost=[0]*4
    for pi in sorted(parents,key=lambda i:-len(old['rows'][i]['sequence'])):
        w=min(range(4),key=lambda i:cost[i]);assignments[w].append(pi);cost[w]+=len(old['rows'][pi]['sequence'])**2
    native={r['label']:r for r in load(prior/'native_manifest.json')['records']};archives={}
    for wi in range(4):
        for r in load(prior/f'teacher_{wi}/report.json')['records']:
            if r['parent_index'] in parents:archives[r['label']]=r['coordinates']
    assert len(archives)==693
    selected={label:native[label] for label in archives}
    assets=[prior/'lock.json',prior/'native_manifest.json',prior/'evaluation_labels.json',prior/'execution.json',prior/'independent_audit.json']
    write_json(root/'lock.json',dict(prior=str(prior),prior_lock=old,parents=parents,assignments=assignments,native=selected,archives=archives,
        cycles=list(CYCLES),seeds=list(NOISES),expected=dict(sequences=693,conditioning=2079,recycle=4851,s1=8316,coordinate_replays=2772),
        asset_hashes={str(p):sha256(p) for p in assets},code_hashes={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ('.py','.md')},
        inference_no_target_cache=True,role='development_plus_separate_stress'))


def verify_native_budget(root):
    lock=load(root/'lock.json')
    for g in ['asset_hashes','code_hashes']:
        for p,h in lock[g].items():assert sha256(Path(p))==h,p
    return lock


def infer_native_budget(root,index):
    from fastglycan.models.soft_sequence_chart import native_sequence_features,device_tree
    from fastglycan.models.differentiable_mini import full_recycle_pairformer,prepare_atom_pairs,diffusion_from_conditioning
    from fastglycan.functional_response_rank import pack_conditioning
    from fastglycan.hybrid_proposals import identity_noise
    from fastglycan.adapter_supervision import build_adapter_supervision
    from fastglycan.backbone_sequence_task import backbone_target_pairs
    from run_context_replication import inventory_of
    runtime=guarded_hip_runtime();lock=verify_native_budget(root);old=lock['prior_lock'];out=root/f'worker_{index}';out.mkdir(exist_ok=False)
    for p,h in old['weights_sha256'].items():assert sha256(Path(p))==h
    start=time.monotonic();t=start;runner=rt.runner_setup(out/'work');runner.configs.dtype='fp32';model=runner.model.eval().requires_grad_(False)
    torch.serialization.add_safe_globals([argparse.Namespace])
    from protenix.data.esm.compute_esm import load_esm_model
    esm,alphabet=load_esm_model('esm2-3b',local_esm_dir=runner.configs.load_checkpoint_dir);esm.eval().requires_grad_(False)
    torch.cuda.synchronize();model_load=time.monotonic()-t
    counts=dict(conditioning=0,recycle=0,s1=0,coordinate_replays=0)
    hooks=[model.pairformer_stack.register_forward_hook(lambda *a:counts.__setitem__('recycle',counts['recycle']+1)),model.diffusion_module.register_forward_hook(lambda *a:counts.__setitem__('s1',counts['s1']+1))]
    report=dict(complete=False,runtime=runtime,model_load_seconds=model_load,records=[],parent_setup=[],counts=counts)
    with torch.no_grad():
        for pi in lock['assignments'][index]:
            t=time.monotonic();g=old['gt'][str(pi)];assert sha256(Path(g['path']))==g['sha256'];gt=dict(np.load(g['path']));ca=gt['atom_names']=='CA'
            pairs,distances=backbone_target_pairs(gt['coordinates'][ca],gt['mask'][ca]);report['parent_setup'].append(dict(parent_index=pi,seconds=time.monotonic()-t))
            for si,(label,seq,pos,aa) in enumerate(native_sequences(old['rows'][pi],pi)):
                item=lock['native'][label];assert sha256(Path(item['path']))==item['sha256'];inv=dict(np.load(item['path']));arch=lock['archives'][label]
                # Archive coordinates are consulted only AFTER candidate inference, outside its timing.
                for cycle in budget_order(pi*77+si):
                    torch.cuda.synchronize();begin=time.monotonic();t=begin;raw,atoms=native_sequence_features(seq);actual=inventory_of(seq,raw,atoms)
                    assert all(np.array_equal(actual[k],inv[k]) for k in actual);native_time=time.monotonic()-t;t=time.monotonic()
                    f=prepare_atom_pairs(model.relative_position_encoding.generate_relp(device_tree(raw,'cuda')));torch.cuda.synchronize();prepare_time=time.monotonic()-t;t=time.monotonic()
                    tokens=alphabet.get_batch_converter()([('hard',seq)])[2].cuda();f['esm_token_embedding']=esm(tokens,repr_layers=[esm.num_layers],return_contacts=False)['representations'][esm.num_layers][0,1:-1]
                    torch.cuda.synchronize();esm_time=time.monotonic()-t;t=time.monotonic()
                    c=full_recycle_pairformer(model,f,N_cycle=cycle,inplace_safe=False,mc_dropout=False);torch.cuda.synchronize();trunk_time=time.monotonic()-t;counts['conditioning']+=1;t=time.monotonic()
                    assert all(torch.isfinite(x).all() and x.dtype==torch.float32 for x in c)
                    xyz=np.stack([diffusion_from_conditioning(model,f,identity_noise(atoms,seed,device='cuda'),pack_conditioning(c),steps=1).squeeze(0).cpu().numpy() for seed in NOISES])
                    torch.cuda.synchronize();decode_time=time.monotonic()-t;assert np.isfinite(xyz).all();t=time.monotonic()
                    labs=build_adapter_supervision(dict(inv,coordinates=xyz[0],mask=np.ones(len(xyz[0]),bool)),inv['bonds'],seq)
                    scores=[screen_native(x,inv,labs,pairs,distances) for x in xyz];score_time=time.monotonic()-t;t=time.monotonic()
                    file=out/f'{label}_c{cycle}.npz';np.savez_compressed(file,coordinates=xyz,seeds=NOISES);io_time=time.monotonic()-t;screen_time=time.monotonic()-begin
                    t=time.monotonic();replay=False
                    if cycle==4:
                        assert sha256(Path(arch['path']))==arch['sha256'];reference=np.load(arch['path'])['coordinates'];assert np.array_equal(reference,xyz),(label,'C4 archive replay mismatch')
                        counts['coordinate_replays']+=4;replay=True
                    audit_time=time.monotonic()-t
                    report['records'].append(dict(parent_index=pi,label=label,position=pos,aa=aa,cycles=cycle,coordinates=dict(path=str(file),sha256=sha256(file)),scores=scores,archive_bitwise_replay=replay,
                        timing=dict(native_seconds=native_time,device_atom_seconds=prepare_time,esm_seconds=esm_time,trunk_seconds=trunk_time,decode_4noise_seconds=decode_time,screen_score_seconds=score_time,coordinate_write_seconds=io_time,total_seconds=screen_time,audit_replay_seconds=audit_time)))
                    del f,c,raw,atoms,labs
                report.update(active=label,seconds=time.monotonic()-start,counts=dict(counts));write_json(out/'report.json',report)
    n=len(lock['assignments'][index]);assert counts==dict(conditioning=n*77*3,recycle=n*77*7,s1=n*77*12,coordinate_replays=n*77*4),counts
    for h in hooks:h.remove()
    report.update(complete=True,seconds=time.monotonic()-start,peak_allocated_bytes=torch.cuda.max_memory_allocated());write_json(out/'report.json',report)


def score_native_budget(root,index):
    from fastglycan.functional_response_rank import prepare_fidelity_pairs,response_structure_metrics,fidelity_lddt
    from fastglycan.multicontext_response import noise_selection
    torch.set_num_threads(1);lock=verify_native_budget(root);old=lock['prior_lock'];run=load(root/f'worker_{index}/report.json');assert run['complete']
    by={(r['label'],r['cycles']):r for r in run['records']};structures=[];sites=[];wt_gt=[]
    for pi in lock['assignments'][index]:
        endpoints={};gt=dict(np.load(old['gt'][str(pi)]['path']))
        for label,seq,pos,aa in native_sequences(old['rows'][pi],pi):
            inv=dict(np.load(lock['native'][label]['path']));ca=np.flatnonzero(inv['atom_names']=='CA');res=inv['residue_ids']
            exact_record=by[label,4];assert sha256(Path(exact_record['coordinates']['path']))==exact_record['coordinates']['sha256'];exact=np.load(exact_record['coordinates']['path'])['coordinates']
            caches=[(prepare_fidelity_pairs(y,res),prepare_fidelity_pairs(y[ca],res[ca])) for y in exact]
            for cycle in CYCLES:
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
            for cycle in CYCLES:
                parent=np.array([s['task'] for s in endpoints[f'p{pi}_wt',cycle]])
                mat[cycle]=np.array([[endpoints[f'p{pi}_s{pos+1}_{a}',cycle][ni]['task']-parent[ni] for a in names] for ni in range(4)])
            for cycle in CYCLES:
                selection=noise_selection(mat[4],mat[cycle],names);chosen=selection['cross_noise']['student_old_choice'];label=f'p{pi}_s{pos+1}_{chosen}'
                sites.append(dict(parent_index=pi,pdb_id=old['rows'][pi]['pdb_id'],position=pos,source_aa=source,cycles=cycle,role='stress' if old['rows'][pi]['pdb_id'].lower()=='2v66' else 'development',
                    selection=selection,selected_actual_geometry=[s['geometry'] for s in endpoints[label,cycle]],selected_C4_geometry=[s['geometry'] for s in endpoints[label,4]],
                    selected_actual_task=[s['task'] for s in endpoints[label,cycle]]))
    write_json(root/f'score_{index}.json',dict(complete=True,structures=structures,sites=sites,wt_gt=wt_gt))


def collect_native_budget(root):
    lock=verify_native_budget(root);structures=[];sites=[];wt_gt=[];timings=[]
    for i in range(4):
        s=load(root/f'score_{i}.json');r=load(root/f'worker_{i}/report.json');assert s['complete'] and r['complete']
        structures+=s['structures'];sites+=s['sites'];wt_gt+=s['wt_gt']
        for pi in lock['assignments'][i]:
            setup=next(p['seconds'] for p in r['parent_setup'] if p['parent_index']==pi)
            for cycle in CYCLES:
                rs=[x for x in r['records'] if x['parent_index']==pi and x['cycles']==cycle];assert len(rs)==77
                sums={k:sum(x['timing'][k] for x in rs) for k in rs[0]['timing']}
                timings.append(dict(parent_index=pi,pdb_id=lock['prior_lock']['rows'][pi]['pdb_id'],cycles=cycle,sequences=77,
                                    model_load_seconds=r['model_load_seconds'],shared_setup_seconds=setup,resident_screen_seconds=sums['total_seconds']+setup,
                                    first_use_screen_seconds=sums['total_seconds']+setup+r['model_load_seconds'],**sums))
    assert len(structures)==8316 and len(sites)==108
    write_json(root/'report.json',dict(complete=True,structures=structures,sites=sites,wt_gt=wt_gt,timings=timings,model_promoted=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--mode',required=True);p.add_argument('--index',type=int,default=0);a=p.parse_args()
    if a.mode=='prepare':prepare_native_budget(a.root)
    elif a.mode=='infer':infer_native_budget(a.root,a.index)
    elif a.mode=='score':score_native_budget(a.root,a.index)
    elif a.mode=='collect':collect_native_budget(a.root)
    else:raise ValueError(a.mode)
