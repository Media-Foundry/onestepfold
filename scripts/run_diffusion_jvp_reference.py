#!/usr/bin/env python3
"""Bounded math-SDPA forward-AD reference at the complete diffusion interface."""
import argparse,json,time
from pathlib import Path
from contextlib import nullcontext
import torch
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.models.soft_sequence_chart import native_sequence_features,device_tree
from fastglycan.models.differentiable_mini import diffusion_from_conditioning
from fastglycan.interface_decomposition import rebuild_features,CONDITIONING_NAMES,dot64
from fastglycan.pairformer_precision import cast_tree,tree_dot
from fastglycan.composite_derivatives import dictionary_jvp,consistency,without_checkpoint_wrappers
from fastglycan.hybrid_proposals import identity_noise
from fastglycan.vjp_comparison import compare_fields,vector_metrics
from fastglycan.paired_teacher_protocol import sha256,write_json

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);root=p.parse_args().root.resolve();out=root/'diffusion_jvp_reference';out.mkdir(exist_ok=False);start=time.monotonic()
 r=dict(complete=False,stage='load',rows=[],source_sha256=sha256(Path(__file__)),reference_kind='FP32 math SDPA diffusion; native FP32 upstream true tangents',model_deployment_accepted=False)
 def save():write_json(out/'report.json',r)
 save();cr=rt.load_json(root/'composite/report.json');assert cr['complete'];cb=torch.load(root/'composite/baseline.pt',map_location='cpu',weights_only=False);assert sha256(root/'composite/baseline.pt')==cr['baseline_sha256']
 lf=Path('/media/PM982/onestepfold/mini_interface_decomposition_v1_20260928/control/baseline.pt');lb=torch.load(lf,map_location='cpu',weights_only=False);assert sha256(lf)==cr['input_sha256'][str(lf)]
 near=Path(rt.load_json(root/'lock.json')['near_root']);seq=rt.load_json(near/'lock.json')['cases']['control']['sequence'];runner=rt.runner_setup(out/'work');model=runner.model.eval().requires_grad_(False);native,atoms=native_sequence_features(seq);native=model.relative_position_encoding.generate_relp(device_tree(native,'cuda'));noise=identity_noise(atoms,211,device='cuda');b=cast_tree(lb['interface'],torch.float32,'cuda');w=cb['w'].cuda()
 def decode(b):
  point=tuple(b[k] for k in CONDITIONING_NAMES);sizes=[x.numel() for x in point];shapes=[x.shape for x in point];flat=torch.cat([x.flatten() for x in point]);point=tuple(x.reshape(s) for x,s in zip(flat.split(sizes),shapes))
  return diffusion_from_conditioning(model,rebuild_features(native,b),noise,point,steps=1)
 def math_context():return torch.nn.attention.sdpa_kernel([torch.nn.attention.SDPBackend.MATH])
 ys={};gs={}
 for mode in ['native32','math32']:
  x={k:v.detach().requires_grad_(True) for k,v in b.items()}
  with math_context() if mode=='math32' else nullcontext():
   y=decode(x);gg=torch.autograd.grad(dot64(w,y),tuple(x.values()),allow_unused=True)
  ys[mode]=y.detach().cpu();gs[mode]={k:(torch.zeros_like(v) if g is None else g).detach().cpu() for (k,v),g in zip(x.items(),gg)}
 r.update(native_archive_exact=torch.equal(ys['native32'],cb['coordinates']),primal_comparison=vector_metrics(ys['native32'],ys['math32']),full_vjp_comparison=compare_fields(gs['native32'],gs['math32']));assert r['native_archive_exact'];save()
 torch.save(dict(outputs=ys,gradients=gs,w=cb['w'],interface=lb['interface']),out/'baseline.pt')
 for row in cr['directions']:
  f=root/'composite'/row['artifact'];assert sha256(f)==row['artifact_sha256'];packet=torch.load(f,map_location='cpu',weights_only=False);state=packet['recycle4'];t={k:state[k] for k in CONDITIONING_NAMES};t.update({k:state[k] for k in b if k not in t});tg=cast_tree(t,torch.float32,'cuda')
  with without_checkpoint_wrappers(model),math_context():primal,tangent=dictionary_jvp(lambda b:{'coordinates':decode(b)},b,tg)
  dx=tangent['coordinates'];project=float(dot64(w,dx));native_vjp=float(tree_dot(gs['native32'],t));ref_vjp=float(tree_dot(gs['math32'],t))
  rr=dict(direction=row['direction'],original_q_vjp=row['analytic'],native_interface_vjp=native_vjp,reference_interface_vjp=ref_vjp,reference_jvp=project,primal_matches_reference=torch.equal(primal['coordinates'].cpu(),ys['math32']),jvp_vjp=consistency(project,ref_vjp),backend_projection=consistency(ref_vjp,native_vjp),original_q_comparison=consistency(project,row['analytic']))
  filename=f'direction{row["direction"]}.pt';torch.save(dict(tangent=t,coordinate_tangent=dx.cpu()),out/filename);rr.update(artifact=filename,artifact_sha256=sha256(out/filename));r['rows'].append(rr);save()
 r.update(complete=True,stage='complete',elapsed_seconds=time.monotonic()-start,peak_memory_gib=torch.cuda.max_memory_allocated()/2**30,baseline_sha256=sha256(out/'baseline.pt'),composite_report_sha256=sha256(root/'composite/report.json'));save()
if __name__=='__main__':main()
