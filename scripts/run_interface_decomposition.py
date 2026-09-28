#!/usr/bin/env python3
"""Two archived failure points; complete conditioning-cut secant attribution."""
import argparse,gc,json,time
from pathlib import Path
import numpy as np
import torch
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.models.soft_esm import AMINO_ACIDS
from fastglycan.models.soft_sequence_chart import SequenceChart,native_sequence_features
from fastglycan.models.differentiable_mini import full_recycle_pairformer,diffusion_from_conditioning
from fastglycan.hybrid_proposals import identity_noise
from fastglycan.interface_decomposition import (INTERFACE_NAMES,CONDITIONING_NAMES,make_interface,
    rebuild_features,detached_interface,dot64,decompose_response)
from fastglycan.paired_teacher_protocol import sha256,write_json


def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--case',choices=['control','8bzn'],required=True);a=p.parse_args()
 root=a.root.resolve();lock=rt.load_json(root/'lock.json');archive=Path(lock['archive_root']);old=archive/f'{a.case}_a1_s1';out=root/a.case;out.mkdir(exist_ok=False)
 source=Path(__file__).resolve().parents[1]
 for path,h in lock['source_sha256'].items():
  assert sha256(source/path)==h,path
 for path,h in lock['input_sha256'].items():assert sha256(archive/path)==h,path
 oldlock=rt.load_json(archive/'lock.json');seq=oldlock['cases'][a.case]['sequence'];saved=np.load(old/'baseline.npz');prior=torch.load(old/'gradients.pt',map_location='cpu',weights_only=False)
 report=dict(complete=False,case=a.case,stage='load',rows=[],lock_sha256=sha256(root/'lock.json'));start=time.monotonic()
 def save():write_json(out/'report.json',report)
 save();runner=rt.runner_setup(out/'work');model=runner.model.eval().requires_grad_(False)
 torch.serialization.add_safe_globals([argparse.Namespace])
 from protenix.data.esm.compute_esm import load_esm_model
 esm,alphabet=load_esm_model('esm2-3b',local_esm_dir=runner.configs.load_checkpoint_dir);esm.eval().requires_grad_(False)
 assert next(model.parameters()).dtype==torch.float32 and not torch.is_autocast_enabled()
 templates={aa:native_sequence_features(aa*len(seq)) for aa in AMINO_ACIDS};chart=SequenceChart(seq,model,esm,alphabet,templates)
 noise=identity_noise(chart.atoms,211,device='cuda');q0=torch.from_numpy(saved['logits']).cuda();w=prior['coordinate_gradients']['new'].cuda();directions=[v.cuda() for v in prior['directions']]
 fixed={k:v.detach() if isinstance(v,torch.Tensor) else v for k,v in chart.native.items()}
 reads=set()
 class ReadDict(dict):
  def __getitem__(self,k):reads.add(k);return super().__getitem__(k)
 def upstream(q):
  f=chart.features(q.softmax(-1),check_chart=True)
  point=full_recycle_pairformer(model,f,N_cycle=4,inplace_safe=False,mc_dropout=False)
  shapes=[x.shape for x in point];sizes=[x.numel() for x in point];flat=torch.cat([x.flatten() for x in point]);point=tuple(x.reshape(s) for x,s in zip(flat.split(sizes),shapes))
  return make_interface(point,f),f,point
 def downstream(b):
  f=ReadDict(rebuild_features(fixed,b))
  return diffusion_from_conditioning(model,f,noise,tuple(b[k] for k in CONDITIONING_NAMES),steps=1)
 report['stage']='baseline_cut_and_chain';save()
 q=q0.detach().requires_grad_(True);b,f,point=upstream(q)
 original=diffusion_from_conditioning(model,f,noise,point,steps=1)
 direct,=torch.autograd.grad(dot64(w,original),q,retain_graph=True)
 leaves=detached_interface(b);cut=downstream(leaves)
 lam_values=torch.autograd.grad(dot64(w,cut),tuple(leaves.values()),allow_unused=True)
 lam={k:(torch.zeros_like(leaves[k]) if v is None else v).detach() for k,v in zip(INTERFACE_NAMES,lam_values)}
 chain,=torch.autograd.grad(tuple(b.values()),q,grad_outputs=tuple(lam.values()))
 error=chain-direct
 report.update(cut_forward_exact=torch.equal(cut,original),cut_forward_max_abs=float((cut-original).abs().max()),chain_max_abs=float(error.abs().max()),chain_l2_error=float(error.norm()),direct_gradient_norm=float(direct.norm()),chain_relative_l2_error=float(error.norm()/direct.norm()),
  archived_forward_max_abs=float((original.detach().cpu()-torch.from_numpy(saved['coordinates'])).abs().max()),
  archived_coordinate_gradient_max_abs=float((direct.cpu()-(prior['gradients']['new']-prior['trust_gradient'])).abs().max()),
  interface_fields=list(INTERFACE_NAMES),downstream_feature_reads=sorted(reads),unused_interface_fields=[k for k,v in zip(INTERFACE_NAMES,lam_values) if v is None])
 # Verify there are no q-dependent direct diffusion reads omitted from the cut.
 allowed=set(INTERFACE_NAMES)|{'d_lm','v_lm','pad_info'}
 omitted=[k for k in reads if isinstance(f.get(k),torch.Tensor) and f[k].requires_grad and k not in allowed]
 report['omitted_differentiable_reads']=omitted
 torch.save(dict(interface={k:v.detach().cpu() for k,v in b.items()},lambda_={k:v.cpu() for k,v in lam.items()},w=w.cpu(),q=q0.cpu(),directions=prior['directions'],direct=direct.cpu(),chain=chain.cpu(),trust_gradient=prior['trust_gradient']),out/'baseline.pt')
 save()
 assert not omitted,omitted
 assert report['cut_forward_exact'],'cut changes forward'
 assert report['chain_l2_error'] <= 1e-10+1e-4*report['direct_gradient_norm'],'chain reconstruction failure'
 direct=direct.detach();del q,b,f,point,original,cut,leaves,chain,error,lam_values;gc.collect();torch.cuda.empty_cache()
 max_replay=0.;max_cpu=0.
 for di,v in enumerate(directions):
  analytic=float(dot64(direct,v));trust_ad=float(dot64(prior['trust_gradient'].cuda(),v))
  for hi,h in enumerate(oldlock['h']):
   report['stage']=f'direction{di}_h{h}';save()
   with torch.no_grad():
    bp,fp,pp=upstream(q0+h*v);xp=downstream(bp)
    bm,fm,pm=upstream(q0-h*v);xm=downstream(bm)
    delta={k:bp[k].double()-bm[k].double() for k in INTERFACE_NAMES};dx=xp.double()-xm.double()
    components={k:float(dot64(lam[k],delta[k])/(2*h)) for k in INTERFACE_NAMES}
    m=sum(components.values());d=float(dot64(w,dx)/(2*h))
    oldcoords=np.load(old/f'direction{di}_h{hi}.npz')
    replay=max(float((xp.cpu()-torch.from_numpy(oldcoords['coordinates_plus'])).abs().max()),float((xm.cpu()-torch.from_numpy(oldcoords['coordinates_minus'])).abs().max()));max_replay=max(max_replay,replay)
    payload=dict(delta={k:dv.cpu() for k,dv in delta.items()},coordinate_delta=dx.cpu(),coordinates_plus=xp.cpu(),coordinates_minus=xm.cpu())
    filename=f'direction{di}_h{hi}.pt';torch.save(payload,out/filename)
    cpu_components={k:float(dot64(lam[k].cpu(),payload['delta'][k])/(2*h)) for k in INTERFACE_NAMES}
    cpu_d=float(dot64(w.cpu(),payload['coordinate_delta'])/(2*h));cpu_error=max(abs(cpu_d-d),*(abs(cpu_components[k]-components[k]) for k in components));max_cpu=max(max_cpu,cpu_error)
    row=decompose_response(analytic,m,d)|dict(direction=di,h=h,components=components,component_delta_norms={k:float(dv.norm()) for k,dv in delta.items()},coordinate_delta_norm=float(dx.norm()),trust_ad=trust_ad,archived_forward_max_abs=replay,cpu_projection_error=cpu_error,artifact=filename,artifact_sha256=sha256(out/filename))
    report['rows'].append(row)
    del bp,bm,fp,fm,pp,pm,xp,xm,delta,dx,payload
   save()
 report.update(complete=True,stage='complete',max_archived_perturbed_replay_error=max_replay,max_cpu_projection_error=max_cpu,elapsed_seconds=time.monotonic()-start,baseline_sha256=sha256(out/'baseline.pt'),model_deployment_accepted=False)
 save()
if __name__=='__main__':main()
