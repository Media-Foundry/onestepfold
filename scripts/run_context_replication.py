"""Frozen repeated-environment teachers and direct-score learning curve."""
import argparse,json,time
from pathlib import Path
import numpy as np
import torch
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.context_replication import AA,NOISES,replication_jobs,native_sequences,task_cases
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.hip_device_policy import guarded_hip_runtime
from fastglycan.task_readout import reference_node_features
from fastglycan.multicontext_response import noise_selection
from run_task_readout import make_task_model,task_prediction


def prepare_replication(root):
    assert not (root/'lock.json').exists()
    selected=rt.load_json(root/'candidate_selection.json')
    old=rt.load_json(root.parent/'factor_student_pilot_v1_20261002/teacher_lock.json')
    rows=selected['rows'];assert len(rows)==40
    assignments=[[] for _ in range(4)];loads=[0]*4
    for i,row in sorted(enumerate(rows),key=lambda x:len(x[1]['sequence']),reverse=True):
        worker=min(range(4),key=lambda k:loads[k]);assignments[worker].append(i);loads[worker]+=len(row['sequence'])**2
    gt={}
    for i,row in enumerate(rows):
        path=Path(row['mapping_path']);assert sha256(path)==row['mapping_sha256']
        gt[str(i)]=dict(path=str(path),sha256=sha256(path))
    lock=dict(schema='context_replication_v1',rows=rows,assignments=assignments,gt=gt,aa=AA,seeds=list(NOISES),
              weights_sha256=old['weights_sha256'],jobs=replication_jobs(selected),
              candidate_sha256=sha256(root/'candidate_selection.json'),
              expected=dict(unique_sequences=3080,c4=3120,recycle=12480,s1=12360,wt_replay=40,s1_replay=40),
              code_hashes={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ('.py','.md')})
    write_json(root/'lock.json',lock)


def verify_replication(root):
    lock=rt.load_json(root/'lock.json')
    assert sha256(root/'candidate_selection.json')==lock['candidate_sha256']
    for p,h in lock['code_hashes'].items():assert sha256(Path(p))==h,p
    return lock


def inventory_of(sequence,features,atoms):
    inv=dict(sequence=np.array(sequence),atom_names=atoms.atom_name,residue_ids=atoms.res_id,
             chain_ids=atoms.chain_id,reference=features['ref_pos'].cpu().numpy(),bonds=atoms.bonds.as_array())
    ca=np.flatnonzero(inv['atom_names']=='CA');n=len(atoms)
    assert np.array_equal(inv['residue_ids'][ca],np.arange(1,len(sequence)+1))
    assert np.isfinite(inv['reference']).all() and inv['reference'].shape==(n,3)
    assert inv['bonds'].ndim==2 and ((inv['bonds'][:,:2]>=0)&(inv['bonds'][:,:2]<n)).all()
    lookup={(int(r),str(a)):j for j,(r,a) in enumerate(zip(inv['residue_ids'],inv['atom_names']))};assert len(lookup)==n
    for i,aa in enumerate(sequence,1):
        groups=[]
        if aa!='G':groups.append(['CA','N','C','CB'])
        if aa in 'IT':groups.append(['CB','CA','CG1' if aa=='I' else 'OG1','CG2'])
        for names in groups:
            a,b,c,d=[inv['reference'][lookup[i,k]] for k in names]
            assert abs(np.dot(np.cross(b-a,c-a),d-a))>=1e-4
    return inv


def preflight_replication(root,index):
    from fastglycan.models.soft_sequence_chart import native_sequence_features
    torch.set_num_threads(1);lock=verify_replication(root);out=root/f'preflight_{index}';out.mkdir(exist_ok=False)
    report=dict(complete=False,records=[],errors=[],c4_calls=0,s1_calls=0);start=time.monotonic()
    for pi in lock['assignments'][index]:
        row=lock['rows'][pi];gt=dict(np.load(lock['gt'][str(pi)]['path']))
        for label,seq,pos,aa in native_sequences(row,pi):
            try:
                f,atoms=native_sequence_features(seq);inv=inventory_of(seq,f,atoms)
                if pos is None:
                    assert np.array_equal(inv['atom_names'],gt['atom_names'])
                    assert np.array_equal(inv['residue_ids'],gt['residue_ids'])
                path=out/f'{label}_inventory.npz';np.savez_compressed(path,**inv)
                report['records'].append(dict(label=label,sequence=seq,path=str(path),sha256=sha256(path),atoms=len(atoms)))
            except Exception as error:report['errors'].append(dict(label=label,error=repr(error)))
        report.update(seconds=time.monotonic()-start);write_json(out/'report.json',report)
    report.update(complete=not report['errors'],seconds=time.monotonic()-start);write_json(out/'report.json',report)
    assert report['complete'],report['errors']


def freeze_preflight(root):
    lock=verify_replication(root);items=[]
    for i in range(4):
        r=rt.load_json(root/f'preflight_{i}/report.json');assert r['complete'] and not r['errors'];items+=r['records']
    assert len(items)==3080 and len({x['label'] for x in items})==3080
    for x in items:assert sha256(Path(x['path']))==x['sha256']
    write_json(root/'native_manifest.json',dict(complete=True,records=items,lock_sha256=sha256(root/'lock.json')))


def teacher_replication(root,index):
    from fastglycan.models.soft_sequence_chart import native_sequence_features,device_tree
    from fastglycan.models.differentiable_mini import full_recycle_pairformer,prepare_atom_pairs,diffusion_from_conditioning
    from fastglycan.functional_response_rank import pack_conditioning
    from fastglycan.hybrid_proposals import identity_noise
    runtime=guarded_hip_runtime();lock=verify_replication(root)
    manifest=rt.load_json(root/'native_manifest.json');assert manifest['complete']
    native={x['label']:x for x in manifest['records']}
    for p,h in lock['weights_sha256'].items():assert sha256(Path(p))==h
    out=root/f'teacher_{index}';out.mkdir(exist_ok=False);start=time.monotonic()
    runner=rt.runner_setup(out/'work');runner.configs.dtype='fp32';model=runner.model.eval().requires_grad_(False)
    torch.serialization.add_safe_globals([argparse.Namespace])
    from protenix.data.esm.compute_esm import load_esm_model
    esm,alphabet=load_esm_model('esm2-3b',local_esm_dir=runner.configs.load_checkpoint_dir);esm.eval().requires_grad_(False)
    counts=dict(c4=0,recycle=0,s1=0,wt_replay=0,s1_replay=0)
    report=dict(complete=False,runtime=runtime,records=[],counts=counts,timings=[])
    hooks=[model.pairformer_stack.register_forward_hook(lambda *args:counts.__setitem__('recycle',counts['recycle']+1)),
           model.diffusion_module.register_forward_hook(lambda *args:counts.__setitem__('s1',counts['s1']+1))]
    def forward(label,seq):
        torch.cuda.synchronize();start=time.monotonic();raw,atoms=native_sequence_features(seq)
        actual=inventory_of(seq,raw,atoms);item=native[label];assert sha256(Path(item['path']))==item['sha256']
        archived=dict(np.load(item['path']))
        assert all(np.array_equal(actual[k],archived[k]) for k in actual)
        f=prepare_atom_pairs(model.relative_position_encoding.generate_relp(device_tree(raw,'cuda')))
        tokens=alphabet.get_batch_converter()([('hard',seq)])[2].cuda()
        f['esm_token_embedding']=esm(tokens,repr_layers=[esm.num_layers],return_contacts=False)['representations'][esm.num_layers][0,1:-1]
        torch.cuda.synchronize();features_time=time.monotonic()-start;start=time.monotonic()
        c=full_recycle_pairformer(model,f,N_cycle=4,inplace_safe=False,mc_dropout=False)
        torch.cuda.synchronize();counts['c4']+=1
        report['timings'].append(dict(label=label,features_esm_seconds=features_time,c4_seconds=time.monotonic()-start))
        assert all(t.dtype==torch.float32 and torch.isfinite(t).all() for t in c)
        return f,atoms,c
    def decode(f,atoms,c,seed):
        return diffusion_from_conditioning(model,f,identity_noise(atoms,seed,device='cuda'),pack_conditioning(c),steps=1).squeeze(0).cpu().numpy()
    with torch.no_grad():
        for pi in lock['assignments'][index]:
            for label,seq,pos,aa in native_sequences(lock['rows'][pi],pi):
                report.update(active=label,seconds=time.monotonic()-start);write_json(out/'report.json',report)
                f,atoms,c=forward(label,seq)
                if pos is None:
                    _,_,repeat=forward(label,seq);assert all(torch.equal(a,b) for a,b in zip(c,repeat));counts['wt_replay']+=1
                    del repeat
                    path=out/f'p{pi}_wt_conditioning.pt';torch.save(dict(sequence=seq,conditioning=[t.cpu() for t in c]),path)
                    conditioning=dict(path=str(path),sha256=sha256(path))
                else:conditioning=None
                co=np.stack([decode(f,atoms,c,seed) for seed in NOISES]);assert np.isfinite(co).all()
                if pos is None:
                    assert np.array_equal(decode(f,atoms,c,NOISES[0]),co[0]);counts['s1_replay']+=1
                path=out/f'{label}_coordinates.npz';np.savez_compressed(path,coordinates=co,seeds=NOISES)
                report['records'].append(dict(label=label,parent_index=pi,position=pos,aa=aa,conditioning=conditioning,
                                               coordinates=dict(path=str(path),sha256=sha256(path))))
            write_json(out/'report.json',report)
    for hook in hooks:hook.remove()
    n=len(lock['assignments'][index]);assert counts==dict(c4=78*n,recycle=312*n,s1=309*n,wt_replay=n,s1_replay=n)
    report.update(complete=True,seconds=time.monotonic()-start,peak_allocated_bytes=torch.cuda.max_memory_allocated());write_json(out/'report.json',report)


def score_replication(root,index):
    from fastglycan.adapter_supervision import build_adapter_supervision
    from fastglycan.functional_response_rank import response_geometry
    from fastglycan.backbone_sequence_task import backbone_target_pairs,backbone_target_loss
    torch.set_num_threads(1);lock=verify_replication(root);out=root/f'score_{index}';out.mkdir(exist_ok=False)
    native={x['label']:x for x in rt.load_json(root/'native_manifest.json')['records']}
    teacher=rt.load_json(root/f'teacher_{index}/report.json');assert teacher['complete']
    endpoints={};start=time.monotonic()
    for record in teacher['records']:
        label=record['label'];pi=record['parent_index'];item=native[label]
        assert sha256(Path(item['path']))==item['sha256']
        assert sha256(Path(record['coordinates']['path']))==record['coordinates']['sha256']
        inv=dict(np.load(item['path']));co=np.load(record['coordinates']['path'])['coordinates']
        gt=dict(np.load(lock['gt'][str(pi)]['path']));gca=gt['atom_names']=='CA'
        pairs,distances=backbone_target_pairs(gt['coordinates'][gca],gt['mask'][gca]);ca=np.flatnonzero(inv['atom_names']=='CA')
        labels=build_adapter_supervision(dict(inv,coordinates=co[0],mask=np.ones(co.shape[1],bool)),inv['bonds'],str(inv['sequence']))
        scores=[float(backbone_target_loss(torch.tensor(x,dtype=torch.float64),ca,pairs,distances)) for x in co]
        endpoints[label]=dict(task=scores,geometry=[response_geometry(x,labels) for x in co])
        if len(endpoints)%77==0:write_json(out/'status.json',dict(complete=False,endpoints=len(endpoints),seconds=time.monotonic()-start))
    cases=[]
    for pi in lock['assignments'][index]:cases+=task_cases(lock['rows'][pi],pi,endpoints)
    write_json(out/'report.json',dict(complete=True,endpoints=endpoints,cases=cases,seconds=time.monotonic()-start))


def collect_replication_labels(root):
    lock=verify_replication(root);cases=[];wt={};counts={k:0 for k in ('c4','recycle','s1','wt_replay','s1_replay')}
    for i in range(4):
        teacher=rt.load_json(root/f'teacher_{i}/report.json');score=rt.load_json(root/f'score_{i}/report.json')
        assert teacher['complete'] and score['complete'];cases+=score['cases']
        for k in counts:counts[k]+=teacher['counts'][k]
        for record in teacher['records']:
            if record['conditioning']:wt[str(record['parent_index'])]=record['conditioning']
    assert all(counts[k]==lock['expected'][k] for k in counts) and len(cases)==160 and len(wt)==40
    cases.sort(key=lambda c:(c['parent_index'],'ADLT'.index(c['source_aa'])))
    paths=[]
    def save(name,data):
        path=root/name;write_json(path,data);paths.append(path)
    save('evaluation_labels.json',dict(cases=cases))
    for size in (8,16,32):
        job=next(j for j in lock['jobs'] if j['size']==size)
        chosen=[next(c for c in cases if [c['parent_index'],c['position']]==site) for site in job['train_sites']]
        # Only old labels and legal metadata are serialized into training files.
        train=[{**{k:v for k,v in c.items() if k not in ('target_delta','wt_task','teacher_geometry')},'target_delta':c['target_delta'][:2]} for c in chosen]
        save(f'train_n{size}.json',dict(cases=train))
    write_json(root/'label_manifest.json',dict(complete=True,wt=wt,counts=counts,
                                              files={str(p):sha256(p) for p in paths},lock_sha256=sha256(root/'lock.json')))


def replication_inputs(root,lock,manifest,cases,device,allowed):
    data=[];cache={}
    for c in cases:
        pi=c['parent_index'];assert pi in allowed
        if pi not in cache:
            item=manifest['wt'][str(pi)];assert sha256(Path(item['path']))==item['sha256']
            packet=torch.load(item['path'],map_location='cpu',weights_only=False)
            assert packet['sequence']==lock['rows'][pi]['sequence']
            _,s,z=packet['conditioning'];cache[pi]=(s.to(device),z.to(device))
        info=lock['gt'][str(pi)];assert sha256(Path(info['path']))==info['sha256']
        gt=dict(np.load(info['path']));ca=gt['atom_names']=='CA'
        ref=reference_node_features(gt['coordinates'][ca],gt['mask'][ca],c['position'])
        s,z=cache[pi];data.append(dict(s=s,z=z,position=c['position'],wt=c['wt'],reference=torch.tensor(ref,device=device)))
    return data


def train_replication(root,jobid):
    lock=verify_replication(root);job=next(j for j in lock['jobs'] if j['id']==jobid)
    gpu=job['architecture']=='context';runtime=guarded_hip_runtime() if gpu else dict(device='cpu');device='cuda' if gpu else 'cpu';torch.set_num_threads(1)
    manifest=rt.load_json(root/'label_manifest.json');path=root/f'train_n{job["size"]}.json'
    assert manifest['complete'] and sha256(path)==manifest['files'][str(path)]
    cases=rt.load_json(path)['cases'];assert [[c['parent_index'],c['position']] for c in cases]==job['train_sites']
    assert all(c['role']=='train' and len(c['target_delta'])==2 for c in cases)
    data=replication_inputs(root,lock,manifest,cases,device,set(job['parents'])) if gpu else [None]*len(cases)
    ids=[torch.tensor([a for a in range(20) if a!=c['wt']],device=device) for c in cases]
    target=[torch.tensor(np.mean(c['target_delta'],axis=0)/job['scale'],device=device,dtype=torch.float32) for c in cases]
    torch.manual_seed(job['seed']);model=make_task_model(job['architecture']).to(device)
    optimizer=torch.optim.AdamW(model.parameters(),lr=job['lr'],weight_decay=job['weight_decay'],eps=1e-8)
    out=root/'runs'/jobid;out.mkdir(parents=True,exist_ok=False)
    torch.save(dict(step=0,state_dict=model.state_dict(),job=job),out/'initial.pt')
    start=time.monotonic();counts=[0]*len(cases)
    report=dict(complete=False,job=job,runtime=runtime,parameters=sum(p.numel() for p in model.parameters()),
                initial_sha256=sha256(out/'initial.pt'),history=[],trace=[],source_lock_sha256=sha256(root/'lock.json'),train_label_sha256=sha256(path))
    def snapshot(step):
        metrics=[]
        with torch.no_grad():
            for i,c in enumerate(cases):
                pred=task_prediction(model,job['architecture'],data[i],c['wt']);loss=(pred[ids[i]]-target[i][ids[i]]).square().mean()
                metrics.append(dict(parent_index=c['parent_index'],position=c['position'],normalized_mse=float(loss),predicted_delta=(pred*job['scale']).cpu().tolist()))
        row=dict(step=step,exposures=list(counts),sites=metrics,seconds=time.monotonic()-start)
        if step:
            cp=out/f'checkpoint_{step}.pt';torch.save(dict(step=step,exposures=counts,state_dict=model.state_dict(),optimizer=optimizer.state_dict(),job=job),cp)
            row.update(checkpoint=str(cp),sha256=sha256(cp))
        report['history'].append(row);write_json(out/'report.json',report)
    snapshot(0)
    for step in range(1,job['steps']+1):
        i=(step-1)%len(cases);optimizer.zero_grad(set_to_none=True)
        pred=task_prediction(model,job['architecture'],data[i],cases[i]['wt']);loss=(pred[ids[i]]-target[i][ids[i]]).square().mean()
        loss.backward();gn=torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True);optimizer.step();counts[i]+=1
        if step<=16 or step%640==0:
            report['trace'].append(dict(step=step,loss=float(loss.detach()),gradient_norm=float(gn),prediction_range=float((pred.max()-pred.min()).detach())))
            report.update(active_step=step,seconds=time.monotonic()-start);write_json(out/'report.json',report)
        if step in job['snapshots']:snapshot(step)
    assert counts==[1024]*len(cases)
    report.update(complete=True,context_exposures=counts,seconds=time.monotonic()-start,peak_allocated_bytes=torch.cuda.max_memory_allocated() if gpu else None)
    write_json(out/'report.json',report)


def evaluate_replication(root,index):
    runtime=guarded_hip_runtime();lock=verify_replication(root);manifest=rt.load_json(root/'label_manifest.json')
    for job in lock['jobs']:assert rt.load_json(root/'runs'/job['id']/'report.json')['complete']
    path=root/'evaluation_labels.json';assert sha256(path)==manifest['files'][str(path)];cases=rt.load_json(path)['cases']
    results=[]
    for ji,job in enumerate(lock['jobs']):
        if ji%4!=index:continue
        report=rt.load_json(root/'runs'/job['id']/'report.json')
        for step in sorted({32768,job['steps']}):
            snapshot=next(h for h in report['history'] if h['step']==step)
            cp=Path(snapshot['checkpoint']);assert sha256(cp)==snapshot['sha256'];packet=torch.load(cp,map_location='cpu',weights_only=False)
            net=make_task_model(job['architecture']).cuda().eval().requires_grad_(False);net.load_state_dict(packet['state_dict'])
            with torch.no_grad():
                for c in cases:
                    data=replication_inputs(root,lock,manifest,[c],'cuda',set(range(40)))[0] if job['architecture']=='context' else None
                    pred=task_prediction(net,job['architecture'],data,c['wt'])*job['scale'];assert torch.isfinite(pred).all() and pred[c['wt']]==0
                    raw=pred.cpu().numpy().astype(float);ids=[a for a in range(20) if a!=c['wt']];names=[AA[a] for a in ids]
                    selection=noise_selection(np.array(c['target_delta'])[:,ids],np.repeat(raw[None,ids],4,axis=0),names)
                    chosen=ids[np.argmin(raw[ids])];error=None
                    if [c['parent_index'],c['position']] in job['train_sites']:
                        old=next(s for s in snapshot['sites'] if (s['parent_index'],s['position'])==(c['parent_index'],c['position']))
                        error=float(np.max(abs(raw-np.array(old['predicted_delta']))));assert error<1e-5
                    elapsed=[]
                    if c is cases[0]:
                        for repeat in range(24):
                            torch.cuda.synchronize();begin=time.perf_counter();task_prediction(net,job['architecture'],data,c['wt']);torch.cuda.synchronize()
                            if repeat>=4:elapsed.append(time.perf_counter()-begin)
                    category='confirmation' if c['role']=='confirmation_candidate' else 'train' if c['parent_index'] in job['parents'] else 'other_train_pool'
                    results.append(dict(job=job['id'],step=step,category=category,parent_index=c['parent_index'],position=c['position'],source_aa=c['source_aa'],pdb_id=c['pdb_id'],
                                        predicted_delta=raw.tolist(),selection=selection,train_replay_error=error,selected_aa=AA[chosen],
                                        selected_teacher_geometry=[g[chosen] for g in c['teacher_geometry']],head_only_warm_latency_samples=elapsed))
                    del data
            del net
    write_json(root/f'evaluation_{index}.json',dict(complete=True,runtime=runtime,results=results,c4_calls=0,s1_calls=0))


def collect_replication(root):
    lock=verify_replication(root);results=[]
    for i in range(4):
        r=rt.load_json(root/f'evaluation_{i}.json');assert r['complete'];results+=r['results']
    expected=sum(len({32768,j['steps']}) for j in lock['jobs'])*160;assert len(results)==expected
    write_json(root/'report.json',dict(complete=True,results=results,deployment_accepted=False,structures_generated_by_student=0,oracle_target_s=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--mode',required=True);p.add_argument('--index',type=int);p.add_argument('--job')
    a=p.parse_args();modes={'prepare':prepare_replication,'freeze_preflight':freeze_preflight,'labels':collect_replication_labels,'collect':collect_replication}
    workers={'preflight':preflight_replication,'teacher':teacher_replication,'score':score_replication,'eval':evaluate_replication}
    if a.mode in modes:modes[a.mode](a.root)
    elif a.mode in workers:workers[a.mode](a.root,a.index)
    elif a.mode=='train':train_replication(a.root,a.job)
    else:raise ValueError(a.mode)
