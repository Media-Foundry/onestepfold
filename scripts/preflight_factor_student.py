import argparse,time
from pathlib import Path
import numpy as np
import torch
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.paired_teacher_protocol import write_json
from fastglycan.factor_student import FactorStudent,expand_pair_factors,factor_geometry_penalties
from fastglycan.factor_student_data import FactorTeacherStore
from fastglycan.models.soft_sequence_chart import native_sequence_features,device_tree
from fastglycan.models.differentiable_mini import prepare_atom_pairs,diffusion_from_conditioning
from fastglycan.functional_response_rank import pack_conditioning
from fastglycan.adapter_supervision import build_adapter_supervision
from fastglycan.hybrid_proposals import identity_noise


def preflight_factor_student(root):
    torch.set_num_threads(1);lock=rt.load_json(root/'student_lock.json');data=FactorTeacherStore(root,True);row=next(r for r in data.lock['rows'] if r['role']=='train');pi=row['index'];pos=row['positions'][0];aa=data.lock['aa'];a=next(a for a in aa if a!=row['sequence'][pos]);item=data.load(pi,pos,a);wt=tuple(x.cuda() for x in data.load(pi)['conditioning']);c=tuple(x.cuda() for x in item['conditioning'])
    runner=rt.runner_setup(root/'preflight_work');runner.configs.dtype='fp32';decoder=runner.model.eval().requires_grad_(False);torch.manual_seed(230301);net=FactorStudent(**lock['architecture']).cuda();opt=torch.optim.AdamW(net.parameters(),lr=lock['lr'],weight_decay=lock['weight_decay'])
    native,atoms=native_sequence_features(item['sequence']);f=prepare_atom_pairs(decoder.relative_position_encoding.generate_relp(device_tree(native,'cuda')));noise=identity_noise(atoms,data.lock['seeds'][0],device='cuda');teacher=torch.tensor(item['coordinates'][1,0],device='cuda')
    with torch.no_grad():replay=diffusion_from_conditioning(decoder,f,noise,pack_conditioning((wt[0],c[1],c[2])),steps=1).squeeze(0)
    assert torch.equal(replay,teacher)
    u,v=net(wt[1],wt[2],pos,aa.index(row['sequence'][pos]),[aa.index(a)]);d=expand_pair_factors(u,v)[0];delta=c[2]-wt[2];latent=(d-delta).square().mean()/delta.square().mean().clamp_min(1e-6)
    x=diffusion_from_conditioning(decoder,f,noise,pack_conditioning((wt[0],c[1],wt[2]+d)),steps=1).squeeze(0);coordinate=(x-teacher).square().mean();inv=item['inventory'];labels=build_adapter_supervision(dict(inv,coordinates=item['coordinates'][1,0],mask=np.ones(len(x),bool)),inv['bonds'],item['sequence']);clash,chirality=factor_geometry_penalties(x,labels)
    loss=latent+.25*coordinate+.01*clash+.1*chirality;loss.backward();norm=torch.nn.utils.clip_grad_norm_(net.parameters(),1.,error_if_nonfinite=True);assert torch.isfinite(loss) and net.v.weight.grad.norm()>0;opt.step()
    write_json(root/'student_preflight.json',dict(complete=True,parent_index=pi,position=pos,aa=a,baseline_replay_exact=True,loss=float(loss.detach()),gradient_norm=float(norm),v_gradient_norm=float(net.v.weight.grad.norm()),peak_allocated_bytes=torch.cuda.max_memory_allocated(),parameters=sum(p.numel() for p in net.parameters()),checkpoint_retained=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();preflight_factor_student(a.root)
