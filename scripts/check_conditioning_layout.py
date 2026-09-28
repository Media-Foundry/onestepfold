#!/usr/bin/env python3
"""Separate denoiser directional response from downstream loss curvature and precision."""
import argparse,json
from pathlib import Path
import torch
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.models.soft_esm import AMINO_ACIDS,sequence_probabilities
from fastglycan.models.soft_sequence_chart import SequenceChart,native_sequence_features
from fastglycan.models.differentiable_mini import full_recycle_pairformer,diffusion_from_conditioning
from fastglycan.hybrid_geometry import GeometryTopology
from fastglycan.hybrid_proposals import identity_noise
from fastglycan.sequence_gate_metrics import contact_objective
from fastglycan.paired_teacher_protocol import write_json
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--case',required=True);a=p.parse_args();root=a.root.resolve();lock=rt.load_json(root/'lock.json');seq=lock['cases'][a.case]['sequence'];out=root/f'layout_fd_{a.case}';out.mkdir(exist_ok=False)
runner=rt.runner_setup(out/'work');model=runner.model.eval().requires_grad_(False);torch.serialization.add_safe_globals([argparse.Namespace])
from protenix.data.esm.compute_esm import load_esm_model
esm,alphabet=load_esm_model('esm2-3b',local_esm_dir=runner.configs.load_checkpoint_dir);esm.eval().requires_grad_(False)
templates={aa:native_sequence_features(aa*len(seq)) for aa in AMINO_ACIDS};chart=SequenceChart(seq,model,esm,alphabet,templates);topology=GeometryTopology(chart.atoms,chart.native['ref_pos'].cpu().numpy());initial=identity_noise(chart.atoms,211,device='cuda')
with torch.no_grad():
 features=chart.features((sequence_probabilities(seq,device='cuda')*4).softmax(-1))
 point=full_recycle_pairformer(model,features,N_cycle=4,inplace_safe=False,mc_dropout=False)
shapes=[v.shape for v in point];sizes=[v.numel() for v in point];scales=[max(float(v.square().mean().sqrt()),1e-3) for v in point];flat=torch.cat([v.flatten() for v in point])
def unpack(v):return tuple(t.reshape(shape) for t,shape in zip(v.split(sizes),shapes))


from fastglycan.paired_teacher_protocol import sha256
outputs={}
with torch.no_grad():
 outputs['original_no_grad']=diffusion_from_conditioning(model,features,initial,point,steps=1)
 outputs['packed_no_grad']=diffusion_from_conditioning(model,features,initial,unpack(flat),steps=1)
 outputs['packed_no_grad_repeat']=diffusion_from_conditioning(model,features,initial,unpack(flat),steps=1)
 outputs['contiguous_no_grad']=diffusion_from_conditioning(model,features,initial,tuple(p.contiguous() for p in point),steps=1)
q=flat.detach().clone().requires_grad_(True)
x=diffusion_from_conditioning(model,features,initial,unpack(q),steps=1);outputs['packed_grad']=x.detach();del x
with torch.no_grad():outputs['packed_requires_grad_no_grad']=diffusion_from_conditioning(model,features,initial,unpack(q),steps=1)
pg=tuple(v.detach().requires_grad_(True) for v in point)
x=diffusion_from_conditioning(model,features,initial,pg,steps=1);outputs['original_grad']=x.detach();del x
names=['s_inputs','s','z']
meta={name:dict(shape=list(v.shape),original_stride=list(v.stride()),packed_stride=list(w.stride()),equal=torch.equal(v,w)) for name,v,w in zip(names,point,unpack(flat))}
comparisons={}
for name,v in outputs.items():
 delta=(v-outputs['packed_grad']).double()
 comparisons[name]=dict(exact=torch.equal(v,outputs['packed_grad']),max_abs=float(delta.abs().max()),rms=float(delta.square().mean().sqrt()))
path=out/'coordinates.pt';torch.save({k:v.cpu() for k,v in outputs.items()},path)
write_json(out/'report.json',dict(complete=True,case=a.case,metadata=meta,relative_to_packed_grad=comparisons,
 packed_repeat_exact=torch.equal(outputs['packed_no_grad'],outputs['packed_no_grad_repeat']),
 coordinate_sha256=sha256(path),source_sha256=sha256(Path(__file__)),lock_sha256=sha256(root/'lock.json')))
