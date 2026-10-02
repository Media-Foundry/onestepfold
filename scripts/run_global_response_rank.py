"""Full s/z functional-rank curves from frozen hard endpoints, WT decoder inputs."""
import argparse
import gzip
import json
import shutil
import time
from pathlib import Path
import numpy as np
import torch
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.models.soft_sequence_chart import native_sequence_features,device_tree
from fastglycan.models.differentiable_mini import prepare_atom_pairs,diffusion_from_conditioning
from fastglycan.hybrid_proposals import identity_noise
from fastglycan.conditioning_swaps import DecoderFeatureTrace
from fastglycan.global_response_rank import GlobalResponseBasis,GLOBAL_VARIANTS,GLOBAL_RANKS
from fastglycan.functional_response_rank import pack_conditioning,ranking_fidelity,prepare_fidelity_pairs,response_structure_metrics,response_geometry
from fastglycan.adapter_supervision import build_adapter_supervision
from fastglycan.backbone_sequence_task import backbone_target_pairs,backbone_target_loss

ARMS=('exact','baseline')+tuple(f'{v}_k{k}' for v in GLOBAL_VARIANTS for k in GLOBAL_RANKS)


def prepare_global_response_rank(root):
    prior=root.parent/'conditioning_swaps_v1_20261002';old=rt.load_json(prior/'lock.json');states=Path(old['prior'])
    assert rt.load_json(prior/'controller_execution.json')['complete'] and not (root/'lock.json').exists()
    for item in old['conditioning_manifest']:assert sha256(states/item['path'])==item['sha256']
    for p,h in old['weights_sha256'].items():assert sha256(Path(p))==h
    files=[dict(path=str(p.relative_to(prior)),sha256=sha256(p)) for pattern in ['worker_*/*_inventory.npz','worker_*/*_coordinates.npz'] for p in prior.glob(pattern)];assert len(files)==1920
    scores=[[] for _ in range(32)];load=[0]*32;owner={pi:i for i,rows in enumerate(old['assignments']) for pi in rows}
    for row in sorted(old['rows'],key=lambda r:len(r['sequence']),reverse=True):
        for pos in row['positions']:
            i=min(range(32),key=lambda x:load[x]);scores[i].append(dict(parent_index=row['index'],position=pos,worker=owner[row['index']]));load[i]+=len(row['sequence'])**2
    write_json(root/'lock.json',dict(schema='global_response_rank_v1',prior=str(prior),states=str(states),prior_lock_sha256=sha256(prior/'lock.json'),
        rows=old['rows'],assignments=old['assignments'],gt=old['gt'],aa=old['aa'],seeds=old['seeds'],arms=ARMS,variants=GLOBAL_VARIANTS,ranks=GLOBAL_RANKS,
        conditioning_manifest=old['conditioning_manifest'],input_files=files,weights_sha256=old['weights_sha256'],score_assignments=scores,
        code_hashes={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.md','.json']},
        expected_nfe=95020,expected_c4=0,full_rank_input_tolerance=1e-5,full_rank_coordinate_tolerance=1e-3,
        scope='oracle full s/z reconstruction; WT s_inputs + native target chemistry; exact and uncompressed baseline references',training=False))


def run_global_response_rank(root,index):
    lock=rt.load_json(root/'lock.json');prior=Path(lock['prior']);states=Path(lock['states']);torch.set_num_threads(1);start=time.monotonic()
    for p,h in lock['code_hashes'].items():assert sha256(Path(p))==h,p
    out=root/f'worker_{index}';out.mkdir(exist_ok=False);report=dict(complete=False,worker=index,parents=[],stage='load',lock_sha256=sha256(root/'lock.json'))
    def save():write_json(out/'report.json',report)
    save();runner=rt.runner_setup(out/'work');runner.configs.dtype='fp32';model=runner.model.eval().requires_grad_(False)
    counts=dict(recycle=0,nfe=0,hard_rebuild=0,exact_replay=0,baseline_replay=0,deduplicated_calls=0);reads=set()
    def forbidden(*args):counts['recycle']+=1;raise AssertionError('C4 forbidden')
    hooks=[model.pairformer_stack.register_forward_pre_hook(forbidden),model.diffusion_module.register_forward_hook(lambda *a:counts.__setitem__('nfe',counts['nfe']+1))]
    hashes={f['path']:f['sha256'] for f in lock['conditioning_manifest']+lock['input_files']}
    def load_state(label,seq):
        p=states/f'worker_{index}/{label}_conditioning.pt';assert sha256(p)==hashes[str(p.relative_to(states))]
        packet=torch.load(p,map_location='cpu',weights_only=False);assert packet['sequence']==seq
        return tuple(t.cuda() for t in packet['conditioning'])
    def chemical_input(label,seq):
        invpath=prior/f'worker_{index}/{label}_inventory.npz';xyzpath=prior/f'worker_{index}/{label}_coordinates.npz'
        for p in [invpath,xyzpath]:assert sha256(p)==hashes[str(p.relative_to(prior))]
        inv=dict(np.load(invpath));native,atoms=native_sequence_features(seq)
        for key,values in [('atom_names',atoms.atom_name),('residue_ids',atoms.res_id),('chain_ids',atoms.chain_id),('bonds',atoms.bonds.as_array()),('reference',native['ref_pos'].numpy())]:assert np.array_equal(inv[key],values),key
        shutil.copy2(invpath,out/f'{label}_inventory.npz');counts['hard_rebuild']+=1
        f=DecoderFeatureTrace(prepare_atom_pairs(model.relative_position_encoding.generate_relp(device_tree(native,'cuda'))))
        return f,atoms,np.load(xyzpath)['coordinates']
    def decode(f,atoms,c):
        packed=pack_conditioning(c)
        result=np.stack([diffusion_from_conditioning(model,f,identity_noise(atoms,seed,device='cuda'),packed,steps=1).squeeze(0).cpu().numpy() for seed in lock['seeds']]);reads.update(f.reads);return result
    report['runtime']=dict(torch=torch.__version__,hip=torch.version.hip,device=torch.cuda.get_device_name(0))
    with torch.no_grad():
        for pi in lock['assignments'][index]:
            row=lock['rows'][pi];seq=row['sequence'];wt=load_state(f'p{pi}_wt',seq);wf,wa,wold=chemical_input(f'p{pi}_wt',seq);wxyz=decode(wf,wa,wt)
            assert np.array_equal(wxyz,wold[0]) and np.array_equal(wxyz,wold[3]);counts['exact_replay']+=1;counts['baseline_replay']+=1
            np.savez_compressed(out/f'p{pi}_wt_coordinates.npz',coordinates=wxyz,seeds=lock['seeds']);sites=[]
            for pos in row['positions']:
                ids=[i for i,a in enumerate(lock['aa']) if a!=seq[pos]];target=[]
                for ai in ids:
                    aa=lock['aa'][ai];target.append(load_state(f'p{pi}_s{pos+1}_{aa}',seq[:pos]+aa+seq[pos+1:]))
                basis=GlobalResponseBasis(wt[1],wt[2],torch.stack([c[1] for c in target]),torch.stack([c[2] for c in target]))
                evidence=basis.evidence();np.savez_compressed(out/f'p{pi}_s{pos+1}_grams.npz',s=np.array(evidence['centered_gram']['s']),z=np.array(evidence['centered_gram']['z']))
                site=dict(position=pos,wt_index=lock['aa'].index(seq[pos]),nonwt_indices=ids,evidence=evidence,mutants=[])
                report['stage']=f'parent_{pi}_site_{pos+1}';save()
                for mi,ai in enumerate(ids):
                    aa=lock['aa'][ai];label=f'p{pi}_s{pos+1}_{aa}';f,atoms,old=chemical_input(label,seq[:pos]+aa+seq[pos+1:]);c=target[mi]
                    exact=decode(f,atoms,c);baseline=decode(f,atoms,(wt[0],c[1],c[2]));assert np.array_equal(exact,old[0]) and np.array_equal(baseline,old[3]),'reference replay'
                    counts['exact_replay']+=1;counts['baseline_replay']+=1;outputs=[exact,baseline];full=[];zero_pair=None;zero_xyz=None
                    for variant in GLOBAL_VARIANTS:
                        for k in GLOBAL_RANKS:
                            s,z=basis.reconstruct(mi,variant,k)
                            if k==0 and variant in ['balanced','separate_both']:
                                assert all(torch.equal(x,y) for x,y in zip((s,z),zero_pair)),'K0 equivalence';xyz=zero_xyz;counts['deduplicated_calls']+=2
                            else:xyz=decode(f,atoms,(wt[0],s,z))
                            if k==0 and variant=='raw':zero_pair=(s,z);zero_xyz=xyz
                            if k==18:
                                input_error=max(float((s-c[1]).abs().max()),float((z-c[2]).abs().max()));coordinate_error=float(np.max(np.abs(xyz-baseline)))
                                assert input_error<=lock['full_rank_input_tolerance'] and coordinate_error<=lock['full_rank_coordinate_tolerance'],(variant,input_error,coordinate_error)
                                full.append(dict(variant=variant,input_max_error=input_error,coordinate_max_error=coordinate_error))
                            outputs.append(xyz)
                    path=out/f'{label}_coordinates.npz';np.savez_compressed(path,coordinates=np.stack(outputs),arms=ARMS,seeds=lock['seeds'])
                    site['mutants'].append(dict(aa=aa,label=label,coordinate_sha256=sha256(path),full_rank_checks=full));report.update(active=label,counts=dict(counts));save()
                sites.append(site);del basis,target
            report['parents'].append(dict(parent_index=pi,sites=sites));save()
    for h in hooks:h.remove()
    n=len(lock['assignments'][index]);assert counts==dict(recycle=0,nfe=n*9502,hard_rebuild=n*96,exact_replay=n*96,baseline_replay=n*96,deduplicated_calls=n*380),counts
    report.update(complete=True,stage='complete',counts=counts,decoder_feature_reads=sorted(reads),seconds=time.monotonic()-start,peak_allocated_bytes=torch.cuda.max_memory_allocated());save()


def score_global_response_rank(root,index):
    torch.set_num_threads(1);lock=rt.load_json(root/'lock.json');out=root/f'scorer_{index}';out.mkdir(exist_ok=False);sites=[];start=time.monotonic()
    for job in lock['score_assignments'][index]:
        pi,pos,wi=job['parent_index'],job['position'],job['worker'];work=root/f'worker_{wi}';w=rt.load_json(work/'report.json');assert w['complete']
        stored=next(s for p in w['parents'] if p['parent_index']==pi for s in p['sites'] if s['position']==pos)
        row=lock['rows'][pi];wtindex=lock['aa'].index(row['sequence'][pos]);gti=lock['gt'][str(pi)];assert sha256(Path(gti['path']))==gti['sha256'];gt=dict(np.load(gti['path']))
        gca=gt['atom_names']=='CA';y=gt['coordinates'][gca];obs=gt['mask'][gca];pairs,dist=backbone_target_pairs(y,obs)
        local=(obs & (np.linalg.norm(y-y[pos],axis=1)<8)) if obs[pos] else np.zeros(len(y),bool);local|=abs(np.arange(len(y))-pos)<=2
        tasks=np.empty((len(ARMS),2,20));rows=[]
        for ai,aa in enumerate(lock['aa']):
            label=f'p{pi}_wt' if ai==wtindex else f'p{pi}_s{pos+1}_{aa}';path=work/f'{label}_coordinates.npz'
            if ai!=wtindex:assert sha256(path)==next(m['coordinate_sha256'] for m in stored['mutants'] if m['aa']==aa)
            co=np.load(path)['coordinates']
            if ai==wtindex:co=np.repeat(co[None],len(ARMS),axis=0)
            inv=dict(np.load(work/f'{label}_inventory.npz'));ca=np.flatnonzero(inv['atom_names']=='CA');res=inv['residue_ids'];assert np.array_equal(res[ca],np.arange(1,len(y)+1))
            labels=build_adapter_supervision(dict(inv,coordinates=co[0,0],mask=np.ones(len(res),bool)),inv['bonds'],str(inv['sequence']))
            for ni,seed in enumerate(lock['seeds']):
                references=[co[0,ni],co[1,ni]];caches=[(prepare_fidelity_pairs(ref,res),prepare_fidelity_pairs(ref[ca],res[ca])) for ref in references]
                geometry_ref=[response_geometry(ref,labels) for ref in references]
                for ki,arm in enumerate(ARMS):
                    x=co[ki,ni];tasks[ki,ni,ai]=float(backbone_target_loss(torch.tensor(x,dtype=torch.float64),ca,pairs,dist));geo=response_geometry(x,labels)
                    rows.append(dict(aa=aa,is_wt=ai==wtindex,noise=seed,arm=arm,task=float(tasks[ki,ni,ai]),geometry=geo,
                        fidelity=response_structure_metrics(x,references[0],ca,local,caches[0]),
                        compression_fidelity=response_structure_metrics(x,references[1],ca,local,caches[1]),
                        severe_delta=geo['severe_pairs']-geometry_ref[0]['severe_pairs'],chirality_delta=geo['checked_chirality_wrong']-geometry_ref[0]['checked_chirality_wrong'],
                        newly_fails_chemistry=geometry_ref[0]['zero_severe_strict_checked_chirality'] and not geo['zero_severe_strict_checked_chirality'],
                        new_compression_chemistry_failure=geometry_ref[1]['zero_severe_strict_checked_chirality'] and not geo['zero_severe_strict_checked_chirality']))
        rankings=[]
        for ki,arm in enumerate(ARMS[1:],1):
            for ni,seed in enumerate(lock['seeds']):
                for refi,refname in [(0,'exact'),(1,'baseline')]:
                    for included in [False,True]:
                        ids=np.arange(20) if included else np.delete(np.arange(20),wtindex)
                        rankings.append(dict(arm=arm,noise=seed,reference=refname,includes_wt=included,**ranking_fidelity(tasks[refi,ni,ids],tasks[ki,ni,ids])))
        result=dict(parent_index=pi,pdb_id=row['pdb_id'],position=pos,ranking=rankings,outputs=rows)
        write_json(work/f'p{pi}_s{pos+1}_scores.json',result);sites.append(result);write_json(out/'status.json',dict(complete=False,sites=len(sites)))
    with gzip.open(out/'report.json.gz','wt') as f:json.dump(dict(complete=True,sites=sites,seconds=time.monotonic()-start,lock_sha256=sha256(root/'lock.json')),f,allow_nan=False)
    write_json(out/'status.json',dict(complete=True,sites=len(sites),seconds=time.monotonic()-start))


def collect_global_response_rank(root):
    lock=rt.load_json(root/'lock.json');sites=[];workers=[rt.load_json(root/f'worker_{i}/report.json') for i in range(8)];assert all(w['complete'] for w in workers)
    for i in range(32):
        with gzip.open(root/f'scorer_{i}/report.json.gz','rt') as f:r=json.load(f)
        assert r['complete'] and r['lock_sha256']==sha256(root/'lock.json');sites+=r['sites']
    assert len(sites)==50 and len({(s['parent_index'],s['position']) for s in sites})==50
    boot=np.random.default_rng(227101).integers(0,10,(10000,10));summary={}
    def aggregate(values):
        parent=[np.mean([v for p,v in values if p==i and v is not None]) if any(p==i and v is not None for p,v in values) else None for i in range(10)]
        if any(v is None for v in parent):return dict(mean=None,protein_bootstrap95=None,per_protein=parent)
        parent=np.array(parent);return dict(mean=float(parent.mean()),protein_bootstrap95=np.quantile(parent[boot].mean(1),[.025,.975]).tolist(),per_protein=parent.tolist())
    for arm in ARMS:
        rows=[(s['parent_index'],r) for s in sites for r in s['outputs'] if r['arm']==arm and not r['is_wt']]
        q={group:{key:aggregate([(p,r[group][key]) for p,r in rows]) for key in rows[0][1][group]} for group in ['fidelity','compression_fidelity']}
        ranks={}
        for ref in ['exact','baseline']:
            ranks[ref]={}
            for included in [False,True]:
                rs=[(s['parent_index'],r) for s in sites for r in s['ranking'] if r['arm']==arm and r['reference']==ref and r['includes_wt']==included]
                if rs:ranks[ref][str(included)]={key:aggregate([(p,r[key]) for p,r in rs]) for key in ['spearman','top1_match','top1_regret','normalized_regret','top3_recall','top5_recall','task_mae']}
        summary[arm]=dict(**q,ranking=ranks,severe_total=sum(r['geometry']['severe_pairs'] for _,r in rows),
            zero_severe_strict_checked_chirality=sum(r['geometry']['zero_severe_strict_checked_chirality'] for _,r in rows),
            newly_fails_chemistry=sum(r['newly_fails_chemistry'] for _,r in rows),new_compression_chemistry_failure=sum(r['new_compression_chemistry_failure'] for _,r in rows),
            local_over_1a=sum(r['fidelity']['local_ca_rmsd_global_frame']>1 for _,r in rows),
            compression_local_over_1a=sum(r['compression_fidelity']['local_ca_rmsd_global_frame']>1 for _,r in rows),
            worst_local_rmsd=max(r['fidelity']['local_ca_rmsd_global_frame'] for _,r in rows),instances=len(rows))
    report=dict(complete=True,lock_sha256=sha256(root/'lock.json'),summary=summary,sites=sites,workers=workers,training=False,deployment_accepted=False)
    with gzip.open(root/'report.json.gz','wt') as f:json.dump(report,f,allow_nan=False)
    write_json(root/'summary.json',{k:v for k,v in report.items() if k not in ['sites','workers']})
    lines=['# Full s/z functional rank with WT s_inputs','','Entire target s/z reconstructed; mean and coefficients are in-sample oracle quantities.','',
        '|Variant|K|AA fidelity|Local CA RMSD|Spearman to Exact|Top1 to Exact|Top1 to baseline|New geometry fails|','|---|---:|---:|---:|---:|---:|---:|---:|']
    for variant in GLOBAL_VARIANTS:
        for k in GLOBAL_RANKS:
            r=summary[f'{variant}_k{k}'];e=r['ranking']['exact']['False'];b=r['ranking']['baseline']['False']
            lines.append(f'|{variant}|{k}|{r["fidelity"]["all_atom_lddt"]["mean"]:.6f}|{r["fidelity"]["local_ca_rmsd_global_frame"]["mean"]:.6f}|{e["spearman"]["mean"]:.6f}|{e["top1_match"]["mean"]:.3f}|{b["top1_match"]["mean"]:.3f}|{r["newly_fails_chemistry"]}|')
    (root/'report.md').write_text('\n'.join(lines)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True,type=Path);p.add_argument('--mode',required=True,choices=['prepare','run','score','collect']);p.add_argument('--index',type=int,default=0);a=p.parse_args()
    if a.mode=='prepare':prepare_global_response_rank(a.root)
    elif a.mode=='run':run_global_response_rank(a.root,a.index)
    elif a.mode=='score':score_global_response_rank(a.root,a.index)
    else:collect_global_response_rank(a.root)
