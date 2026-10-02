"""Frozen final-checkpoint factor-only evaluation, with oracle s explicit."""
import argparse,gzip,hashlib,time,shutil
from pathlib import Path
import numpy as np
import torch
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.factor_student import FactorStudent,expand_pair_factors
from fastglycan.factor_student_data import FactorTeacherStore
from fastglycan.models.soft_sequence_chart import native_sequence_features,device_tree
from fastglycan.models.differentiable_mini import prepare_atom_pairs,diffusion_from_conditioning
from fastglycan.hybrid_proposals import identity_noise
from fastglycan.functional_response_rank import pack_conditioning
import run_global_response_rank as scoring

ARMS=('exact','baseline','wt_z','oracle_r32','student_0','student_1')


def prepare_factor_evaluation(root):
    student=rt.load_json(root/'student_lock.json');teacher=rt.load_json(root/'teacher_lock.json');out=root/'evaluation';out.mkdir(exist_ok=False);scores=[[] for _ in range(8)];load=[0]*8
    ck=[]
    for i in range(2):
        report=rt.load_json(root/f'train_{i}/report.json');assert report['complete'];p=root/f'train_{i}/final.pt';assert sha256(p)==report['checkpoint_sha256'];ck.append(dict(path=str(p),sha256=sha256(p)))
    for wi,parents in enumerate(student['evaluation_assignments']):
        for pi in parents:
            for pos in teacher['rows'][pi]['positions']:
                si=min(range(8),key=lambda x:load[x]);scores[si].append(dict(parent_index=pi,position=pos,worker=wi));load[si]+=len(teacher['rows'][pi]['sequence'])**2
    write_json(out/'lock.json',dict(teacher,arms=ARMS,assignments=student['evaluation_assignments'],score_assignments=scores,checkpoints=ck,parent_root=str(root),student_lock_sha256=sha256(root/'student_lock.json'),code_hashes=student['code_hashes'],evaluation_parents=student['evaluation_parents'],expected_nfe=5496,expected_c4=0))


def evaluate_factor_student(root,index):
    outroot=root/'evaluation';lock=rt.load_json(outroot/'lock.json');torch.set_num_threads(1);data=FactorTeacherStore(root);out=outroot/f'worker_{index}';out.mkdir(exist_ok=False);start=time.monotonic()
    for p,h in lock['code_hashes'].items():assert sha256(Path(p))==h
    runner=rt.runner_setup(out/'work');runner.configs.dtype='fp32';decoder=runner.model.eval().requires_grad_(False);nets=[]
    for item in lock['checkpoints']:
        assert sha256(Path(item['path']))==item['sha256'];p=torch.load(item['path'],map_location='cpu',weights_only=False);net=FactorStudent(**p['architecture']).cuda().eval();net.load_state_dict(p['state_dict']);nets.append(net)
    counts=dict(nfe=0,recycle=0,exact_replay=0,baseline_replay=0);report=dict(complete=False,parents=[],lock_sha256=sha256(outroot/'lock.json'));feature_cache={}
    def save():write_json(out/'report.json',report)
    def forbid(*args):counts['recycle']+=1;raise AssertionError('C4 forbidden')
    hooks=[decoder.pairformer_stack.register_forward_pre_hook(forbid),decoder.diffusion_module.register_forward_hook(lambda *a:counts.__setitem__('nfe',counts['nfe']+1))]
    def features(item):
        native,atoms=native_sequence_features(item['sequence']);inv=item['inventory'];assert np.array_equal(atoms.atom_name,inv['atom_names']) and np.array_equal(atoms.bonds.as_array(),inv['bonds']) and np.array_equal(native['ref_pos'].numpy(),inv['reference'])
        np.savez_compressed(out/f'{item["label"]}_inventory.npz',**inv)
        return prepare_atom_pairs(decoder.relative_position_encoding.generate_relp(device_tree(native,'cuda'))),atoms
    def decode(f,atoms,c):return np.stack([diffusion_from_conditioning(decoder,f,identity_noise(atoms,n,device='cuda'),pack_conditioning(c),steps=1).squeeze(0).cpu().numpy() for n in lock['seeds']])
    with torch.no_grad():
        for pi in lock['assignments'][index]:
            row=lock['rows'][pi];wi=lock['aa'];wtitem=data.load(pi);wt=tuple(x.cuda() for x in wtitem['conditioning']);f,atoms=features(wtitem);x=decode(f,atoms,wt);assert np.array_equal(x,wtitem['coordinates']);counts['exact_replay']+=1;counts['baseline_replay']+=1;np.savez_compressed(out/f'p{pi}_wt_coordinates.npz',coordinates=x);sites=[]
            for pos in row['positions']:
                factors=[];timings=[];parity=[]
                for net in nets:
                    torch.cuda.synchronize();t=time.monotonic();uv=net(wt[1],wt[2],pos,wi.index(row['sequence'][pos]),list(range(20)));torch.cuda.synchronize();timings.append(time.monotonic()-t);factors.append(uv)
                    first=next(j for j,a in enumerate(wi) if a!=row['sequence'][pos]);single=expand_pair_factors(*net(wt[1],wt[2],pos,wi.index(row['sequence'][pos]),[first]))[0];batch=expand_pair_factors(uv[0][first:first+1],uv[1][first:first+1])[0];err=float((single-batch).abs().max());assert err<1e-4;parity.append(err)
                    assert torch.count_nonzero(uv[1][wi.index(row['sequence'][pos])])==0
                site=dict(position=pos,mutants=[],factor20_seconds=timings,batch_max_error=parity)
                for ai,a in enumerate(wi):
                    if a==row['sequence'][pos]:continue
                    item=data.load(pi,pos,a);f,atoms=features(item);c=tuple(x.cuda() for x in item['conditioning']);delta=c[2].double()-wt[2].double();u,s,v=torch.linalg.svd(delta.permute(2,0,1),full_matrices=False);r=32;oracle=(wt[2].double()+((u[:,:,:r]*s[:,None,:r])@v[:,:r]).permute(1,2,0)).float()
                    preds=[];expand_times=[]
                    for uv in factors:
                        torch.cuda.synchronize();t=time.monotonic();d=expand_pair_factors(uv[0][ai:ai+1],uv[1][ai:ai+1])[0];torch.cuda.synchronize();expand_times.append(time.monotonic()-t);preds.append(wt[2]+d)
                    coords=[decode(f,atoms,c),decode(f,atoms,(wt[0],c[1],c[2]))]
                    assert np.array_equal(coords[0],item['coordinates'][0]) and np.array_equal(coords[1],item['coordinates'][1]);counts['exact_replay']+=1;counts['baseline_replay']+=1
                    for z in [wt[2],oracle,*preds]:coords.append(decode(f,atoms,(wt[0],c[1],z)))
                    label=item['label'];p=out/f'{label}_coordinates.npz';np.savez_compressed(p,coordinates=np.stack(coords),arms=ARMS,seeds=lock['seeds']);den=float(delta.square().mean())
                    site['mutants'].append(dict(aa=a,label=label,coordinate_sha256=sha256(p),latent_nmse=[float((z.double()-c[2].double()).square().mean())/max(den,1e-6) for z in [wt[2],oracle,*preds]],expand_seconds=expand_times))
                    report.update(active=label,counts=dict(counts));save()
                sites.append(site)
            report['parents'].append(dict(parent_index=pi,sites=sites));save()
    for h in hooks:h.remove()
    n=len(lock['assignments'][index]);assert counts==dict(nfe=n*458,recycle=0,exact_replay=n*39,baseline_replay=n*39)
    report.update(complete=True,counts=counts,seconds=time.monotonic()-start,peak_allocated_bytes=torch.cuda.max_memory_allocated());save()


def collect_factor_evaluation(root):
    out=root/'evaluation';lock=rt.load_json(out/'lock.json');sites=[];workers=[rt.load_json(out/f'worker_{i}/report.json') for i in range(8)];assert all(w['complete'] for w in workers)
    for i in range(8):
        with gzip.open(out/f'scorer_{i}/report.json.gz','rt') as f:r=__import__('json').load(f)
        assert r['complete'];sites+=r['sites']
    assert len(sites)==24;summary={};rng=np.random.default_rng(230501)
    for role in ['train','validation']:
        parents=sorted({s['parent_index'] for s in sites if lock['rows'][s['parent_index']]['role']==role});boot=rng.integers(0,len(parents),(10000,len(parents)))
        def agg(values):
            per=[float(np.mean([v for p,v in values if p==pi])) for pi in parents];a=np.array(per);return dict(mean=float(a.mean()),per_protein=dict(zip(map(str,parents),per)),protein_bootstrap95=np.quantile(a[boot].mean(1),[.025,.975]).tolist())
        summary[role]={}
        for arm in ARMS:
            rows=[(s['parent_index'],r) for s in sites if s['parent_index'] in parents for r in s['outputs'] if r['arm']==arm and not r['is_wt']]
            ranking={}
            for ref in ['exact','baseline']:
                rk=[(s['parent_index'],r) for s in sites if s['parent_index'] in parents for r in s['ranking'] if r['arm']==arm and r['reference']==ref and not r['includes_wt']]
                if rk:ranking[ref]={k:agg([(p,r[k]) for p,r in rk]) for k in ['spearman','top1_match','top1_regret','top3_recall','top5_recall']}
            summary[role][arm]=dict(proteins=len(parents),instances=len(rows),ranking=ranking,local_mean=agg([(p,r['fidelity']['local_ca_rmsd_global_frame']) for p,r in rows]),aa_lddt=agg([(p,r['fidelity']['all_atom_lddt']) for p,r in rows]),local_over_1a=sum(r['fidelity']['local_ca_rmsd_global_frame']>1 for _,r in rows),local_max=max(r['fidelity']['local_ca_rmsd_global_frame'] for _,r in rows),geometry_pass=sum(r['geometry']['zero_severe_strict_checked_chirality'] for _,r in rows),new_geometry_vs_baseline=sum(r['new_compression_chemistry_failure'] for _,r in rows),new_geometry_vs_exact=sum(r['newly_fails_chemistry'] for _,r in rows))
    report=dict(complete=True,summary=summary,sites=sites,workers=workers,oracle_target_s=True,deployment_accepted=False)
    with gzip.open(out/'report.json.gz','wt') as f:__import__('json').dump(report,f,allow_nan=False)
    write_json(out/'summary.json',dict(complete=True,summary=summary,oracle_target_s=True,deployment_accepted=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--mode',choices=['prepare','run','score','collect'],required=True);p.add_argument('--index',type=int,default=0);a=p.parse_args();scoring.ARMS=ARMS
    if a.mode=='prepare':prepare_factor_evaluation(a.root)
    elif a.mode=='run':evaluate_factor_student(a.root,a.index)
    elif a.mode=='score':scoring.score_global_response_rank(a.root/'evaluation',a.index)
    else:collect_factor_evaluation(a.root)
