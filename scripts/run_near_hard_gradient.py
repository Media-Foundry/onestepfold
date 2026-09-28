#!/usr/bin/env python3
"""Full live-ESM ERC logits derivatives at two near-hard interior points."""
import argparse,json,time,gc
from pathlib import Path
import numpy as np
import torch
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.models.soft_esm import AMINO_ACIDS,sequence_probabilities
from fastglycan.models.soft_sequence_chart import SequenceChart,native_sequence_features
from fastglycan.models.differentiable_mini import full_recycle_pairformer,diffusion_from_conditioning
from fastglycan.hybrid_proposals import identity_noise
from fastglycan.hybrid_geometry import GeometryTopology,hard_accept
from fastglycan.conditioning_diagnostics import weighted_geometry_objectives
from fastglycan.input_interpolation import probability_interpolation,tensor_delta,audit_reference_caches,aligned_rmsd
from fastglycan.near_hard_diagnostics import original_logit_directions,fd_measurement,summarize_directions
from fastglycan.paired_teacher_protocol import sha256,write_json


def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--case',required=True);p.add_argument('--alpha-index',type=int,required=True);p.add_argument('--steps',type=int,choices=[1,2],required=True);a=p.parse_args()
 root=a.root.resolve();lock=rt.load_json(root/'lock.json');alpha=lock['alphas'][a.alpha_index];seq=lock['cases'][a.case]['sequence'];out=root/f'{a.case}_a{a.alpha_index}_s{a.steps}';out.mkdir(exist_ok=False)
 source=Path(__file__).resolve().parents[1]
 for name,h in lock['source_sha256'].items():
  if sha256(source/name)!=h:raise ValueError('source drift '+name)
 started=time.monotonic();report=dict(complete=False,case=a.case,alpha=alpha,steps=a.steps,derivative_space='FP32 logits q;temperature1; full live ERC',lock_sha256=sha256(root/'lock.json'),stage='load',directions=[])
 def save():write_json(out/'report.json',report)
 save();runner=rt.runner_setup(out/'work');model=runner.model.eval().requires_grad_(False)
 if next(model.parameters()).dtype!=torch.float32 or torch.is_autocast_enabled():raise RuntimeError('not FP32 model')
 torch.serialization.add_safe_globals([argparse.Namespace])
 from protenix.data.esm.compute_esm import load_esm_model
 esm,alphabet=load_esm_model('esm2-3b',local_esm_dir=runner.configs.load_checkpoint_dir);esm.eval().requires_grad_(False)
 templates={aa:native_sequence_features(aa*len(seq)) for aa in AMINO_ACIDS};chart=SequenceChart(seq,model,esm,alphabet,templates);topology=GeometryTopology(chart.atoms,chart.native['ref_pos'].cpu().numpy());noise=identity_noise(chart.atoms,211,device='cuda')
 onehot=sequence_probabilities(seq,device='cuda');intended=probability_interpolation(onehot.double(),alpha);q0=intended.log().float();p0=q0.softmax(-1).detach();calls=0;cache_checks=0
 def forward_probability(probability):
  nonlocal calls,cache_checks
  # No input-dependent ESM/conditioning cache: this call executes live soft ESM.
  f=chart.features(probability,check_chart=True);calls+=1
  with audit_reference_caches(model,f) as records:
   point=full_recycle_pairformer(model,f,N_cycle=4,inplace_safe=False,mc_dropout=False)
   shapes=[v.shape for v in point];sizes=[v.numel() for v in point];flat=torch.cat([v.flatten() for v in point]);point=tuple(v.reshape(s) for v,s in zip(flat.split(sizes),shapes))
   x=diffusion_from_conditioning(model,f,noise,point,steps=a.steps)
  cache_checks+=len(records)
  return x,f,point
 def forward(q):
  probability=q.softmax(-1);x,f,point=forward_probability(probability);return probability,x,f,point
 def coordinate_losses(x):
  values=weighted_geometry_objectives(x,chart.ca_indices,topology)
  return {name:values[name] for name in ['old','new']}
 def trust(p):return .01*(p*(p.log()-p0.log())).sum(-1).mean()
 report['stage']='hard_and_near_hard';save()
 with torch.no_grad():
  xhard,fhard,hardpoint=forward_probability(onehot);pbase,xbase,fbase,basepoint=forward(q0)
  _,hard_geometry=topology.terms(xhard);_,geometry=topology.terms(xbase)
  def change(v,b):
   d=tensor_delta(v,b);d['delta_norm']=float((v.double()-b.double()).norm());d['cosine_to_hard']=float(torch.nn.functional.cosine_similarity(v.double().flatten(),b.double().flatten(),dim=0));return d
  ids=torch.tensor([alphabet.get_idx(aa) for aa in AMINO_ACIDS],device='cuda');weights=esm.embed_tokens.weight[ids]
  trace=dict(token_embedding=change(pbase@weights,onehot@weights),esm_output=change(fbase['esm_token_embedding'],fhard['esm_token_embedding']))
  proj=model.input_embedder.linear_esm(fbase['esm_token_embedding']);projhard=model.input_embedder.linear_esm(fhard['esm_token_embedding'])
  trace['projected_esm']=change(proj,projhard);trace['s_inputs']=change(basepoint[0],hardpoint[0])
  trace['projected_delta_cosine_to_sinputs_delta']=float(torch.nn.functional.cosine_similarity((proj-projhard).double().flatten(),(basepoint[0]-hardpoint[0]).double().flatten(),dim=0))
  report.update(hard_geometry=hard_geometry,geometry=geometry,geometry_gate=hard_accept(-1.,0.,geometry,hard_geometry),hard_geometry_gate=hard_accept(-1.,0.,hard_geometry,hard_geometry),
    near_hard_ca_rmsd=aligned_rmsd(xbase[0,chart.ca_indices].cpu().numpy(),xhard[0,chart.ca_indices].cpu().numpy()),input_trace=trace,
    actual_probability_max_error=float((pbase.double()-intended).abs().max()),actual_non_native_mass_mean=float((pbase.double()*(1-onehot.double())).sum(-1).mean()))
  np.savez_compressed(out/'baseline.npz',hard_coordinates=xhard.cpu().numpy(),coordinates=xbase.cpu().numpy(),probabilities=pbase.cpu().numpy(),logits=q0.cpu().numpy(),sequence=seq,
   atom_names=chart.atoms.atom_name,residue_ids=chart.atoms.res_id,chain_ids=chart.atoms.chain_id)
  torch.save(dict(atoms=chart.atoms,reference=chart.native['ref_pos'].cpu(),ca_indices=chart.ca_indices.cpu()),out/'topology.pt')
 del fhard,hardpoint,fbase,basepoint,proj,projhard;save()
 def compute_gradients():
  q=q0.detach().clone().requires_grad_(True);p,x,_,_=forward(q);values=coordinate_losses(x);t=trust(p)
  gt,=torch.autograd.grad(t,q,retain_graph=True)
  gs={};gx={};scalars={}
  for name in ['old','new']:
   cg,=torch.autograd.grad(values[name],x,retain_graph=True)
   loss=values[name]+(t if name=='new' else 0.)
   gradient,=torch.autograd.grad(loss,q,retain_graph=True)
   gs[name]=gradient.detach();gx[name]=cg.detach();scalars[name]=float(loss.detach())
  return gs,gx,gt.detach(),x.detach(),scalars
 report['stage']='autograd';save();gradients,gx,gt,xgrad,point_values=compute_gradients();gc.collect()
 report['grad_no_grad_max_abs']=float((xgrad-xbase).abs().max());report['grad_no_grad_exact']=torch.equal(xgrad,xbase)
 report['stage']='repeat_gradient';save();repeat,_,_,xrepeat,_=compute_gradients();gc.collect()
 stats={name:dict(finite=bool(torch.isfinite(g).all()),norm=float(g.norm()),max_abs=float(g.abs().max()),zero_fraction=float((g==0).float().mean()),repeat_max_abs=float((g-repeat[name]).abs().max())) for name,g in gradients.items()}
 report['gradient_stats']=stats;report['repeated_forward_exact']=torch.equal(xgrad,xrepeat);report['point_losses']=point_values
 directions=list(original_logit_directions(q0,3,731));torch.save(dict(gradients={k:v.cpu() for k,v in gradients.items()},coordinate_gradients={k:v.cpu() for k,v in gx.items()},trust_gradient=gt.cpu(),directions=[v.cpu() for v in directions]),out/'gradients.pt')
 del repeat,xrepeat;torch.cuda.empty_cache();save()
 for direction_index,v in enumerate(directions):
  record=dict(index=direction_index,rows=[]);report['directions'].append(record)
  analytic={name:float((g.double()*v.double()).sum()) for name,g in gradients.items()};trust_ad=float((gt.double()*v.double()).sum())
  for hi,h in enumerate(lock['h']):
   report['stage']=f'fd_direction{direction_index}_h{h}';save()
   with torch.no_grad():
    pp,xp,_,_=forward(q0+h*v);pm,xm,_,_=forward(q0-h*v);lp=coordinate_losses(xp);lm=coordinate_losses(xm);lp['new']=lp['new']+trust(pp);lm['new']=lm['new']+trust(pm)
    dp=pp.double()-pm.double();dx=xp.double()-xm.double();pnorm=float(dp.norm());xnorm=float(dx.norm())
    details={}
    for name in ['old','new']:
     nonlinear=fd_measurement(analytic[name],float(lp[name]),float(lm[name]),h,probability_delta_norm=pnorm,coordinate_delta_norm=xnorm)
     linear_numerator=float((gx[name].double()*dx).sum())+2*h*(trust_ad if name=='new' else 0.)
     linear=fd_measurement(analytic[name],linear_numerator,0.,h,probability_delta_norm=pnorm,coordinate_delta_norm=xnorm)
     details[name]=dict(nonlinear=nonlinear,linearized=linear)
    filename=f'direction{direction_index}_h{hi}.npz';np.savez_compressed(out/filename,coordinates_plus=xp.cpu().numpy(),coordinates_minus=xm.cpu().numpy(),probabilities_plus=pp.cpu().numpy(),probabilities_minus=pm.cpu().numpy())
    record['rows'].append(dict(h=h,probability_delta_norm=pnorm,probability_delta_max_abs=float(dp.abs().max()),coordinate_delta_norm=xnorm,coordinate_delta_rms=float(dx.square().mean().sqrt()),
      probability_min=min(float(pp.min()),float(pm.min())),probability_sum_max_error=max(float((pp.double().sum(-1)-1).abs().max()),float((pm.double().sum(-1)-1).abs().max())),
      objectives=details,coordinate_file=filename,coordinate_sha256=sha256(out/filename)))
   save()
 report['summary']={}
 for name in ['old','new']:
  report['summary'][name]={kind:summarize_directions([[r['objectives'][name][kind] for r in d['rows']] for d in report['directions']],finite=stats[name]['finite'],gradient_norm=stats[name]['norm'],repeat_max_abs=stats[name]['repeat_max_abs']) for kind in ['nonlinear','linearized']}
 report.update(complete=True,stage='complete',full_forward_calls=calls,atom_cache_builder_checks=cache_checks,elapsed_seconds=time.monotonic()-started,peak_memory_gib=torch.cuda.max_memory_allocated()/2**30,
  baseline_sha256=sha256(out/'baseline.npz'),gradients_sha256=sha256(out/'gradients.pt'),topology_sha256=sha256(out/'topology.pt'),model_deployment_accepted=False)
 save()

if __name__=='__main__':main()
