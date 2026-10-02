"""Information-path interventions from frozen hard conditioning, zero C4 calls."""
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
from fastglycan.conditioning_swaps import ARMS,swap_conditioning,DecoderFeatureTrace
from fastglycan.functional_response_rank import pack_conditioning,ranking_fidelity,prepare_fidelity_pairs,response_structure_metrics,response_geometry
from fastglycan.adapter_supervision import build_adapter_supervision
from fastglycan.backbone_sequence_task import backbone_target_pairs,backbone_target_loss


def prepare_conditioning_swaps(root):
    prior=root.parent/'functional_response_rank_v1_20261002';old=rt.load_json(prior/'lock.json')
    assert rt.load_json(prior/'controller_execution.json')['complete'] and not (root/'lock.json').exists()
    manifest=rt.load_json(prior/'conditioning_manifest.json');assert manifest['count']==960
    for f in manifest['files']:assert sha256(prior/f['path'])==f['sha256'],f['path']
    for path,h in old['weights_sha256'].items():assert sha256(Path(path))==h,path
    files=[]
    for p in prior.glob('worker_*/*_inventory.npz'):files.append(dict(path=str(p.relative_to(prior)),sha256=sha256(p)))
    for p in prior.glob('worker_*/*_coordinates.npz'):files.append(dict(path=str(p.relative_to(prior)),sha256=sha256(p)))
    assert len(files)==1920
    write_json(root/'lock.json',dict(schema='conditioning_swaps_v1',prior=str(prior),prior_lock_sha256=sha256(prior/'lock.json'),
        rows=old['rows'],assignments=old['assignments'],gt=old['gt'],aa=old['aa'],seeds=old['seeds'],arms=list(ARMS),
        weights_sha256=old['weights_sha256'],conditioning_manifest=manifest['files'],input_files=files,
        code_hashes={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.md','.json']},
        expected_c4=0,expected_esm_calls=0,expected_nfe=11520,expected_unique_outputs=11420,
        scope='WT/target neural-state swaps; chemistry always native target; no prediction head or global SVD',training=False))


def run_conditioning_swaps(root,index):
    lock=rt.load_json(root/'lock.json');prior=Path(lock['prior']);torch.set_num_threads(1);start=time.monotonic()
    for path,h in lock['code_hashes'].items():assert sha256(Path(path))==h,path
    out=root/f'worker_{index}';out.mkdir(exist_ok=False);report=dict(complete=False,worker=index,parents=[],stage='load',lock_sha256=sha256(root/'lock.json'))
    def save():write_json(out/'report.json',report)
    save();runner=rt.runner_setup(out/'work');runner.configs.dtype='fp32';model=runner.model.eval().requires_grad_(False)
    counts=dict(recycle=0,nfe=0,hard_rebuild=0,exact_replay=0,wt_identity_arms=0);timings=[];reads=set()
    def forbidden(*args):counts['recycle']+=1;raise AssertionError('C4 must not execute in cached swap experiment')
    hooks=[model.pairformer_stack.register_forward_pre_hook(forbidden),model.diffusion_module.register_forward_hook(lambda *a:counts.__setitem__('nfe',counts['nfe']+1))]
    hashes={f['path']:f['sha256'] for f in lock['conditioning_manifest']+lock['input_files']}
    report['runtime']=dict(torch=torch.__version__,hip=torch.version.hip,device=torch.cuda.get_device_name(0))
    import inspect,protenix.model.modules.diffusion as diffusion_source
    report['native_diffusion_source']=dict(path=inspect.getfile(diffusion_source),sha256=sha256(Path(inspect.getfile(diffusion_source))))
    def load(label,seq):
        prefix=f'worker_{index}/{label}';paths={k:prior/f'{prefix}_{k}' for k in ['conditioning.pt','inventory.npz','coordinates.npz']}
        for p in paths.values():assert sha256(p)==hashes[str(p.relative_to(prior))],p
        packet=torch.load(paths['conditioning.pt'],map_location='cpu',weights_only=False);assert packet['sequence']==seq
        c=tuple(v.cuda() for v in packet['conditioning']);assert all(v.dtype==torch.float32 and torch.isfinite(v).all() for v in c)
        inv=dict(np.load(paths['inventory.npz']));native,atoms=native_sequence_features(seq)
        for k,a in [('atom_names',atoms.atom_name),('residue_ids',atoms.res_id),('chain_ids',atoms.chain_id),('bonds',atoms.bonds.as_array())]:assert np.array_equal(inv[k],a),k
        assert np.array_equal(inv['reference'],native['ref_pos'].numpy())
        f=DecoderFeatureTrace(prepare_atom_pairs(model.relative_position_encoding.generate_relp(device_tree(native,'cuda'))));counts['hard_rebuild']+=1
        shutil.copy2(paths['inventory.npz'],out/f'{label}_inventory.npz')
        xyz=np.load(paths['coordinates.npz'])['coordinates'];exact=xyz if label.endswith('_wt') else xyz[0]
        return c,f,atoms,exact
    def decode(f,atoms,c):
        packed=pack_conditioning(c);t=time.monotonic()
        result=np.stack([diffusion_from_conditioning(model,f,identity_noise(atoms,seed,device='cuda'),packed,steps=1).squeeze(0).cpu().numpy() for seed in lock['seeds']])
        timings.append(time.monotonic()-t);reads.update(f.reads);return result
    with torch.no_grad():
        for pi in lock['assignments'][index]:
            row=lock['rows'][pi];seq=row['sequence'];report['stage']=f'parent_{pi}';save()
            wt,wf,wa,oldwt=load(f'p{pi}_wt',seq);wt_outputs=[]
            for arm in ARMS:
                result=decode(wf,wa,swap_conditioning(wt,wt,row['positions'][0],arm));assert np.array_equal(result,oldwt),'WT arm replay'
                wt_outputs.append(result);counts['wt_identity_arms']+=1
            np.savez_compressed(out/f'p{pi}_wt_coordinates.npz',coordinates=np.stack(wt_outputs),arms=ARMS,seeds=lock['seeds']);counts['exact_replay']+=1
            sites=[]
            for pos in row['positions']:
                site=dict(position=pos,wt_index=lock['aa'].index(seq[pos]),mutants=[])
                for ai,aa in enumerate(lock['aa']):
                    if aa==seq[pos]:continue
                    label=f'p{pi}_s{pos+1}_{aa}';target_seq=seq[:pos]+aa+seq[pos+1:];target,f,atoms,old=load(label,target_seq)
                    outputs=[]
                    for arm in ARMS:outputs.append(decode(f,atoms,swap_conditioning(wt,target,pos,arm)))
                    assert np.array_equal(outputs[0],old),'archive Exact replay'
                    counts['exact_replay']+=1
                    path=out/f'{label}_coordinates.npz';np.savez_compressed(path,coordinates=np.stack(outputs),arms=ARMS,seeds=lock['seeds'])
                    site['mutants'].append(dict(aa=aa,label=label,coordinate_sha256=sha256(path),exact_replay=True))
                    report.update(active=label,counts=dict(counts));save()
                sites.append(site)
            report['parents'].append(dict(parent_index=pi,sites=sites));save()
    for h in hooks:h.remove()
    n=len(lock['assignments'][index]);assert counts==dict(recycle=0,nfe=n*1152,hard_rebuild=n*96,exact_replay=n*96,wt_identity_arms=n*6)
    allowed={'relp','ref_pos','ref_charge','ref_mask','ref_atom_name_chars','ref_element','atom_to_token_idx','d_lm','v_lm','pad_info'}
    assert reads==allowed,reads
    report.update(complete=True,stage='complete',counts=counts,decoder_feature_reads=sorted(reads),decode_two_noise_seconds=timings,
        seconds=time.monotonic()-start,peak_allocated_bytes=torch.cuda.max_memory_allocated());save()


def score_conditioning_swaps(root,index):
    torch.set_num_threads(1);lock=rt.load_json(root/'lock.json');out=root/f'worker_{index}';worker=rt.load_json(out/'report.json');assert worker['complete'];sites=[];start=time.monotonic()
    for parent in worker['parents']:
        pi=parent['parent_index'];row=lock['rows'][pi];gtinfo=lock['gt'][str(pi)];assert sha256(Path(gtinfo['path']))==gtinfo['sha256']
        gt=dict(np.load(gtinfo['path']));ca=gt['atom_names']=='CA';gty=gt['coordinates'][ca];observed=gt['mask'][ca];pairs,dist=backbone_target_pairs(gty,observed)
        for site in parent['sites']:
            pos=site['position'];wi=site['wt_index'];local=(observed & (np.linalg.norm(gty-gty[pos],axis=1)<8)) if observed[pos] else np.zeros(len(gty),bool);local|=abs(np.arange(len(gty))-pos)<=2
            tasks=np.empty((6,2,20));outputs=[];response=[]
            wtinv=dict(np.load(out/f'p{pi}_wt_inventory.npz'))
            # Use explicit indexing to keep [noise,residue,xyz] ordering.
            wtxyz=np.load(out/f'p{pi}_wt_coordinates.npz')['coordinates'][0][:,wtinv['atom_names']=='CA'].astype(np.float64)
            ii,jj=np.triu_indices(len(gty),3);wd=np.linalg.norm(wtxyz[:,ii]-wtxyz[:,jj],axis=-1)
            for ai,aa in enumerate(lock['aa']):
                label=f'p{pi}_wt' if ai==wi else f'p{pi}_s{pos+1}_{aa}'
                path=out/f'{label}_coordinates.npz'
                if ai!=wi:assert sha256(path)==next(m['coordinate_sha256'] for m in site['mutants'] if m['aa']==aa)
                inv=dict(np.load(out/f'{label}_inventory.npz'));co=np.load(path)['coordinates'];ca=np.flatnonzero(inv['atom_names']=='CA');res=inv['residue_ids']
                assert np.array_equal(res[ca],np.arange(1,len(gty)+1))
                mapping=dict(inv,coordinates=co[0,0],mask=np.ones(len(res),bool));labels=build_adapter_supervision(mapping,inv['bonds'],str(inv['sequence']))
                if ai!=wi:
                    dc=co[:,:,ca];response.append(np.linalg.norm(dc[:,:,ii].astype(float)-dc[:,:,jj],axis=-1)-wd[None])
                for ni,seed in enumerate(lock['seeds']):
                    exact=co[0,ni];cache=(prepare_fidelity_pairs(exact,res),prepare_fidelity_pairs(exact[ca],res[ca]));refgeom=response_geometry(exact,labels)
                    for ki,arm in enumerate(ARMS):
                        x=co[ki,ni];tasks[ki,ni,ai]=float(backbone_target_loss(torch.tensor(x,dtype=torch.float64),ca,pairs,dist));geom=response_geometry(x,labels)
                        outputs.append(dict(aa=aa,is_wt=ai==wi,noise=seed,arm=arm,task=float(tasks[ki,ni,ai]),
                            fidelity=response_structure_metrics(x,exact,ca,local,cache),geometry=geom,
                            severe_delta=geom['severe_pairs']-refgeom['severe_pairs'],chirality_delta=geom['checked_chirality_wrong']-refgeom['checked_chirality_wrong'],
                            newly_fails_chemistry=refgeom['zero_severe_strict_checked_chirality'] and not geom['zero_severe_strict_checked_chirality']))
            rankings=[];response=np.array(response);scale=[]
            for ki,arm in enumerate(ARMS[1:],1):
                for ni,seed in enumerate(lock['seeds']):
                    for included in [False,True]:
                        ids=np.arange(20) if included else np.delete(np.arange(20),wi)
                        rankings.append(dict(arm=arm,noise=seed,includes_wt=included,**ranking_fidelity(tasks[0,ni,ids],tasks[ki,ni,ids])))
                    true=response[:,0,ni];pred=response[:,ki,ni];ct=true-true.mean(0);cp=pred-pred.mean(0)
                    scale.append(dict(arm=arm,noise=seed,exact_response_rms=float(np.sqrt(np.mean(true**2))),
                        relative_response_l2_error=float(np.linalg.norm(pred-true)/np.linalg.norm(true)) if np.linalg.norm(true)>1e-12 else None,
                        centered_AA_response_l2_error=float(np.linalg.norm(cp-ct)/np.linalg.norm(ct)) if np.linalg.norm(ct)>1e-12 else None))
            result=dict(parent_index=pi,pdb_id=row['pdb_id'],position=pos,ranking=rankings,outputs=outputs,response_scale=scale)
            write_json(out/f'p{pi}_s{pos+1}_scores.json',result);sites.append(result);write_json(out/'score_status.json',dict(complete=False,sites=len(sites)))
    write_json(out/'score_report.json',dict(complete=True,sites=sites,seconds=time.monotonic()-start,lock_sha256=sha256(root/'lock.json')))
    write_json(out/'score_status.json',dict(complete=True,sites=len(sites)))


def collect_conditioning_swaps(root):
    lock=rt.load_json(root/'lock.json');sites=[];workers=[]
    for i in range(8):
        w=rt.load_json(root/f'worker_{i}/report.json');s=rt.load_json(root/f'worker_{i}/score_report.json');assert w['complete'] and s['complete'] and s['lock_sha256']==sha256(root/'lock.json');sites+=s['sites'];workers.append(w)
    assert len(sites)==50;summary={};boot=np.random.default_rng(226101).integers(0,10,(10000,10))
    def aggregate(values):
        parents=np.array([np.mean([v for p,v in values if p==i and v is not None]) if any(p==i and v is not None for p,v in values) else np.nan for i in range(10)])
        if not np.isfinite(parents).all():return dict(mean=None,protein_bootstrap95=None,per_protein=[float(x) if np.isfinite(x) else None for x in parents])
        return dict(mean=float(parents.mean()),protein_bootstrap95=np.quantile(parents[boot].mean(1),[.025,.975]).tolist(),per_protein=parents.tolist())
    for arm in ARMS:
        rows=[(s['parent_index'],r) for s in sites for r in s['outputs'] if r['arm']==arm and not r['is_wt']]
        quality={key:aggregate([(p,r['fidelity'][key]) for p,r in rows]) for key in rows[0][1]['fidelity']};ranking={}
        for included in [False,True]:
            rs=[(s['parent_index'],r) for s in sites for r in s['ranking'] if r['arm']==arm and r['includes_wt']==included]
            if rs:ranking[str(included)]={key:aggregate([(p,r[key]) for p,r in rs]) for key in ['spearman','top1_match','top1_regret','normalized_regret','top3_recall','top5_recall','task_mae']}
        summary[arm]=dict(quality=quality,ranking=ranking,severe_total=sum(r['geometry']['severe_pairs'] for _,r in rows),
            zero_severe_strict_checked_chirality=sum(r['geometry']['zero_severe_strict_checked_chirality'] for _,r in rows),
            newly_fails_chemistry=sum(r['newly_fails_chemistry'] for _,r in rows),severe_increased_instances=sum(r['severe_delta']>0 for _,r in rows),
            chirality_increased_instances=sum(r['chirality_delta']>0 for _,r in rows),instances=len(rows))
    contrasts={}
    for a,b in [('global_only','wt_trunk'),('local_only','wt_trunk'),('exact','wt_trunk'),('wt_trunk','chem_only'),('exact','target_trunk_only'),('target_trunk_only','chem_only')]:
        result={}
        for key in ['spearman','top1_match','top1_regret']:
            values=[]
            for s in sites:
                for seed in lock['seeds']:
                    def value(arm):return (1. if key!='top1_regret' else 0.) if arm=='exact' else next(r[key] for r in s['ranking'] if r['arm']==arm and r['noise']==seed and not r['includes_wt'])
                    av,bv=value(a),value(b);values.append((s['parent_index'],None if av is None or bv is None else av-bv))
            result[key]=aggregate(values)
        contrasts[a+' minus '+b]=result
    report=dict(complete=True,lock_sha256=sha256(root/'lock.json'),summary=summary,paired_contrasts=contrasts,sites=sites,workers=workers,training=False,deployment_accepted=False)
    with gzip.open(root/'report.json.gz','wt') as f:json.dump(report,f,allow_nan=False)
    write_json(root/'summary.json',{k:v for k,v in report.items() if k not in ['sites','workers']})
    lines=['# Conditioning information-path swaps','','Exact is a model reference, not experimental truth. Chemistry stays target in all arms.','',
        '|Arm|AA fidelity lDDT|Local CA RMSD|19-AA Spearman|Top1 match|Top1 regret|Chemistry pass/1900|','|---|---:|---:|---:|---:|---:|---:|']
    for arm,r in summary.items():
        q=r['quality'];a=r['ranking'].get('False');rho=a['spearman']['mean'] if a else 1.;match=a['top1_match']['mean'] if a else 1.;regret=a['top1_regret']['mean'] if a else 0.
        lines.append(f'|{arm}|{q["all_atom_lddt"]["mean"]:.6f}|{q["local_ca_rmsd_global_frame"]["mean"]:.6f}|{rho:.6f}|{match:.3f}|{regret:.6f}|{r["zero_severe_strict_checked_chirality"]}|')
    (root/'report.md').write_text('\n'.join(lines)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True,type=Path);p.add_argument('--mode',required=True,choices=['prepare','run','score','collect']);p.add_argument('--index',type=int,default=0);a=p.parse_args()
    if a.mode=='prepare':prepare_conditioning_swaps(a.root)
    elif a.mode=='run':run_conditioning_swaps(a.root,a.index)
    elif a.mode=='score':score_conditioning_swaps(a.root,a.index)
    else:collect_conditioning_swaps(a.root)
