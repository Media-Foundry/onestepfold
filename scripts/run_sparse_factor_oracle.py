"""R32 plus fixed residual masks; existing eight-parent panel, no new C4."""
import argparse,gzip,json,time
from pathlib import Path
import numpy as np
import torch
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.factor_student_data import FactorTeacherStore
from fastglycan.factor_memorization import sparse_response_masks
from fastglycan.models.soft_sequence_chart import native_sequence_features,device_tree
from fastglycan.models.differentiable_mini import prepare_atom_pairs,diffusion_from_conditioning
from fastglycan.hybrid_proposals import identity_noise
from fastglycan.functional_response_rank import pack_conditioning
import run_global_response_rank as scoring

ARMS=('exact','baseline','oracle_r32','rowcol','contact','top_row_budget','top_contact_budget')


def run_sparse_oracle(root,index):
    lock=rt.load_json(root/'lock.json');torch.set_num_threads(1)
    for p,h in lock['code_hashes'].items():assert sha256(Path(p))==h,p
    store=FactorTeacherStore(Path(lock['teachers']));out=root/f'worker_{index}';out.mkdir(exist_ok=False);start=time.monotonic()
    old=rt.load_json(Path(lock['teachers'])/'evaluation/lock.json');owner={pi:wi for wi,parents in enumerate(old['assignments']) for pi in parents}
    runner=rt.runner_setup(out/'work');runner.configs.dtype='fp32';model=runner.model.eval().requires_grad_(False)
    counts=dict(nfe=0,recycle=0,replayed_packets=0);report=dict(complete=False,parents=[],lock_sha256=sha256(root/'lock.json'))
    def forbidden(*args):counts['recycle']+=1;raise AssertionError('C4 forbidden')
    hooks=[model.pairformer_stack.register_forward_pre_hook(forbidden),model.diffusion_module.register_forward_hook(lambda *a:counts.__setitem__('nfe',counts['nfe']+1))]
    def features(item):
        native,atoms=native_sequence_features(item['sequence']);inv=item['inventory']
        for key,actual in [('atom_names',atoms.atom_name),('residue_ids',atoms.res_id),('chain_ids',atoms.chain_id),('bonds',atoms.bonds.as_array()),('reference',native['ref_pos'].numpy())]:assert np.array_equal(actual,inv[key]),key
        np.savez_compressed(out/f'{item["label"]}_inventory.npz',**inv)
        return prepare_atom_pairs(model.relative_position_encoding.generate_relp(device_tree(native,'cuda'))),atoms
    def decode(f,atoms,c):return np.stack([diffusion_from_conditioning(model,f,identity_noise(atoms,n,device='cuda'),pack_conditioning(c),steps=1).squeeze(0).cpu().numpy() for n in lock['seeds']])
    with torch.no_grad():
        for pi in lock['assignments'][index]:
            row=lock['rows'][pi];wtitem=store.load(pi);wt=tuple(x.cuda() for x in wtitem['conditioning']);f,atoms=features(wtitem);xwt=decode(f,atoms,wt)
            assert np.array_equal(xwt,wtitem['coordinates']);np.savez_compressed(out/f'p{pi}_wt_coordinates.npz',coordinates=xwt)
            ca=np.flatnonzero(wtitem['inventory']['atom_names']=='CA');assert len(ca)==len(row['sequence'])
            assert np.array_equal(wtitem['inventory']['residue_ids'][ca],np.arange(1,len(ca)+1))
            wtca=torch.tensor(xwt[0,ca],device='cuda');sites=[]
            for pos in row['positions']:
                site=dict(position=pos,mutants=[])
                for a in lock['aa']:
                    if a==row['sequence'][pos]:continue
                    item=store.load(pi,pos,a);f,atoms=features(item);c=tuple(x.cuda() for x in item['conditioning']);delta=c[2].double()-wt[2].double()
                    p,s,qh=torch.linalg.svd(delta.permute(2,0,1),full_matrices=False);r=lock['rank'];bulk=((p[:,:,:r]*s[:,None,:r])@qh[:,:r]).permute(1,2,0);residual=delta-bulk
                    masks=sparse_response_masks(residual,pos,wtca,lock['contact_radius'])
                    z0=(wt[2].double()+bulk).float();zs=[z0]+[torch.where(mask[:,:,None],c[2],z0) for mask in masks.values()]
                    coords=[decode(f,atoms,c),decode(f,atoms,(wt[0],c[1],c[2]))]+[decode(f,atoms,(wt[0],c[1],z)) for z in zs]
                    assert np.array_equal(coords[0],item['coordinates'][0]) and np.array_equal(coords[1],item['coordinates'][1])
                    oldpacket=Path(lock['teachers'])/f'evaluation/worker_{owner[pi]}/{item["label"]}_coordinates.npz'
                    assert sha256(oldpacket)==lock['prior_coordinate_hashes'][str(oldpacket)]
                    previous=np.load(oldpacket)['coordinates'];assert np.array_equal(coords[2],previous[3]),'R32 replay';counts['replayed_packets']+=1
                    path=out/f'{item["label"]}_coordinates.npz';np.savez_compressed(path,coordinates=np.stack(coords),arms=ARMS,seeds=lock['seeds'])
                    mp=out/f'{item["label"]}_masks.npz';np.savez_compressed(mp,**{k:v.cpu().numpy() for k,v in masks.items()})
                    length,_,channels=delta.shape;factor_bytes=2*length*channels*r*4;dense_bytes=delta.numel()*4
                    evidence=dict(latent_nmse={arm:float((z.double()-c[2].double()).square().mean()/delta.square().mean().clamp_min(1e-6)) for arm,z in zip(ARMS[2:],zs)},
                        pairs={k:int(m.sum()) for k,m in masks.items()},factor_bytes=factor_bytes,dense_bytes=dense_bytes,
                        representation_fraction={'oracle_r32':factor_bytes/dense_bytes,**{k:(factor_bytes+int(m.sum())*(channels*4+8))/dense_bytes for k,m in masks.items()}},
                        mask_sha256=sha256(mp),mask_exact_max_error={k:float((z-c[2])[mask].abs().max()) for (k,mask),z in zip(masks.items(),zs[1:])})
                    site['mutants'].append(dict(aa=a,label=item['label'],coordinate_sha256=sha256(path),evidence=evidence));report.update(active=item['label'],counts=dict(counts));write_json(out/'report.json',report)
                sites.append(site)
            report['parents'].append(dict(parent_index=pi,sites=sites))
    for hook in hooks:hook.remove()
    assert counts==dict(nfe=len(lock['assignments'][index])*534,recycle=0,replayed_packets=len(lock['assignments'][index])*38)
    report.update(complete=True,counts=counts,seconds=time.monotonic()-start,peak_allocated_bytes=torch.cuda.max_memory_allocated());write_json(out/'report.json',report)


def collect_sparse_oracle(root):
    lock=rt.load_json(root/'lock.json');workers=[rt.load_json(root/f'worker_{i}/report.json') for i in range(8)];assert all(w['complete'] for w in workers)
    sites=[]
    for i in range(8):
        with gzip.open(root/f'scorer_{i}/report.json.gz','rt') as f:r=json.load(f)
        assert r['complete'];sites+=r['sites']
    assert len(sites)==16 and len({(s['parent_index'],s['position']) for s in sites})==16
    summary={}
    for arm in ARMS:
        outputs=[r for s in sites for r in s['outputs'] if r['arm']==arm and not r['is_wt']]
        ranks=[r for s in sites for r in s['ranking'] if r['arm']==arm and not r['includes_wt'] and r['reference']=='exact']
        assert len(outputs)==608
        summary[arm]=dict(instances=len(outputs),ranking={k:float(np.mean([r[k] for r in ranks])) for k in ['spearman','top1_match','top1_regret','top3_recall','top5_recall']} if ranks else {},
            top1_count=sum(r['top1_match'] for r in ranks),local_mean=float(np.mean([r['fidelity']['local_ca_rmsd_global_frame'] for r in outputs])),
            local_max=max(r['fidelity']['local_ca_rmsd_global_frame'] for r in outputs),local_over_1a=sum(r['fidelity']['local_ca_rmsd_global_frame']>1 for r in outputs),
            geometry_pass=sum(r['geometry']['zero_severe_strict_checked_chirality'] for r in outputs),new_geometry_vs_baseline=sum(r['new_compression_chemistry_failure'] for r in outputs),
            aa_lddt=float(np.mean([r['fidelity']['all_atom_lddt'] for r in outputs])))
    report=dict(complete=True,summary=summary,sites=sites,workers=workers,oracle_target_s=True,training=False,deployment_accepted=False)
    with gzip.open(root/'report.json.gz','wt') as f:json.dump(report,f,allow_nan=False)
    write_json(root/'summary.json',{k:v for k,v in report.items() if k not in ['sites','workers']})


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--index',type=int,default=0);p.add_argument('--mode',choices=['run','score','collect'],required=True);a=p.parse_args();scoring.ARMS=ARMS
    if a.mode=='run':run_sparse_oracle(a.root,a.index)
    elif a.mode=='score':scoring.score_global_response_rank(a.root,a.index)
    else:collect_sparse_oracle(a.root)
