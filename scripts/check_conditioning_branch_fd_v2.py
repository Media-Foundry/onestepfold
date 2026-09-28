#!/usr/bin/env python3
"""Decompose fixed-graph conditioning branches and weighted objective terms."""
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
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--case',required=True);p.add_argument('--branch',choices=['s_inputs','s','z','all'],required=True);a=p.parse_args();root=a.root.resolve();lock=rt.load_json(root/'lock.json');seq=lock['cases'][a.case]['sequence'];out=root/f'branch_fd2_{a.case}_{a.branch}';out.mkdir(exist_ok=False)
runner=rt.runner_setup(out/'work');model=runner.model.eval().requires_grad_(False);torch.serialization.add_safe_globals([argparse.Namespace])
from protenix.data.esm.compute_esm import load_esm_model
esm,alphabet=load_esm_model('esm2-3b',local_esm_dir=runner.configs.load_checkpoint_dir);esm.eval().requires_grad_(False)
templates={aa:native_sequence_features(aa*len(seq)) for aa in AMINO_ACIDS};chart=SequenceChart(seq,model,esm,alphabet,templates);topology=GeometryTopology(chart.atoms,chart.native['ref_pos'].cpu().numpy());initial=identity_noise(chart.atoms,211,device='cuda')
with torch.no_grad():
 features=chart.features((sequence_probabilities(seq,device='cuda')*4).softmax(-1))
 point=full_recycle_pairformer(model,features,N_cycle=4,inplace_safe=False,mc_dropout=False)
shapes=[v.shape for v in point];sizes=[v.numel() for v in point];scales=[max(float(v.square().mean().sqrt()),1e-3) for v in point];flat=torch.cat([v.flatten() for v in point])
def unpack(v):return tuple(t.reshape(shape) for t,shape in zip(v.split(sizes),shapes))


from fastglycan.conditioning_diagnostics import weighted_geometry_objectives,directional_comparison
from fastglycan.paired_teacher_protocol import sha256
for name,digest in lock['source_sha256'].items():
 if sha256(Path(__file__).resolve().parents[1]/name)!=digest:raise ValueError('frozen source changed '+name)
def losses(x):return weighted_geometry_objectives(x,chart.ca_indices,topology)
q=flat.detach().clone().requires_grad_(True)
x=diffusion_from_conditioning(model,features,initial,unpack(q),steps=1)
anchor=x.detach().clone();y=anchor.clone().requires_grad_(True);values=losses(y)
coordinate_gradients={};input_gradients={};base_losses={}
for key,value in values.items():
 gx,=torch.autograd.grad(value,y,retain_graph=True)
 gq,=torch.autograd.grad(x,q,grad_outputs=gx,retain_graph=True)
 coordinate_gradients[key]=gx.detach().double();input_gradients[key]=gq.detach();base_losses[key]=float(value)
with torch.no_grad():
 repeat=diffusion_from_conditioning(model,features,initial,unpack(flat),steps=1)
 if not torch.equal(repeat,anchor):raise RuntimeError('forward is not reproducible')
prior=rt.load_json(root/f'pullback_fd_{a.case}/report.json')
for name in ('old','new'):
 if abs(base_losses[name]-prior['base_losses'][name+'_fp32'])>1e-7:raise RuntimeError('conditioning point/loss replay drift')
del x,q,y,values,gx,gq,repeat
names=['s_inputs','s','z'];active=[i for i,n in enumerate(names) if a.branch=='all' or n==a.branch]
mask=torch.cat([torch.full((size,),i in active,device='cuda',dtype=torch.bool) for i,size in enumerate(sizes)])
result=dict(complete=False,case=a.case,branch=a.branch,model_precision='fp32',scope='fixed chart conditioning diagnosis, not sequence or deployment acceptance',
 source_sha256=sha256(Path(__file__)),helper_sha256=sha256(Path(__file__).resolve().parents[1]/'src/fastglycan/conditioning_diagnostics.py'),
 lock_sha256=sha256(root/'lock.json'),base_losses=base_losses,block_rms=scales,
 forward_replay_exact=True,replay_layout='packed for both grad and no_grad',prior_point_replay=True,
 storage={n:dict(original_offset=int(p.storage_offset()),packed_offset=int(w.storage_offset()),original_ptr_mod256=int(p.data_ptr()%256),packed_ptr_mod256=int(w.data_ptr()%256)) for n,p,w in zip(names,point,unpack(flat))},h=[.01,.003,.001,.0003,.0001],directions=[])
generator=torch.Generator(device='cuda').manual_seed(731);directions=[]
for index in range(3):
 v=torch.cat([(torch.randn(shape,device='cuda',generator=generator)*scale).flatten() for shape,scale in zip(shapes,scales)])
 directions.append((f'random{index}',v*mask))
# Additional high-signal diagnostic; never replaces the three random directions.
g=input_gradients['new']*mask
if g.norm()>0:
 directions.append(('gradient_aligned_new',g/g.norm()*directions[0][1].norm()))
for label,v in directions:
 analytic={key:float((g.double()*v.double()).sum()) for key,g in input_gradients.items()}
 absolute_products={key:float((g.double()*v.double()).abs().sum()) for key,g in input_gradients.items()}
 rows=[]
 with torch.no_grad():
  for h in result['h']:
   xp=diffusion_from_conditioning(model,features,initial,unpack(flat+h*v),steps=1)
   xm=diffusion_from_conditioning(model,features,initial,unpack(flat-h*v),steps=1)
   response=(xp.double()-xm.double())/(2*h);lp,lm=losses(xp),losses(xm)
   values={key:directional_comparison(analytic[key],float((coordinate_gradients[key]*response).sum()),float((lp[key]-lm[key])/(2*h))) for key in input_gradients}
   rows.append(dict(h=h,coordinate_response_norm=float(response.norm()),values=values))
 result['directions'].append(dict(label=label,direction_norm=float(v.norm()),absolute_dot_products=absolute_products,rows=rows));write_json(out/'report.json',result)
result['summary']={}
for key in input_gradients:
 result['summary'][key]={}
 for field in ('linear_pass','objective_pass'):
  passed=[any(r1['values'][key][field] and r2['values'][key][field] for r1,r2 in zip(d['rows'],d['rows'][1:])) for d in result['directions']]
  result['summary'][key][field]=dict(random_directions=passed[:3],random_passed=all(passed[:3]),aligned=passed[3] if len(passed)>3 else None)
result['complete']=True;write_json(out/'report.json',result)
