#!/usr/bin/env python3
"""ESM coarse boundaries followed by one frozen-endpoint precision experiment."""
import argparse,gc,inspect,time
from pathlib import Path
import torch
from fastglycan.models.soft_esm import soft_esm2
from fastglycan.interface_decomposition import dot64
from fastglycan.esm_precision_reference import Segment,precision_copy,reference_softmax,FloatingDtypeAudit,precision_decomposition
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan import stage0_confirm_runtime as rt


def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root.resolve();out=root/'run';out.mkdir(exist_ok=False)
 lock=rt.load_json(root/'lock.json');prior=Path(lock['prior_root']);previous=rt.load_json(prior/'control/report.json')
 source=Path(__file__).resolve().parents[1]
 for f,h in lock['source_sha256'].items():assert sha256(source/f)==h,f
 for f,h in lock['input_sha256'].items():assert sha256(prior/f)==h,f
 base=torch.load(prior/'control/baseline.pt',map_location='cpu',weights_only=False)
 report=dict(complete=False,stage='load',coarse_rows=[],precision_rows=[],lock_sha256=sha256(root/'lock.json'));start=time.monotonic()
 def save():write_json(out/'report.json',report)
 save();torch.serialization.add_safe_globals([argparse.Namespace])
 from protenix.data.esm.compute_esm import load_esm_model
 esm,alphabet=load_esm_model('esm2-3b',local_esm_dir='/media/PM982/onestepfold/protenix_stage0_pkg/v1_1/runtime/checkpoint');esm.eval().requires_grad_(False)
 import esm.multihead_attention as attention
 import esm.rotary_embedding as rotary
 import esm.modules as modules
 report['runtime']=dict(torch_version=torch.__version__,hip=torch.version.hip,device=torch.cuda.get_device_name(),matmul_precision=torch.get_float32_matmul_precision(),allow_tf32=torch.backends.cuda.matmul.allow_tf32,
  sources={m.__name__:dict(path=inspect.getfile(m),sha256=sha256(Path(inspect.getfile(m)))) for m in [attention,rotary,modules]},
  norms={n:dict(class_name=type(m).__module__+'.'+type(m).__name__,eps=m.eps,shape=list(m.weight.shape)) for n,m in esm.named_modules() if 'LayerNorm' in type(m).__name__})
 assert next(esm.parameters()).dtype==torch.float32 and not torch.is_autocast_enabled()
 count=len(esm.layers);ends=[count//3,2*count//3,count];names=['input']+[f'after_{i}' for i in ends]+['after_norm'];q0=base['q'].cuda();mu=base['mu']['esm_token_embedding'].cuda();directions=[v.cuda() for v in base['directions']]
 def capture(q):
  states=[];handles=[]
  handles.append(esm.layers[0].register_forward_pre_hook(lambda m,args:states.append(args[0])))
  for endpoint in ends:handles.append(esm.layers[endpoint-1].register_forward_hook(lambda m,args,result:states.append(result[0])))
  handles.append(esm.emb_layer_norm_after.register_forward_hook(lambda m,args,result:states.append(result)))
  try:H=soft_esm2(esm,alphabet,q.softmax(-1))
  finally:
   for handle in handles:handle.remove()
  assert len(states)==5
  return H,states
 report['stage']='coarse_baseline';save();q=q0.detach().requires_grad_(True);H,states=capture(q)
 grads=torch.autograd.grad(dot64(mu,H),tuple(states))
 assert torch.equal(H.detach().cpu(),base['early']['esm_token_embedding'])
 basestates=[x.detach().cpu() for x in states];lambdas=[g.detach().cpu() for g in grads]
 torch.save(dict(states=basestates,lambdas=lambdas,names=names,q=base['q'],directions=base['directions'],mu=mu.cpu()),out/'coarse_baseline.pt')
 report['coarse_baseline_exact']=True;report['boundaries']=names
 del H,states,q,grads;gc.collect();torch.cuda.empty_cache()
 for row in previous['rows']:
  di=row['direction'];h=row['h'];v=directions[di];report['stage']=f'capture_direction{di}_h{h}';save()
  with torch.no_grad():
   hp,sp=capture(q0+h*v);hm,sm=capture(q0-h*v)
   oldfile=prior/'control'/row['artifact'];assert sha256(oldfile)==row['artifact_sha256'];old_delta=torch.load(oldfile,map_location='cpu',weights_only=False)['esm_token_embedding']
   exact=torch.equal((hp.double()-hm.double()).cpu(),old_delta);assert exact,'ESM difference replay failed'
   plus=[x.cpu() for x in sp];minus=[x.cpu() for x in sm]
   c=[float(dot64(g,p.double()-m.double())/(2*h)) for g,p,m in zip(lambdas,plus,minus)]
   errors=[y-x for x,y in zip(c[:-1],c[1:])]
   filename=f'endpoints_d{di}_h{h}.pt';torch.save(dict(plus=plus,minus=minus),out/filename)
   report['coarse_rows'].append(dict(direction=di,h=h,projections=c,deviations=errors,numerator_deviations=[2*h*x for x in errors],output_delta_exact=exact,artifact=filename,artifact_sha256=sha256(out/filename)))
   del hp,hm,sp,sm,plus,minus,old_delta
  save()
 primary=next(r for r in report['coarse_rows'] if r['direction']==0 and r['h']==.003);selected=max(range(4),key=lambda i:abs(primary['deviations'][i]));report['selected_segment']=selected
 if selected==3:native=Segment(norm=esm.emb_layer_norm_after)
 else:
  lo=0 if selected==0 else ends[selected-1];hi=ends[selected];native=Segment(layers=list(esm.layers[lo:hi]))
 native.eval().requires_grad_(False)
 report['selection']=dict(rule='max_abs_deviation_direction0_h0.003_earliest_tie',start=names[selected],end=names[selected+1],value=primary['deviations'][selected])
 # Snapshot native cached constants before any dtype lifting.
 rope={n:dict(cos=m._cos_cached.detach().cpu(),sin=m._sin_cached.detach().cpu(),seq_len=m._seq_len_cached) for n,m in native.named_modules() if hasattr(m,'_cos_cached')}
 torch.save(rope,out/'native_rope.pt');del esm,capture;gc.collect();torch.cuda.empty_cache()
 ref32,repl32=precision_copy(native,torch.float32);ref64,repl64=precision_copy(native,torch.float64)
 report['layernorm_replacements']=dict(ref32=repl32,ref64=repl64)
 u0=basestates[selected].cuda();output_mu=lambdas[selected+1].cuda();g32=None;gradients={};baseline_outputs={}
 for label,segment,dtype in [('native32',native,torch.float32),('reference32',ref32,torch.float32),('reference64',ref64,torch.float64)]:
  report['stage']='baseline_'+label;save();leaf=u0.to(dtype).detach().requires_grad_(True)
  if label=='native32':value=segment(leaf);g,=torch.autograd.grad(dot64(output_mu,value),leaf)
  else:
   with reference_softmax():value=segment(leaf);g,=torch.autograd.grad(dot64(output_mu,value),leaf)
  gradients[label]=g.detach();baseline_outputs[label]=value.detach().cpu()
 assert torch.equal(baseline_outputs['native32'],basestates[selected+1]),'native segment baseline mismatch'
 local_chain=gradients['native32'].cpu()-lambdas[selected]
 report['native_local_chain_max_abs']=float(local_chain.abs().max());report['native_local_chain_relative_l2']=float(local_chain.norm()/lambdas[selected].norm())
 assert float(local_chain.norm())<=1e-10+1e-4*float(lambdas[selected].norm())
 report['reference32_baseline_max_abs']=float((baseline_outputs['reference32']-baseline_outputs['native32']).abs().max())
 audit=FloatingDtypeAudit();softmax_records=[]
 with torch.no_grad(),reference_softmax(softmax_records),audit:ref64(u0.double())
 report['dtype_audit']=dict(counts=audit.counts,non_double=audit.non_double,softmax_records=softmax_records)
 assert not audit.non_double,'hidden low-precision operator'
 assert all(x==('torch.float64','torch.float64') for x in softmax_records)
 if selected!=3:assert len(softmax_records)==len(ref64.layers)
 torch.save(dict(gradients={k:g.cpu() for k,g in gradients.items()},outputs=baseline_outputs,u0=u0.cpu(),mu=output_mu.cpu()),out/'precision_baseline.pt')
 for row in report['coarse_rows']:
  di=row['direction'];h=row['h'];report['stage']=f'precision_direction{di}_h{h}';save()
  packet=torch.load(out/row['artifact'],map_location='cpu',weights_only=False);up=packet['plus'][selected].cuda();um=packet['minus'][selected].cuda();vh=(up.double()-um.double())/(2*h)
  values={};outputs={};jvps={}
  for label,segment,dtype in [('native32',native,torch.float32),('reference32',ref32,torch.float32),('reference64',ref64,torch.float64)]:
   with torch.no_grad():
    if label=='native32':yp=segment(up);ym=segment(um)
    else:
     with reference_softmax():yp=segment(up.to(dtype));ym=segment(um.to(dtype))
    s=float(dot64(output_mu,yp.double()-ym.double())/(2*h));ad=float(dot64(gradients[label],vh))
   values[label]=dict(S=s,A=ad);outputs[label]=dict(plus=yp.cpu(),minus=ym.cpu())
   if label!='native32':
    vd=vh.to(dtype)
    try:
     with reference_softmax():_,tangent=torch.func.jvp(segment,(u0.to(dtype),),(vd,))
     j=float(dot64(output_mu,tangent));reverse=float(dot64(gradients[label],vd));jvps[label]=dict(supported=True,jvp=j,vjp_same_cast=reverse,absolute_error=abs(j-reverse),relative_error=abs(j-reverse)/max(abs(j),abs(reverse),1e-30),direction_cast_l2=float((vd.double()-vh).norm()),tangent_norm=float(tangent.norm()));del tangent
    except (NotImplementedError,RuntimeError) as error:
     jvps[label]=dict(supported=False,error=str(error))
  native_exact=torch.equal(outputs['native32']['plus'],packet['plus'][selected+1]) and torch.equal(outputs['native32']['minus'],packet['minus'][selected+1]);assert native_exact,'native frozen-endpoint replay mismatch'
  s32=values['native32']['S'];a32=values['native32']['A'];s64=values['reference64']['S'];a64=values['reference64']['A']
  midpoint=(up.double()+um.double())/2-u0.double();radius=max(float((up.double()-u0.double()).norm()),float((um.double()-u0.double()).norm()))
  filename=f'precision_d{di}_h{h}.pt';torch.save(outputs,out/filename)
  result=precision_decomposition(s32,a32,s64,a64,h)|dict(direction=di,h=h,values=values,jvp=jvps,midpoint_offset_norm=float(midpoint.norm()),endpoint_radius=radius,secant_direction_norm=float(vh.norm()),native_endpoint_exact=native_exact,
   reference32_plus_max_abs=float((outputs['reference32']['plus']-outputs['native32']['plus']).abs().max()),reference32_minus_max_abs=float((outputs['reference32']['minus']-outputs['native32']['minus']).abs().max()),artifact=filename,artifact_sha256=sha256(out/filename))
  report['precision_rows'].append(result);save()
 report.update(complete=True,stage='complete',elapsed_seconds=time.monotonic()-start,peak_memory_gib=torch.cuda.max_memory_allocated()/2**30,model_deployment_accepted=False,
  baseline_sha256=sha256(out/'coarse_baseline.pt'),precision_baseline_sha256=sha256(out/'precision_baseline.pt'),rope_sha256=sha256(out/'native_rope.pt'))
 save()
if __name__=='__main__':main()
