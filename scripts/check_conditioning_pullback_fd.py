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
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--case',required=True);a=p.parse_args();root=a.root.resolve();lock=rt.load_json(root/'lock.json');seq=lock['cases'][a.case]['sequence'];out=root/f'pullback_fd_{a.case}';out.mkdir(exist_ok=False)
runner=rt.runner_setup(out/'work');model=runner.model.eval().requires_grad_(False);torch.serialization.add_safe_globals([argparse.Namespace])
from protenix.data.esm.compute_esm import load_esm_model
esm,alphabet=load_esm_model('esm2-3b',local_esm_dir=runner.configs.load_checkpoint_dir);esm.eval().requires_grad_(False)
templates={aa:native_sequence_features(aa*len(seq)) for aa in AMINO_ACIDS};chart=SequenceChart(seq,model,esm,alphabet,templates);topology=GeometryTopology(chart.atoms,chart.native['ref_pos'].cpu().numpy());initial=identity_noise(chart.atoms,211,device='cuda')
with torch.no_grad():
 features=chart.features((sequence_probabilities(seq,device='cuda')*4).softmax(-1))
 point=full_recycle_pairformer(model,features,N_cycle=4,inplace_safe=False,mc_dropout=False)
shapes=[v.shape for v in point];sizes=[v.numel() for v in point];scales=[max(float(v.square().mean().sqrt()),1e-3) for v in point];flat=torch.cat([v.flatten() for v in point])
def unpack(v):return tuple(t.reshape(shape) for t,shape in zip(v.split(sizes),shapes))

def losses(x):
 task=contact_objective(x,chart.ca_indices)[0]
 terms,_=topology.terms(x)
 return dict(old=task,new=task+terms['bond']+2*terms['peptide']+terms['clash']+.2*terms['chirality'])
q=flat.detach().clone().requires_grad_(True)
x=diffusion_from_conditioning(model,features,initial,unpack(q),steps=1)
anchor=x.detach().clone()
coordinate_gradients={};input_gradients={};base_losses={}
for precision in ('fp32','loss_fp64'):
 y=anchor.to(torch.float64 if precision=='loss_fp64' else torch.float32).requires_grad_(True)
 values=losses(y)
 for name,value in values.items():
  key=name+'_'+precision
  gx,=torch.autograd.grad(value,y,retain_graph=True)
  gq,=torch.autograd.grad(x,q,grad_outputs=gx.to(x),retain_graph=True)
  coordinate_gradients[key]=gx.detach().double();input_gradients[key]=gq.detach();base_losses[key]=float(value)
del x,q,y,values,gx,gq
result=dict(complete=False,case=a.case,model_precision='fp32',full_model_fp64=False,
 scope='diagnostic only, original gates unchanged',block_rms=scales,base_losses=base_losses,
 h=[.01,.003,.001,.0003,.0001],directions=[])
generator=torch.Generator(device='cuda').manual_seed(731)
for index in range(3):
 v=torch.cat([(torch.randn(shape,device='cuda',generator=generator)*scale).flatten() for shape,scale in zip(shapes,scales)])
 analytic={key:float((g.double()*v.double()).sum()) for key,g in input_gradients.items()}
 rows=[]
 with torch.no_grad():
  for h in result['h']:
   xp=diffusion_from_conditioning(model,features,initial,unpack(flat+h*v),steps=1)
   xm=diffusion_from_conditioning(model,features,initial,unpack(flat-h*v),steps=1)
   response=(xp.double()-xm.double())/(2*h)
   values={}
   for precision in ('fp32','loss_fp64'):
    yp=xp.double() if precision=='loss_fp64' else xp
    ym=xm.double() if precision=='loss_fp64' else xm
    lp,lm=losses(yp),losses(ym)
    for name in ('old','new'):
     key=name+'_'+precision;ad=analytic[key]
     linear=float((coordinate_gradients[key]*response).sum())
     nonlinear=float((lp[name]-lm[name])/(2*h))
     tolerance=lambda fd:abs(fd-ad)<=1e-6+.05*max(abs(fd),abs(ad))
     values[key]=dict(analytic=ad,linearized_coordinate_fd=linear,objective_fd=nonlinear,
       linear_pass=tolerance(linear),objective_pass=tolerance(nonlinear),
       curvature_remainder=nonlinear-linear)
   rows.append(dict(h=h,values=values))
 result['directions'].append(dict(index=index,rows=rows));write_json(out/'report.json',result)
result['summary']={}
for key in input_gradients:
 result['summary'][key]={}
 for field in ('linear_pass','objective_pass'):
  passed=[any(r1['values'][key][field] and r2['values'][key][field] for r1,r2 in zip(d['rows'],d['rows'][1:])) for d in result['directions']]
  result['summary'][key][field]=dict(directions=passed,passed=all(passed))
from fastglycan.paired_teacher_protocol import sha256
result.update(complete=True,source_sha256=sha256(Path(__file__)),lock_sha256=sha256(root/'lock.json'))
write_json(out/'report.json',result)
