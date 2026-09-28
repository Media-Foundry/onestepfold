#!/usr/bin/env python3
"""Additional input-scale-aware conditioning FD; original unit-direction gates unchanged."""
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
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--case',required=True);a=p.parse_args();root=a.root.resolve();lock=rt.load_json(root/'lock.json');seq=lock['cases'][a.case]['sequence'];out=root/f'relative_fd_{a.case}';out.mkdir(exist_ok=False)
runner=rt.runner_setup(out/'work');model=runner.model.eval().requires_grad_(False);torch.serialization.add_safe_globals([argparse.Namespace])
from protenix.data.esm.compute_esm import load_esm_model
esm,alphabet=load_esm_model('esm2-3b',local_esm_dir=runner.configs.load_checkpoint_dir);esm.eval().requires_grad_(False)
templates={aa:native_sequence_features(aa*len(seq)) for aa in AMINO_ACIDS};chart=SequenceChart(seq,model,esm,alphabet,templates);topology=GeometryTopology(chart.atoms,chart.native['ref_pos'].cpu().numpy());initial=identity_noise(chart.atoms,211,device='cuda')
with torch.no_grad():
 features=chart.features((sequence_probabilities(seq,device='cuda')*4).softmax(-1))
 point=full_recycle_pairformer(model,features,N_cycle=4,inplace_safe=False,mc_dropout=False)
shapes=[v.shape for v in point];sizes=[v.numel() for v in point];scales=[max(float(v.square().mean().sqrt()),1e-3) for v in point];flat=torch.cat([v.flatten() for v in point])
def unpack(v):return tuple(t.reshape(shape) for t,shape in zip(v.split(sizes),shapes))
def objective(v,name):
 x=diffusion_from_conditioning(model,features,initial,unpack(v),steps=1)
 task=contact_objective(x,chart.ca_indices)[0]
 if name=='old':return task
 terms,_=topology.terms(x);return task+terms['bond']+2*terms['peptide']+terms['clash']+.2*terms['chirality']
result=dict(complete=False,case=a.case,dtype='float32',direction='independent Gaussian blocks scaled by conditioning RMS, no global normalization',block_rms=scales,relative_h=[.03,.01,.003,.001,.0003],old_unit_direction_gate_unchanged=True,objectives={})
for name in ('old','new'):
 q=flat.detach().clone().requires_grad_(True);gradient,=torch.autograd.grad(objective(q,name),q);records=[];generator=torch.Generator(device='cuda').manual_seed(731)
 for _ in range(3):
  pieces=[torch.randn(shape,device='cuda',generator=generator)*scale for shape,scale in zip(shapes,scales)];v=torch.cat([t.flatten() for t in pieces]);analytic=float((gradient.double()*v.double()).sum());rows=[]
  with torch.no_grad():
   for h in result['relative_h']:
    difference=float((objective(q+h*v,name)-objective(q-h*v,name))/(2*h));error=abs(analytic-difference)
    rows.append(dict(h=h,analytic=analytic,finite_difference=difference,absolute_error=error,passed=error<=1e-6+.05*max(abs(analytic),abs(difference))))
  records.append(dict(rows=rows,plateau_pass=any(a['passed'] and b['passed'] for a,b in zip(rows,rows[1:]))))
 result['objectives'][name]=dict(directions=records,passed=all(x['plateau_pass'] for x in records));write_json(out/'report.json',result)
result['complete']=True;write_json(out/'report.json',result)
