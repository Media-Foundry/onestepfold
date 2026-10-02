"""New sequence-isolated parents: immutable native hard C4/S1 teacher endpoints."""
import argparse,time
from pathlib import Path
import numpy as np
import torch
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.models.soft_sequence_chart import native_sequence_features,device_tree
from fastglycan.models.differentiable_mini import full_recycle_pairformer,prepare_atom_pairs,diffusion_from_conditioning
from fastglycan.hybrid_proposals import identity_noise
from fastglycan.functional_response_rank import pack_conditioning


def prepare_factor_teachers(root):
    s=rt.load_json(root/'selection.json');assert s['complete'] and not (root/'teacher_lock.json').exists();gt={}
    for row in s['rows']:
        p=Path(row['source_metadata']['chemistry_packet'])/'mapping.npz';m=dict(np.load(p));assert sum(m['atom_names']=='CA')==len(row['sequence']);gt[str(row['index'])]=dict(path=str(p),sha256=sha256(p))
    write_json(root/'teacher_lock.json',dict(s,schema='factor_student_teachers_v1',selection_sha256=sha256(root/'selection.json'),gt=gt,seeds=[230201,230211],code_hashes={str(p):sha256(p) for p in (root/'teacher_code').rglob('*') if p.is_file() and p.suffix in ['.py','.md','.json']},expected_nfe=3696,training=False))


def export_factor_teachers(root,index):
    lock=rt.load_json(root/'teacher_lock.json');torch.set_num_threads(1);out=root/f'teacher_{index}';out.mkdir(exist_ok=False);start=time.monotonic()
    for p,h in lock['code_hashes'].items():assert sha256(Path(p))==h
    for p,h in lock['weights_sha256'].items():assert sha256(Path(p))==h
    report=dict(complete=False,worker=index,parents=[],lock_sha256=sha256(root/'teacher_lock.json'))
    def save():write_json(out/'report.json',report)
    save();runner=rt.runner_setup(out/'work');runner.configs.dtype='fp32';model=runner.model.eval().requires_grad_(False)
    torch.serialization.add_safe_globals([argparse.Namespace])
    from protenix.data.esm.compute_esm import load_esm_model
    esm,alphabet=load_esm_model('esm2-3b',local_esm_dir=runner.configs.load_checkpoint_dir);esm.eval().requires_grad_(False)
    counts=dict(c4=0,recycle=0,nfe=0,wt_replay=0);times=[]
    hooks=[model.pairformer_stack.register_forward_hook(lambda *a:counts.__setitem__('recycle',counts['recycle']+1)),model.diffusion_module.register_forward_hook(lambda *a:counts.__setitem__('nfe',counts['nfe']+1))]
    def forward(seq):
        torch.cuda.synchronize();t=time.monotonic();native,atoms=native_sequence_features(seq);f=model.relative_position_encoding.generate_relp(device_tree(native,'cuda'))
        tokens=alphabet.get_batch_converter()([('hard',seq)])[2].cuda();f['esm_token_embedding']=esm(tokens,repr_layers=[esm.num_layers],return_contacts=False)['representations'][esm.num_layers][0,1:-1];f=prepare_atom_pairs(f)
        torch.cuda.synchronize();tf=time.monotonic()-t;t=time.monotonic();c=full_recycle_pairformer(model,f,N_cycle=4,inplace_safe=False,mc_dropout=False);torch.cuda.synchronize();tc=time.monotonic()-t
        assert all(torch.isfinite(x).all() and x.dtype==torch.float32 for x in c);counts['c4']+=1;times.append(dict(features_esm_seconds=tf,c4_seconds=tc))
        return f,atoms,c
    def decode(f,atoms,c):return np.stack([diffusion_from_conditioning(model,f,identity_noise(atoms,seed,device='cuda'),pack_conditioning(c),steps=1).squeeze(0).cpu().numpy() for seed in lock['seeds']])
    def store(label,seq,f,atoms,c,xyz):
        p=out/f'{label}_conditioning.pt';torch.save(dict(sequence=seq,conditioning=[x.cpu() for x in c]),p)
        inv=out/f'{label}_inventory.npz';np.savez_compressed(inv,atom_names=atoms.atom_name,residue_ids=atoms.res_id,chain_ids=atoms.chain_id,reference=f['ref_pos'].cpu().numpy(),bonds=atoms.bonds.as_array(),sequence=np.array(seq))
        coords=out/f'{label}_coordinates.npz';np.savez_compressed(coords,coordinates=xyz,seeds=lock['seeds'])
        return dict(label=label,files={x.name:dict(sha256=sha256(x),bytes=x.stat().st_size) for x in [p,inv,coords]})
    with torch.no_grad():
        for pi in lock['assignments'][index]:
            row=lock['rows'][pi];seq=row['sequence'];f,atoms,wt=forward(seq);_,_,replay=forward(seq);assert all(torch.equal(x,y) for x,y in zip(wt,replay));counts['wt_replay']+=1
            wx=decode(f,atoms,wt);parent=dict(parent_index=pi,role=row['role'],wt=store(f'p{pi}_wt',seq,f,atoms,wt,wx),sites=[])
            for pos in row['positions']:
                site=dict(position=pos,mutants=[])
                for aa in lock['aa']:
                    if aa==seq[pos]:continue
                    label=f'p{pi}_s{pos+1}_{aa}';report['active']=label;save();target=seq[:pos]+aa+seq[pos+1:];mf,ma,c=forward(target)
                    exact=decode(mf,ma,c);base=decode(mf,ma,(wt[0],c[1],c[2]));assert np.isfinite(exact).all() and np.isfinite(base).all()
                    site['mutants'].append(dict(aa=aa,**store(label,target,mf,ma,c,np.stack([exact,base]))))
                parent['sites'].append(site)
            report['parents'].append(parent);save()
    for h in hooks:h.remove()
    n=len(lock['assignments'][index]);assert counts==dict(c4=40*n,recycle=160*n,nfe=154*n,wt_replay=n),counts
    report.update(complete=True,counts=counts,seconds=time.monotonic()-start,timings=times,peak_allocated_bytes=torch.cuda.max_memory_allocated());save()


def collect_factor_teachers(root):
    lock=rt.load_json(root/'teacher_lock.json');workers=[rt.load_json(root/f'teacher_{i}/report.json') for i in range(8)];assert all(w['complete'] for w in workers)
    manifest=[]
    for w in workers:
        for p in w['parents']:
            for item in [p['wt']]+[m for s in p['sites'] for m in s['mutants']]:
                for name,record in item['files'].items():
                    path=root/f'teacher_{w["worker"]}'/name;assert sha256(path)==record['sha256'];manifest.append(dict(path=str(path.relative_to(root)),**record))
    assert len(manifest)==936*3
    write_json(root/'teacher_manifest.json',manifest);write_json(root/'teacher_report.json',dict(complete=True,workers=workers,counts={k:sum(w['counts'][k] for w in workers) for k in workers[0]['counts']},lock_sha256=sha256(root/'teacher_lock.json'),manifest_sha256=sha256(root/'teacher_manifest.json')))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True,type=Path);p.add_argument('--mode',choices=['prepare','run','collect'],required=True);p.add_argument('--index',type=int,default=0);a=p.parse_args()
    if a.mode=='prepare':prepare_factor_teachers(a.root)
    elif a.mode=='run':export_factor_teachers(a.root,a.index)
    else:collect_factor_teachers(a.root)
