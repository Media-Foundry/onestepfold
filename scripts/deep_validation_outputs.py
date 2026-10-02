"""Gated S1 refinement, native functional checks, timing and blockwise capture."""
import argparse,gzip,json,time
from pathlib import Path
import numpy as np
import torch
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.factor_student_data import FactorTeacherStore
from fastglycan.factor_student import factor_geometry_penalties
from fastglycan.factor_memorization import response_nmse
from fastglycan.deep_response_student import DeepResponseStudent
from fastglycan.models.soft_sequence_chart import native_sequence_features,device_tree
from fastglycan.models.differentiable_mini import prepare_atom_pairs,diffusion_from_conditioning,full_recycle_pairformer
from fastglycan.hybrid_proposals import identity_noise
from fastglycan.functional_response_rank import pack_conditioning
from fastglycan.adapter_supervision import build_adapter_supervision
from run_deep_validation_v2 import gpu_guard,site_tensors,predict_site
import run_global_response_rank as scoring


def load_deep_checkpoint(item):
    p=Path(item['path']);assert sha256(p)==item['sha256'];packet=torch.load(p,map_location='cuda',weights_only=False)
    net=DeepResponseStudent(**packet['job']['architecture']).cuda();net.load_state_dict(packet['state_dict']);return net,packet


def refine_deep_model(root,jobid):
    runtime=gpu_guard();lock=rt.load_json(root/'lock.json');job=rt.load_json(root/'jobs'/f'{jobid}.json');out=root/'runs'/jobid;out.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    store=FactorTeacherStore(Path(lock['teachers']),training_only=True);net,packet=load_deep_checkpoint(job['checkpoint']);optimizer=torch.optim.AdamW(net.parameters(),lr=job['lr'],weight_decay=1e-4,eps=1e-8)
    runner=rt.runner_setup(out/'work');runner.configs.dtype='fp32';model=runner.model.eval().requires_grad_(False);rng=np.random.default_rng(232501);cache={};records=[];checked=set();nfe=0
    def forbid(*args):raise AssertionError('C4 forbidden in functional refinement')
    hook=model.pairformer_stack.register_forward_pre_hook(forbid)
    for step in range(1024):
        pi,pos=job['train_sites'][int(rng.integers(len(job['train_sites'])))];row=store.rows[pi];choices=[a for a in store.lock['aa'] if a!=row['sequence'][pos]];aa=choices[int(rng.integers(19))];ni=int(rng.integers(2));item=store.load(pi,pos,aa)
        if pi not in cache:cache[pi]=tuple(t.cuda() for t in store.load(pi)['conditioning'])
        wt=cache[pi];target=tuple(t.cuda() for t in item['conditioning']);optimizer.zero_grad(set_to_none=True);pred=net(wt[1],wt[2],pos,store.lock['aa'].index(row['sequence'][pos]),[store.lock['aa'].index(aa)])[0]
        latent=response_nmse(pred[None],(target[2]-wt[2])[None]).mean();loss=latent;parts={}
        if job['functional']:
            native,atoms=native_sequence_features(item['sequence']);inv=item['inventory'];assert np.array_equal(atoms.atom_name,inv['atom_names']) and np.array_equal(atoms.bonds.as_array(),inv['bonds'])
            f=prepare_atom_pairs(model.relative_position_encoding.generate_relp(device_tree(native,'cuda')));noise=identity_noise(atoms,store.lock['seeds'][ni],device='cuda');teacher=torch.tensor(item['coordinates'][1,ni],device='cuda')
            if pi not in checked:
                with torch.no_grad():replay=diffusion_from_conditioning(model,f,noise,pack_conditioning((wt[0],target[1],target[2])),steps=1).squeeze(0)
                assert torch.equal(replay,teacher);nfe+=1;checked.add(pi)
            x=diffusion_from_conditioning(model,f,noise,pack_conditioning((wt[0],target[1],wt[2]+pred)),steps=1).squeeze(0);nfe+=1
            coord=(x-teacher).square().mean();ca=torch.tensor(np.flatnonzero(inv['atom_names']=='CA'),device='cuda');ij=torch.triu_indices(len(ca),len(ca),3,device='cuda')
            dist=(torch.linalg.vector_norm(x[ca[ij[0]]]-x[ca[ij[1]]],dim=-1)-torch.linalg.vector_norm(teacher[ca[ij[0]]]-teacher[ca[ij[1]]],dim=-1)).square().mean()
            labels=build_adapter_supervision(dict(inv,coordinates=item['coordinates'][1,ni],mask=np.ones(len(x),bool)),inv['bonds'],item['sequence']);clash,chirality=factor_geometry_penalties(x,labels)
            loss=loss+.25*coord+.25*dist+.01*clash+.1*chirality;parts=dict(coordinate=float(coord),distance=float(dist),clash=float(clash),chirality=float(chirality))
        loss.backward();gn=torch.nn.utils.clip_grad_norm_(net.parameters(),1.,error_if_nonfinite=True);optimizer.step();records.append(dict(step=step+1,parent_index=pi,position=pos,aa=aa,noise_index=ni,latent=float(latent),loss=float(loss),gradient_norm=float(gn),**parts))
        if (step+1)%64==0:write_json(out/'report.json',dict(complete=False,job=job,records=records,s1_calls=nfe,c4_calls=0))
    hook.remove();cp=out/'checkpoint_1024.pt';torch.save(dict(state_dict=net.state_dict(),optimizer=optimizer.state_dict(),job=dict(job,architecture=packet['job']['architecture']),step=1024),cp)
    write_json(out/'report.json',dict(complete=True,job=job,runtime=runtime,records=records,s1_calls=nfe,c4_calls=0,history=[dict(step=1024,checkpoint=str(cp),checkpoint_sha256=sha256(cp))],seconds=time.monotonic()-start))


class StressArchive:
    """Read-only old 6UFE-92 packet adapter; exact/baseline axes explicitly checked."""
    def __init__(self,base):
        self.base=Path(base);self.spatial=self.base/'spatial_response_rank_v1_20261002';self.lock=rt.load_json(self.spatial/'lock.json')
        self.owner={pi:wi for wi,ps in enumerate(self.lock['assignments']) for pi in ps};self.rows={r['index']:r for r in self.lock['rows']};self.checked={}
        self.states=self.base/'functional_response_rank_v1_20261002'
        self.hashes={x['path']:x['sha256'] for x in self.lock['conditioning_manifest']}
    def load(self,pi,pos=None,aa=None):
        row=self.rows[pi];label=f'p{pi}_wt' if pos is None or aa==row['sequence'][pos] else f'p{pi}_s{pos+1}_{aa}';wi=self.owner[pi]
        state=self.states/f'worker_{wi}/{label}_conditioning.pt';assert sha256(state)==self.hashes[str(state.relative_to(self.states))]
        packet=torch.load(state,map_location='cpu',weights_only=False);inv=dict(np.load(self.spatial/f'worker_{wi}/{label}_inventory.npz'));xyz=np.load(self.spatial/f'worker_{wi}/{label}_coordinates.npz')
        seq=row['sequence'] if pos is None else row['sequence'][:pos]+aa+row['sequence'][pos+1:];assert packet['sequence']==seq
        if pos is None:coords=xyz['coordinates']
        else:
            arms=list(xyz['arms']);coords=xyz['coordinates'][[arms.index('exact'),arms.index('baseline')]]
        return dict(label=label,sequence=seq,conditioning=tuple(packet['conditioning']),inventory=inv,coordinates=coords)


def decode_deep_panel(root,panel,index):
    runtime=gpu_guard();outroot=root/'functional'/panel;lock=rt.load_json(outroot/'lock.json');store=StressArchive(root.parent) if panel=='stress' else FactorTeacherStore(Path(lock['teachers']));out=outroot/f'worker_{index}';out.mkdir(exist_ok=False);start=time.monotonic()
    runner=rt.runner_setup(out/'work');runner.configs.dtype='fp32';model=runner.model.eval().requires_grad_(False);nets=[load_deep_checkpoint(x)[0].eval().requires_grad_(False) for x in lock['checkpoints']];counts=dict(nfe=0,c4=0,replay=0)
    def forbid(*args):counts['c4']+=1;raise AssertionError('C4 forbidden')
    hooks=[model.pairformer_stack.register_forward_pre_hook(forbid),model.diffusion_module.register_forward_hook(lambda *a:counts.__setitem__('nfe',counts['nfe']+1))]
    def features(item):
        native,atoms=native_sequence_features(item['sequence']);inv=item['inventory'];assert np.array_equal(atoms.atom_name,inv['atom_names']) and np.array_equal(atoms.res_id,inv['residue_ids']) and np.array_equal(atoms.bonds.as_array(),inv['bonds']) and np.array_equal(native['ref_pos'].numpy(),inv['reference'])
        np.savez_compressed(out/f'{item["label"]}_inventory.npz',**inv)
        return prepare_atom_pairs(model.relative_position_encoding.generate_relp(device_tree(native,'cuda'))),atoms
    def decode(f,a,c):return np.stack([diffusion_from_conditioning(model,f,identity_noise(a,seed,device='cuda'),pack_conditioning(c),steps=1).squeeze(0).cpu().numpy() for seed in lock['seeds']])
    report=dict(complete=False,parents=[],runtime=runtime,lock_sha256=sha256(outroot/'lock.json'))
    with torch.no_grad():
        for pi in lock['assignments'][index]:
            row=lock['rows'][pi];wi=store.load(pi);wt=tuple(t.cuda() for t in wi['conditioning']);f,a=features(wi);x=decode(f,a,wt);assert np.array_equal(x,wi['coordinates']);np.savez_compressed(out/f'p{pi}_wt_coordinates.npz',coordinates=x);sites=[]
            for pos in row['positions']:
                ids=[j for j,aa in enumerate(lock['aa']) if aa!=row['sequence'][pos]];preds=[net(wt[1],wt[2],pos,lock['aa'].index(row['sequence'][pos]),ids) for net in nets];site=dict(position=pos,mutants=[])
                for ai,j in enumerate(ids):
                    item=store.load(pi,pos,lock['aa'][j]);f,a=features(item);c=tuple(t.cuda() for t in item['conditioning']);delta=c[2].double()-wt[2].double();u,s,v=torch.linalg.svd(delta.permute(2,0,1),full_matrices=False);oracle=(wt[2].double()+((u[:,:,:32]*s[:,None,:32])@v[:,:32]).permute(1,2,0)).float()
                    coords=[decode(f,a,c),decode(f,a,(wt[0],c[1],c[2]))];assert np.array_equal(coords[0],item['coordinates'][0]) and np.array_equal(coords[1],item['coordinates'][1]);counts['replay']+=2
                    coords += [decode(f,a,(wt[0],c[1],z)) for z in [wt[2],oracle,*[wt[2]+p[ai] for p in preds]]]
                    path=out/f'{item["label"]}_coordinates.npz';np.savez_compressed(path,coordinates=np.stack(coords),arms=lock['arms'],seeds=lock['seeds']);site['mutants'].append(dict(aa=lock['aa'][j],label=item['label'],coordinate_sha256=sha256(path)));report.update(active=item['label'],counts=dict(counts));write_json(out/'report.json',report)
                sites.append(site)
            report['parents'].append(dict(parent_index=pi,sites=sites))
    for h in hooks:h.remove()
    report.update(complete=True,counts=counts,seconds=time.monotonic()-start);write_json(out/'report.json',report)


def collect_deep_panel(root,panel):
    out=root/'functional'/panel;lock=rt.load_json(out/'lock.json');sites=[]
    for i in range(6):
        with gzip.open(out/f'scorer_{i}/report.json.gz','rt') as f:r=json.load(f)
        assert r['complete'];sites+=r['sites']
    summary={}
    for arm in lock['arms']:
        rows=[r for s in sites for r in s['outputs'] if r['arm']==arm and not r['is_wt']];rank=[r for s in sites for r in s['ranking'] if r['arm']==arm and r['reference']=='exact' and not r['includes_wt']];local=np.array([r['fidelity']['local_ca_rmsd_global_frame'] for r in rows])
        summary[arm]=dict(instances=len(rows),spearman=float(np.mean([r['spearman'] for r in rank])) if rank else 1.,top1=sum(r['top1_match'] for r in rank) if rank else len(sites)*2,rankings=len(sites)*2,regret=float(np.mean([r['top1_regret'] for r in rank])) if rank else 0.,local_mean=float(local.mean()),local_p95=float(np.quantile(local,.95)),local_p99=float(np.quantile(local,.99)),local_max=float(local.max()),local_over_1a=int((local>1).sum()),new_geometry_vs_baseline=sum(r['new_compression_chemistry_failure'] for r in rows),geometry_pass=sum(r['geometry']['zero_severe_strict_checked_chirality'] for r in rows))
    with gzip.open(out/'report.json.gz','wt') as f:json.dump(dict(complete=True,summary=summary,sites=sites,oracle_target_s=True),f,allow_nan=False)
    write_json(out/'summary.json',dict(complete=True,summary=summary,oracle_target_s=True,deployment_accepted=False))


def native_response_diagnostic(root,mode):
    """Fresh hard features for measured C4; optional H capture, never train teachers."""
    runtime=gpu_guard();lock=rt.load_json(root/'lock.json');out=root/mode;out.mkdir(exist_ok=False);store=FactorTeacherStore(Path(lock['teachers']),training_only=True);runner=rt.runner_setup(out/'work');runner.configs.dtype='fp32';model=runner.model.eval().requires_grad_(False)
    torch.serialization.add_safe_globals([argparse.Namespace]);from protenix.data.esm.compute_esm import load_esm_model
    esm,alphabet=load_esm_model('esm2-3b',local_esm_dir=runner.configs.load_checkpoint_dir);esm.eval().requires_grad_(False);seq=store.rows[3]['sequence'];pos=36;records=[];captured=[];stage_inputs=[];handles=[];wttrace=None
    if mode=='blockwise':
        blocks=[m for m in model.pairformer_stack.modules() if type(m).__name__=='PairformerBlock'];assert len(blocks)==16
        for index,block in enumerate(blocks):
            if (index+1)%4==0:handles.append(block.register_forward_hook(lambda m,args,result:captured.append(tuple(x.detach().cpu().clone() for x in result))))
        handles.append(model.pairformer_stack.register_forward_pre_hook(lambda m,args:stage_inputs.append(tuple(x.detach().cpu().clone() for x in args[:2]))))
    with torch.no_grad():
        order=[seq[pos]]+[a for a in lock['aa'] if a!=seq[pos]]
        for aa in order:
            item=store.load(3,None if aa==seq[pos] else pos,aa);torch.cuda.synchronize();start=time.monotonic();native,atoms=native_sequence_features(item['sequence']);f=model.relative_position_encoding.generate_relp(device_tree(native,'cuda'));tokens=alphabet.get_batch_converter()([('hard',item['sequence'])])[2].cuda();f['esm_token_embedding']=esm(tokens,repr_layers=[esm.num_layers],return_contacts=False)['representations'][esm.num_layers][0,1:-1];f=prepare_atom_pairs(f);torch.cuda.synchronize();feature_time=time.monotonic()-start
            captured.clear();stage_inputs.clear();start=time.monotonic();c=full_recycle_pairformer(model,f,N_cycle=4,inplace_safe=False,mc_dropout=False);torch.cuda.synchronize();cold=time.monotonic()-start
            assert all(torch.equal(x.cpu(),y) for x,y in zip(c,item['conditioning']));row=dict(aa=aa,feature_esm_seconds=feature_time,c4_cold_seconds=cold,matched_replay=True)
            if mode=='blockwise':
                assert len(captured)==16 and len(stage_inputs)==4
                path=out/f'{aa}_boundaries.pt';torch.save(dict(sequence=item['sequence'],boundaries=captured,recycle_inputs=stage_inputs,s_inputs=c[0].cpu()),path);row['path']=str(path);row['sha256']=sha256(path)
                if wttrace is None:wttrace=list(captured)
                else:
                    evidence=[]
                    for j,(a,b) in enumerate(zip(captured,wttrace)):
                        ds=a[0].double()-b[0].double();dz=a[1].double()-b[1].double();sigma=torch.linalg.svdvals(dz.cuda().permute(2,0,1));evidence.append(dict(boundary=j+1,s_energy=float(ds.square().sum()),z_energy=float(dz.square().sum()),spatial_r32_residual=float(sigma[:,32:].square().sum()/sigma.square().sum())))
                    row['response']=evidence
            else:
                for _ in range(1):full_recycle_pairformer(model,f,N_cycle=4,inplace_safe=False,mc_dropout=False)
                times=[]
                for _ in range(3):
                    torch.cuda.synchronize();start=time.monotonic();full_recycle_pairformer(model,f,N_cycle=4,inplace_safe=False,mc_dropout=False);torch.cuda.synchronize();times.append(time.monotonic()-start)
                row['c4_seconds']=times
            records.append(row);write_json(out/'report.json',dict(complete=False,runtime=runtime,records=records))
        if mode=='timing':
            spec=rt.load_json(root/'selected.json');net,_=load_deep_checkpoint(spec['checkpoints'][0]);net.eval().requires_grad_(False);wt=tuple(t.cuda() for t in store.load(3)['conditioning']);times=[];expand=[]
            from fastglycan.factor_student import expand_pair_factors
            for rep in range(13):
                torch.cuda.synchronize();start=time.monotonic();uv=net.factors(wt[1],wt[2],pos,lock['aa'].index(seq[pos]),list(range(20)));torch.cuda.synchronize();t=time.monotonic()-start;start=time.monotonic();pred=expand_pair_factors(*uv);torch.cuda.synchronize();e=time.monotonic()-start
                if rep>=3:times.append(t);expand.append(e)
            one=float(np.median(records[0]['c4_seconds']));response=float(np.median(np.array(times)+expand));cost=sum(np.median(r['c4_seconds']) for r in records)
            timing=dict(factor_seconds=times,expansion_seconds=expand,one_wt_c4_seconds=one,sum20_c4_seconds=float(cost),response_seconds=response,response_over_c4=response/one,desired=response<.25*one,acceptable=response<one,conditional_speedup=float(cost/(one+response)),oracle_target_s_cost_not_included=True)
        else:timing=None
    for h in handles:h.remove()
    write_json(out/'report.json',dict(complete=True,runtime=runtime,records=records,timing=timing,training=False,blocks_captured=16 if mode=='blockwise' else 0))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--mode',choices=['refine','decode','score','collect','timing','blockwise'],required=True);p.add_argument('--job');p.add_argument('--panel',default='main');p.add_argument('--index',type=int,default=0);a=p.parse_args()
    if a.mode=='refine':refine_deep_model(a.root,a.job)
    elif a.mode=='decode':decode_deep_panel(a.root,a.panel,a.index)
    elif a.mode=='score':
        scoring.ARMS=tuple(rt.load_json(a.root/'functional'/a.panel/'lock.json')['arms']);scoring.score_global_response_rank(a.root/'functional'/a.panel,a.index)
    elif a.mode=='collect':collect_deep_panel(a.root,a.panel)
    else:native_response_diagnostic(a.root,a.mode)
