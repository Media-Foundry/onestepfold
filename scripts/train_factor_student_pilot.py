"""Bounded new-parent factor-only student; oracle target s is decoder-only."""
import argparse,json,time
from pathlib import Path
import numpy as np
import torch
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.factor_student import FactorStudent,expand_pair_factors,factor_geometry_penalties
from fastglycan.factor_student_data import FactorTeacherStore
from fastglycan.models.soft_sequence_chart import native_sequence_features,device_tree
from fastglycan.models.differentiable_mini import prepare_atom_pairs,diffusion_from_conditioning
from fastglycan.functional_response_rank import pack_conditioning
from fastglycan.adapter_supervision import build_adapter_supervision
from fastglycan.hybrid_proposals import identity_noise


def train_factor_student(root,index):
    lock=rt.load_json(root/'student_lock.json');torch.set_num_threads(1);seed=lock['initialization_seeds'][index];torch.manual_seed(seed);np.random.seed(seed);start=time.monotonic()
    for p,h in lock['code_hashes'].items():assert sha256(Path(p))==h
    data=FactorTeacherStore(root,training_only=True);out=root/f'train_{index}';out.mkdir(exist_ok=False)
    runner=rt.runner_setup(out/'work');runner.configs.dtype='fp32';decoder=runner.model.eval().requires_grad_(False)
    for p,h in data.lock['weights_sha256'].items():assert sha256(Path(p))==h
    torch.manual_seed(seed)  # runner setup also seeds RNG; initialize the student AFTER it.
    net=FactorStudent(**lock['architecture']).cuda().train();optimizer=torch.optim.AdamW(net.parameters(),lr=lock['lr'],weight_decay=lock['weight_decay'])
    counts=dict(nfe=0,recycle=0)
    def forbid(*args):counts['recycle']+=1;raise AssertionError('trunk forbidden during student fitting')
    hooks=[decoder.pairformer_stack.register_forward_pre_hook(forbid),decoder.diffusion_module.register_forward_hook(lambda *a:counts.__setitem__('nfe',counts['nfe']+1))]
    rows=[r for r in data.lock['rows'] if r['role']=='train'];aa=data.lock['aa'];rng=np.random.default_rng(lock['sampling_seed']);history=[];checked=set();wtgpu={}
    report=dict(complete=False,index=index,seed=seed,updates=0,losses=[],parameters=sum(p.numel() for p in net.parameters()),lock_sha256=sha256(root/'student_lock.json'))
    for step in range(lock['updates']):
        row=rows[int(rng.integers(len(rows)))];pi=row['index'];pos=row['positions'][int(rng.integers(2))];choices=[x for x in aa if x!=row['sequence'][pos]];a=choices[int(rng.integers(19))];ni=int(rng.integers(2))
        item=data.load(pi,pos,a)
        if pi not in wtgpu:wtgpu[pi]=tuple(x.cuda() for x in data.load(pi)['conditioning'])
        wt=wtgpu[pi];target_z=item['conditioning'][2].cuda();delta=target_z-wt[2]
        optimizer.zero_grad(set_to_none=True);u,v=net(wt[1],wt[2],pos,aa.index(row['sequence'][pos]),[aa.index(a)]);pred=expand_pair_factors(u,v)[0]
        latent=(pred-delta).square().mean()/delta.square().mean().clamp_min(1e-6);loss=latent;parts=dict(latent=float(latent.detach()))
        if step>=lock['warmup']:
            native,atoms=native_sequence_features(item['sequence']);inv=item['inventory']
            assert np.array_equal(atoms.atom_name,inv['atom_names']) and np.array_equal(atoms.bonds.as_array(),inv['bonds']) and np.array_equal(native['ref_pos'].numpy(),inv['reference'])
            f=prepare_atom_pairs(decoder.relative_position_encoding.generate_relp(device_tree(native,'cuda')));noise=identity_noise(atoms,data.lock['seeds'][ni],device='cuda');target_s=item['conditioning'][1].cuda();teacher=torch.tensor(item['coordinates'][1,ni],device='cuda')
            if pi not in checked:
                with torch.no_grad():replay=diffusion_from_conditioning(decoder,f,noise,pack_conditioning((wt[0],target_s,target_z)),steps=1).squeeze(0)
                assert torch.equal(replay,teacher),'matched baseline replay';checked.add(pi)
            x=diffusion_from_conditioning(decoder,f,noise,pack_conditioning((wt[0],target_s,wt[2]+pred)),steps=1).squeeze(0)
            coordinate=(x-teacher).square().mean();ca=torch.tensor(np.flatnonzero(inv['atom_names']=='CA'),device='cuda');ij=torch.triu_indices(len(ca),len(ca),offset=3,device='cuda')
            dx=torch.linalg.vector_norm(x[ca[ij[0]]]-x[ca[ij[1]]],dim=-1);dt=torch.linalg.vector_norm(teacher[ca[ij[0]]]-teacher[ca[ij[1]]],dim=-1);distance=(dx-dt).square().mean()
            labels=build_adapter_supervision(dict(inv,coordinates=item['coordinates'][1,ni],mask=np.ones(len(x),bool)),inv['bonds'],item['sequence']);clash,chirality=factor_geometry_penalties(x,labels)
            loss=loss+lock['loss_weights']['coordinate']*coordinate+lock['loss_weights']['distance']*distance+lock['loss_weights']['clash']*clash+lock['loss_weights']['chirality']*chirality
            parts.update(coordinate=float(coordinate.detach()),distance=float(distance.detach()),clash=float(clash.detach()),chirality=float(chirality.detach()))
        assert torch.isfinite(loss);loss.backward();norm=torch.nn.utils.clip_grad_norm_(net.parameters(),1.,error_if_nonfinite=True);optimizer.step()
        history.append(dict(step=step+1,parent_index=pi,position=pos,aa=a,noise_index=ni,loss=float(loss.detach()),gradient_norm=float(norm),**parts))
        if (step+1)%64==0:
            report.update(updates=step+1,losses=history,counts=dict(counts),seconds=time.monotonic()-start);write_json(out/'report.json',report)
    assert len(checked)==16 and counts['recycle']==0 and counts['nfe']==lock['updates']-lock['warmup']+16
    path=out/'final.pt';torch.save(dict(state_dict=net.state_dict(),architecture=lock['architecture'],seed=seed,updates=lock['updates'],student_lock_sha256=sha256(root/'student_lock.json')),path)
    report.update(complete=True,updates=lock['updates'],losses=history,counts=counts,checkpoint_sha256=sha256(path),seconds=time.monotonic()-start,peak_allocated_bytes=torch.cuda.max_memory_allocated(),matched_baseline_replay_parents=sorted(checked));write_json(out/'report.json',report)
    for h in hooks:h.remove()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--index',type=int,required=True);a=p.parse_args();train_factor_student(a.root,a.index)
