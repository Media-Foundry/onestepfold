#!/usr/bin/env python3
"""Original-logits true JVP/VJP, plus native FP32 archived-trajectory composition."""
import argparse,gc,time
from pathlib import Path
import numpy as np
import torch
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.models.soft_sequence_chart import SequenceChart,native_sequence_features
from fastglycan.models.soft_esm import AMINO_ACIDS
from fastglycan.models.differentiable_mini import full_recycle_pairformer,diffusion_from_conditioning
from fastglycan.esm_interface_diagnostics import early_interface
from fastglycan.interface_decomposition import dot64,rebuild_features,CONDITIONING_NAMES
from fastglycan.pairformer_precision import PairformerStages,cast_tree,tree_dot
from fastglycan.composite_derivatives import without_checkpoint_wrappers,dictionary_jvp,consistency
from fastglycan.hybrid_proposals import identity_noise
from fastglycan.paired_teacher_protocol import sha256,write_json


def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root.resolve();out=root/'composite';out.mkdir(exist_ok=False)
 lock=rt.load_json(root/'lock.json');prior=Path(lock['prior_root']);near=Path(lock['near_root']);earlyroot=Path('/media/PM982/onestepfold/mini_esm_interface_v1_20260928');lateroot=Path('/media/PM982/onestepfold/mini_interface_decomposition_v1_20260928')
 assert rt.load_json(root/'run/report.json')['complete']
 statesfile=prior/'run/coarse_baseline.pt';assert sha256(statesfile)==rt.load_json(prior/'run/report.json')['baseline_sha256'];stored=torch.load(statesfile,map_location='cpu',weights_only=False)
 eb=torch.load(earlyroot/'control/baseline.pt',map_location='cpu',weights_only=False);lb=torch.load(lateroot/'control/baseline.pt',map_location='cpu',weights_only=False);old=np.load(near/'control_a1_s1/baseline.npz');w=lb['w'].cuda();seq=rt.load_json(near/'lock.json')['cases']['control']['sequence']
 report=dict(complete=False,stage='load',directions=[],source_sha256=sha256(Path(__file__)),reference_kind='native FP32 trajectory, true forward AD; not full FP64 model',input_sha256={str(f):sha256(f) for f in [statesfile,earlyroot/'control/baseline.pt',lateroot/'control/baseline.pt',near/'control_a1_s1/baseline.npz']});start=time.monotonic()
 def save():write_json(out/'report.json',report)
 save();runner=rt.runner_setup(out/'work');model=runner.model.eval().requires_grad_(False);torch.serialization.add_safe_globals([argparse.Namespace])
 from protenix.data.esm.compute_esm import load_esm_model
 esm,alphabet=load_esm_model('esm2-3b',local_esm_dir=runner.configs.load_checkpoint_dir);esm.eval().requires_grad_(False)
 templates={aa:native_sequence_features(aa*len(seq)) for aa in AMINO_ACIDS};chart=SequenceChart(seq,model,esm,alphabet,templates);engine=PairformerStages(model,chart.native).eval();noise=identity_noise(chart.atoms,211,device='cuda')
 q0=eb['q'].cuda();directions=[x.cuda() for x in eb['directions']];states=cast_tree(stored['states'],torch.float32,'cuda');adjoints=cast_tree(stored['adjoints'],torch.float32,'cuda');late=cast_tree(lb['interface'],torch.float32,'cuda')
 def pack(point):
  shapes=[x.shape for x in point];sizes=[x.numel() for x in point];flat=torch.cat([x.flatten() for x in point]);return tuple(x.reshape(s) for x,s in zip(flat.split(sizes),shapes))
 def full(q):
  f=chart.features(q.softmax(-1),check_chart=False);point=full_recycle_pairformer(model,f,N_cycle=4,inplace_safe=False,mc_dropout=False)
  return diffusion_from_conditioning(model,f,noise,pack(point),steps=1)
 def early(q):return early_interface(chart.features(q.softmax(-1),check_chart=False))
 def decode(b):return diffusion_from_conditioning(model,rebuild_features(chart.native,b),noise,pack(tuple(b[k] for k in CONDITIONING_NAMES)),steps=1)
 report['stage']='native_vjp';save();q=q0.detach().requires_grad_(True);x=full(q);g,=torch.autograd.grad(dot64(w,x),q);g=g.detach();x0=x.detach();del x,q;gc.collect();torch.cuda.empty_cache()
 report.update(native_archive_exact=torch.equal(x0.cpu(),torch.from_numpy(old['coordinates'])),native_archive_max_abs=float((x0.cpu()-torch.from_numpy(old['coordinates'])).abs().max()),gradient_finite=bool(torch.isfinite(g).all()),gradient_norm=float(g.norm()),archived_gradient_max_abs=float((g.cpu()-lb['direct']).abs().max()))
 assert report['native_archive_exact'],'native primal no longer replays archived coordinates'
 torch.save(dict(q=q0.cpu(),gradient=g.cpu(),w=w.cpu(),coordinates=x0.cpu(),directions=eb['directions']),out/'baseline.pt');save()
 for di,v in enumerate(directions):
  report['stage']=f'direction{di}';save();row=dict(direction=di,analytic=float(dot64(g,v)),boundaries=[]);tensors={}
  with without_checkpoint_wrappers(model):
   try:
    primal,tangent=torch.func.jvp(full,(q0,),(v,));value=float(dot64(w,tangent));row['full_jvp']=dict(supported=True,primal_exact=torch.equal(primal,x0),primal_max_abs=float((primal-x0).abs().max()),tangent_norm=float(tangent.norm()),comparison=consistency(value,row['analytic']));tensors['full_coordinate_tangent']=tangent.detach().cpu();del primal,tangent
   except (RuntimeError,NotImplementedError) as error:row['full_jvp']=dict(supported=False,error=str(error))
   try:
    names=list(states[0])
    primal_values,tangent_values=torch.func.jvp(lambda q:tuple(early(q).values()),(q0,),(v,));cp=dict(zip(names,primal_values));ct=dict(zip(names,tangent_values))
    exact=all(torch.equal(cp[k],states[0][k]) for k in cp);projection=float(tree_dot(adjoints[0],ct));row['boundaries'].append(dict(name='early',primal_exact=exact,projection=projection,comparison=consistency(projection,row['analytic'])));assert exact,'early native trajectory mismatch'
    tensors['early']=cast_tree(ct,torch.float32,'cpu')
    current=ct
    for stage in range(5):
     primal,current=dictionary_jvp(lambda state,stage=stage:engine.step(stage,state),states[stage],current)
     exact=all(torch.equal(primal[k],states[stage+1][k]) for k in primal);projection=float(tree_dot(adjoints[stage+1],current));name='initialization' if stage==0 else f'recycle{stage}'
     row['boundaries'].append(dict(name=name,primal_exact=exact,projection=projection,comparison=consistency(projection,row['analytic'])));assert exact,name+' native trajectory mismatch';tensors[name]=cast_tree(current,torch.float32,'cpu')
    bt=engine.final(current);names=list(late)
    primal,dx=torch.func.jvp(lambda *values:decode(dict(zip(names,values))),tuple(late.values()),tuple(bt[k] for k in names));projection=float(dot64(w,dx));exact=torch.equal(primal,x0)
    row['boundaries'].append(dict(name='coordinates',primal_exact=exact,primal_max_abs=float((primal-x0).abs().max()),projection=projection,comparison=consistency(projection,row['analytic'])));tensors['composed_coordinate_tangent']=dx.detach().cpu()
    row['composition']=dict(supported=True,all_primals_exact=all(z['primal_exact'] for z in row['boundaries']),all_projection_checks_pass=all(z['comparison']['passed'] for z in row['boundaries']),comparison=consistency(projection,row['analytic']))
    if 'full_coordinate_tangent' in tensors:
     delta=tensors['composed_coordinate_tangent'].double()-tensors['full_coordinate_tangent'].double();row['full_vs_composed_tangent']=dict(absolute_l2=float(delta.norm()),relative_l2=float(delta.norm()/tensors['full_coordinate_tangent'].double().norm()),max_abs=float(delta.abs().max()))
   except (RuntimeError,NotImplementedError,AssertionError) as error:row['composition']=dict(supported=False,error=str(error))
  filename=f'direction{di}.pt';torch.save(tensors,out/filename);row.update(artifact=filename,artifact_sha256=sha256(out/filename));report['directions'].append(row);save();gc.collect();torch.cuda.empty_cache()
 report.update(complete=True,stage='complete',elapsed_seconds=time.monotonic()-start,peak_memory_gib=torch.cuda.max_memory_allocated()/2**30,baseline_sha256=sha256(out/'baseline.pt'),model_deployment_accepted=False);save()
if __name__=='__main__':main()
