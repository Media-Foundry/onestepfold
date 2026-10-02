"""Frozen local slice intervention; exact target conditioning outside the strips."""
import argparse
import hashlib
import json
import time
from pathlib import Path
import numpy as np
import torch
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.models.soft_sequence_chart import native_sequence_features, device_tree
from fastglycan.models.differentiable_mini import full_recycle_pairformer, prepare_atom_pairs, diffusion_from_conditioning
from fastglycan.hybrid_proposals import identity_noise
from fastglycan.functional_response_rank import (reconstruct_local_responses,local_conditioning_intervention,
    pack_conditioning,ranking_fidelity,prepare_fidelity_pairs,response_structure_metrics,response_geometry)
from fastglycan.adapter_supervision import build_adapter_supervision
from fastglycan.backbone_sequence_task import backbone_target_pairs, backbone_target_loss

AA='ACDEFGHIKLMNPQRSTVWY'
RANKS=[0,1,2,3,5,8,10,12,15,18]
SEEDS=[225001,225011]


def prepare_functional_response_rank(root):
    prior=root.parent/'hard_response_rank_v1_20261002'
    lock=rt.load_json(prior/'lock.json');report=rt.load_json(prior/'report.json')
    assert report['complete'] and not (root/'lock.json').exists()
    records={}
    for worker in report['workers']:
        for site in worker['records']:
            path=prior/f'worker_{worker["worker"]}'/site['endpoint_file']
            assert sha256(path)==site['endpoint_sha256']
            records[f'{site["parent_index"]}:{site["position_0based"]}']=dict(path=str(path),sha256=site['endpoint_sha256'],ledger=site['ledger'])
    gt={}
    for row in lock['rows']:
        path=Path(row['source_metadata']['chemistry_packet'])/'mapping.npz'
        m=dict(np.load(path));ca=m['atom_names']=='CA';assert ca.sum()==len(row['sequence'])
        gt[str(row['index'])]=dict(path=str(path),sha256=sha256(path))
        backbone_target_pairs(m['coordinates'][ca],m['mask'][ca])
    for p,h in lock['weights_sha256'].items():assert sha256(Path(p))==h
    write_json(root/'lock.json',dict(schema='functional_response_rank_v1',rows=lock['rows'],assignments=lock['assignments'],
        endpoints=records,gt=gt,weights_sha256=lock['weights_sha256'],prior_lock_sha256=sha256(prior/'lock.json'),
        prior_report_sha256=sha256(prior/'report.json'),ranks=RANKS,seeds=SEEDS,aa=AA,
        code_hashes={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.json','.md']},
        full_rank_coordinate_max_tolerance_angstrom=1e-3,full_rank_input_max_tolerance=1e-5,
        expected_c4=960,expected_nfe=21870,expected_unique_coordinate_predictions=20920,
        scope='conditional local strips only; exact hard target elsewhere; oracle in-sample projection',training=False))


def run_functional_response_rank(root,index):
    lock=rt.load_json(root/'lock.json');torch.set_num_threads(1)
    for p,h in lock['code_hashes'].items():assert sha256(Path(p))==h,p
    out=root/f'worker_{index}';out.mkdir(exist_ok=False)
    report=dict(complete=False,worker=index,stage='load',parents=[],lock_sha256=sha256(root/'lock.json'));start=time.monotonic()
    def save():write_json(out/'report.json',report)
    save();runner=rt.runner_setup(out/'work');runner.configs.dtype='fp32';model=runner.model.eval().requires_grad_(False)
    for p,h in lock['weights_sha256'].items():assert sha256(Path(p))==h,p
    torch.serialization.add_safe_globals([argparse.Namespace])
    from protenix.data.esm.compute_esm import load_esm_model
    esm,alphabet=load_esm_model('esm2-3b',local_esm_dir=runner.configs.load_checkpoint_dir);esm.eval().requires_grad_(False)
    counts=dict(c4=0,recycle=0,nfe=0,sham=0,endpoint_replay=0);timings=[]
    hooks=[model.pairformer_stack.register_forward_hook(lambda *a:counts.__setitem__('recycle',counts['recycle']+1)),
           model.diffusion_module.register_forward_hook(lambda *a:counts.__setitem__('nfe',counts['nfe']+1))]
    report['runtime']=dict(torch=torch.__version__,hip=torch.version.hip,device=torch.cuda.get_device_name(0),model_dtype=str(next(model.parameters()).dtype))
    def forward(sequence,label):
        torch.cuda.synchronize();t=time.monotonic();native,atoms=native_sequence_features(sequence)
        f=model.relative_position_encoding.generate_relp(device_tree(native,'cuda'))
        tokens=alphabet.get_batch_converter()([('hard',sequence)])[2].cuda()
        f['esm_token_embedding']=esm(tokens,repr_layers=[esm.num_layers],return_contacts=False)['representations'][esm.num_layers][0,1:-1]
        f=prepare_atom_pairs(f);torch.cuda.synchronize();feature_time=time.monotonic()-t;t=time.monotonic()
        c=full_recycle_pairformer(model,f,N_cycle=4,inplace_safe=False,mc_dropout=False)
        torch.cuda.synchronize();trunk_time=time.monotonic()-t;counts['c4']+=1
        torch.save(dict(sequence=sequence,conditioning=[v.cpu() for v in c]),out/f'{label}_conditioning.pt')
        inventory=dict(atom_names=atoms.atom_name,residue_ids=atoms.res_id,chain_ids=atoms.chain_id,
                       reference=f['ref_pos'].cpu().numpy(),bonds=atoms.bonds.as_array(),sequence=np.array(sequence))
        np.savez_compressed(out/f'{label}_inventory.npz',**inventory)
        timings.append(dict(sequence=label,features_esm_seconds=feature_time,c4_seconds=trunk_time))
        return f,atoms,c
    def replay(c,arrays,ai,pos,atoms,ledger):
        current=dict(s_site=c[1][pos].cpu().numpy(),z_row=c[2][pos].cpu().numpy(),z_col=c[2][:,pos].cpu().numpy(),s_inputs_site=c[0][pos].cpu().numpy())
        assert all(np.array_equal(current[k],arrays[k][ai]) for k in current),'prior endpoint mismatch'
        ids=[(str(c),int(r),str(a)) for c,r,a in zip(atoms.chain_id,atoms.res_id,atoms.atom_name)]
        assert hashlib.sha256(json.dumps(ids,separators=(',',':')).encode()).hexdigest()==ledger['atom_identity_sha256']
        assert hashlib.sha256(atoms.bonds.as_array().tobytes()).hexdigest()==ledger['topology_sha256']
        counts['endpoint_replay']+=1
        return current
    def decode(f,atoms,c):
        packed=pack_conditioning(c)
        return np.stack([diffusion_from_conditioning(model,f,identity_noise(atoms,seed,device='cuda'),packed,steps=1).squeeze(0).cpu().numpy() for seed in SEEDS])
    with torch.no_grad():
        for pi in lock['assignments'][index]:
            row=lock['rows'][pi];seq=row['sequence'];report['stage']=f'parent_{pi}';save()
            f,atoms,c=forward(seq,f'p{pi}_wt');wtxyz=decode(f,atoms,c)
            np.savez_compressed(out/f'p{pi}_wt_coordinates.npz',coordinates=wtxyz)
            site_records=[]
            for pos in row['positions']:
                source=lock['endpoints'][f'{pi}:{pos}'];assert sha256(Path(source['path']))==source['sha256']
                arrays=dict(np.load(source['path']));wi=AA.index(seq[pos]);replay(c,arrays,wi,pos,atoms,source['ledger'][wi])
                projected,energy=reconstruct_local_responses(arrays,wi,RANKS)
                for key in ['s_site','z_row','z_col']:
                    assert np.max(np.abs(projected[18][key]-arrays[key]))<=lock['full_rank_input_max_tolerance']
                site=dict(position=pos,wt_index=wi,energy=energy,mutants=[])
                for ai,aa in enumerate(AA):
                    if ai==wi:continue
                    label=f'p{pi}_s{pos+1}_{aa}';mutant=seq[:pos]+aa+seq[pos+1:]
                    mf,ma,mc=forward(mutant,label)
                    original=replay(mc,arrays,ai,pos,ma,source['ledger'][ai]);t=time.monotonic()
                    exact=decode(mf,ma,mc)
                    sham=pack_conditioning(local_conditioning_intervention(mc,original,pos))
                    assert all(torch.equal(a,b) for a,b in zip(pack_conditioning(mc),sham))
                    sham_x=diffusion_from_conditioning(model,mf,identity_noise(ma,SEEDS[0],device='cuda'),sham,steps=1).squeeze(0).cpu().numpy()
                    assert np.array_equal(sham_x,exact[0]),'sham not bitwise';counts['sham']+=1
                    coordinates=[exact]
                    for k in RANKS:
                        slices={key:projected[k][key][ai] for key in ['s_site','z_row','z_col']}
                        altered=local_conditioning_intervention(mc,slices,pos)
                        coordinates.append(decode(mf,ma,altered))
                    coordinates=np.stack(coordinates)
                    full_error=float(np.max(np.abs(coordinates[-1]-coordinates[0])))
                    assert full_error<=lock['full_rank_coordinate_max_tolerance_angstrom'],('full rank replay',full_error)
                    file=out/f'{label}_coordinates.npz';np.savez_compressed(file,coordinates=coordinates,ranks=[-1]+RANKS,seeds=SEEDS)
                    site['mutants'].append(dict(aa=aa,label=label,coordinate_sha256=sha256(file),full_rank_coordinate_max=full_error,sham_exact=True,
                        decode_and_save_seconds=time.monotonic()-t))
                    report.update(counts=dict(counts),active=label);save()
                    del mf,ma,mc,sham,altered
                site_records.append(site)
            report['parents'].append(dict(parent_index=pi,sites=site_records));save()
    n=len(lock['assignments'][index]);assert counts==dict(c4=n*96,recycle=n*384,nfe=n*2187,sham=n*95,endpoint_replay=n*100),counts
    for hook in hooks:hook.remove()
    report.update(complete=True,stage='complete',counts=counts,timings=timings,seconds=time.monotonic()-start,
        peak_allocated_bytes=torch.cuda.max_memory_allocated());save()


def score_functional_response_rank(root,index):
    torch.set_num_threads(1);lock=rt.load_json(root/'lock.json');out=root/f'worker_{index}';worker=rt.load_json(out/'report.json');assert worker['complete']
    allsites=[];start=time.monotonic()
    for parent in worker['parents']:
        pi=parent['parent_index'];row=lock['rows'][pi];gtinfo=lock['gt'][str(pi)]
        assert sha256(Path(gtinfo['path']))==gtinfo['sha256'];gt=dict(np.load(gtinfo['path']));gtca=gt['atom_names']=='CA'
        observed=gt['mask'][gtca];gty=gt['coordinates'][gtca];pairs,distances=backbone_target_pairs(gty,observed)
        for site in parent['sites']:
            pos=site['position'];wi=site['wt_index'];local=(observed & (np.linalg.norm(gty-gty[pos],axis=1)<8.)) if observed[pos] else np.zeros(len(gty),bool)
            local|=np.abs(np.arange(len(gty))-pos)<=2
            task=np.empty((len(RANKS)+1,2,20));rows=[]
            for ai,aa in enumerate(AA):
                label=f'p{pi}_wt' if ai==wi else f'p{pi}_s{pos+1}_{aa}'
                inv=dict(np.load(out/f'{label}_inventory.npz'));co=dict(np.load(out/f'{label}_coordinates.npz'))['coordinates']
                if ai==wi:co=np.repeat(co[None],len(RANKS)+1,axis=0)
                else:
                    record=next(m for m in site['mutants'] if m['aa']==aa)
                    assert sha256(out/f'{label}_coordinates.npz')==record['coordinate_sha256']
                ca=np.flatnonzero(inv['atom_names']=='CA');res=inv['residue_ids'];sequence=str(inv['sequence'])
                mapping=dict(inv,coordinates=co[0,0],mask=np.ones(len(res),bool))
                labels=build_adapter_supervision(mapping,inv['bonds'],sequence)
                for ni,seed in enumerate(SEEDS):
                    exact=co[0,ni];caches=(prepare_fidelity_pairs(exact,res),prepare_fidelity_pairs(exact[ca],res[ca]))
                    reference_geometry=response_geometry(exact,labels)
                    for ki,k in enumerate([-1]+RANKS):
                        x=co[ki,ni];task[ki,ni,ai]=float(backbone_target_loss(torch.tensor(x,dtype=torch.float64),ca,pairs,distances))
                        geometry=response_geometry(x,labels)
                        rows.append(dict(aa=aa,is_wt=ai==wi,noise=seed,rank=k,task=float(task[ki,ni,ai]),
                            fidelity=response_structure_metrics(x,exact,ca,local,caches),geometry=geometry,
                            severe_delta=geometry['severe_pairs']-reference_geometry['severe_pairs'],
                            chirality_delta=geometry['checked_chirality_wrong']-reference_geometry['checked_chirality_wrong'],
                            newly_fails_chemistry=reference_geometry['zero_severe_strict_checked_chirality'] and not geometry['zero_severe_strict_checked_chirality']))
            rankrows=[]
            for ki,k in enumerate(RANKS,1):
                for ni,seed in enumerate(SEEDS):
                    for include_wt in [False,True]:
                        ids=np.arange(20) if include_wt else np.delete(np.arange(20),wi)
                        rankrows.append(dict(rank=k,noise=seed,includes_wt=include_wt,**ranking_fidelity(task[0,ni,ids],task[ki,ni,ids])))
            result=dict(parent_index=pi,pdb_id=row['pdb_id'],position=pos,local_residues=int(local.sum()),energy=site['energy'],ranking=rankrows,outputs=rows)
            write_json(out/f'p{pi}_s{pos+1}_scores.json',result);allsites.append(result)
            write_json(out/'score_status.json',dict(complete=False,sites=len(allsites),seconds=time.monotonic()-start))
    write_json(out/'score_report.json',dict(complete=True,sites=allsites,seconds=time.monotonic()-start,lock_sha256=sha256(root/'lock.json')))
    write_json(out/'score_status.json',dict(complete=True,sites=len(allsites),seconds=time.monotonic()-start))


def collect_functional_response_rank(root):
    import gzip
    lock=rt.load_json(root/'lock.json');sites=[];workers=[]
    for i in range(8):
        worker=rt.load_json(root/f'worker_{i}/report.json');scores=rt.load_json(root/f'worker_{i}/score_report.json')
        assert worker['complete'] and scores['complete'] and scores['lock_sha256']==sha256(root/'lock.json')
        sites+=scores['sites'];workers.append(worker)
    assert len(sites)==50 and len({(s['parent_index'],s['position']) for s in sites})==50
    summary={};rng=np.random.default_rng(225101);boot=rng.integers(0,10,(10000,10))
    def aggregate(values):
        parents=np.array([np.mean([v for p,v in values if p==i and v is not None]) for i in range(10)])
        return dict(mean=float(parents.mean()),protein_bootstrap95=np.quantile(parents[boot].mean(1),[.025,.975]).tolist(),per_protein=parents.tolist())
    for k in RANKS:
        quality={};ranking={}
        selected=[(s['parent_index'],r) for s in sites for r in s['outputs'] if r['rank']==k and not r['is_wt']]
        for key in selected[0][1]['fidelity']:
            quality[key]=aggregate([(p,r['fidelity'][key]) for p,r in selected])
        for include_wt in [False,True]:
            rs=[(s['parent_index'],r) for s in sites for r in s['ranking'] if r['rank']==k and r['includes_wt']==include_wt]
            ranking[str(include_wt)]={key:aggregate([(p,r[key]) for p,r in rs]) for key in ['spearman','top1_regret','normalized_regret','top1_match','top3_recall','top5_recall','task_mae']}
            ranking[str(include_wt)]['low_task_range_count']=sum(r['low_task_range'] for _,r in rs)
        summary[str(k)]=dict(quality=quality,ranking=ranking,
            severe_total=sum(r['geometry']['severe_pairs'] for _,r in selected),
            severe_increased_instances=sum(r['severe_delta']>0 for _,r in selected),
            chirality_increased_instances=sum(r['chirality_delta']>0 for _,r in selected),
            newly_fails_chemistry=sum(r['newly_fails_chemistry'] for _,r in selected),
            zero_severe_strict_checked_chirality=sum(r['geometry']['zero_severe_strict_checked_chirality'] for _,r in selected),instances=len(selected))
    refs=[r for s in sites for r in s['outputs'] if r['rank']==-1 and not r['is_wt']]
    report=dict(complete=True,scope=lock['scope'],training=False,deployment_accepted=False,lock_sha256=sha256(root/'lock.json'),
                summary=summary,exact_reference=dict(instances=len(refs),severe_total=sum(r['geometry']['severe_pairs'] for r in refs),
                zero_severe_strict_checked_chirality=sum(r['geometry']['zero_severe_strict_checked_chirality'] for r in refs)),
                sites=sites,workers=workers)
    with gzip.open(root/'report.json.gz','wt') as f:json.dump(report,f,allow_nan=False)
    write_json(root/'summary.json',{k:v for k,v in report.items() if k not in ['sites','workers']})
    lines=['# Conditional local functional rank','','All other conditioning is exact hard-target; this is not complete trunk compression.','',
           '|K|AA fidelity lDDT|CA fidelity lDDT|Local CA RMSD|19-AA Spearman|Top1 match|Top1 regret|Geometry pass /1900|',
           '|---|---:|---:|---:|---:|---:|---:|---:|']
    for k,r in summary.items():
        q=r['quality'];a=r['ranking']['False']
        lines.append(f'|{k}|{q["all_atom_lddt"]["mean"]:.6f}|{q["ca_lddt"]["mean"]:.6f}|{q["local_ca_rmsd_global_frame"]["mean"]:.6f}|{a["spearman"]["mean"]:.6f}|{a["top1_match"]["mean"]:.3f}|{a["top1_regret"]["mean"]:.6f}|{r["zero_severe_strict_checked_chirality"]}|')
    (root/'report.md').write_text('\n'.join(lines)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--mode',choices=['prepare','run','score','collect'],required=True);parser.add_argument('--index',type=int,default=0);args=parser.parse_args()
    if args.mode=='prepare':prepare_functional_response_rank(args.root)
    elif args.mode=='run':run_functional_response_rank(args.root,args.index)
    elif args.mode=='score':score_functional_response_rank(args.root,args.index)
    else:collect_functional_response_rank(args.root)
