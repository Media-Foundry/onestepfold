#!/usr/bin/env python3
"""Extended recycle states and one selected frozen-endpoint precision experiment."""
import argparse,copy,gc,inspect,time
from pathlib import Path
import torch
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.models.soft_esm import AMINO_ACIDS
from fastglycan.models.soft_sequence_chart import SequenceChart,native_sequence_features
from fastglycan.models.differentiable_mini import full_recycle_pairformer
from fastglycan.esm_interface_diagnostics import early_interface,early_features,EARLY_NAMES
from fastglycan.interface_decomposition import make_interface
from fastglycan.pairformer_precision import PairformerStages,cast_tree,pullback,tree_dot,reference_copy,reference_attention
from fastglycan.esm_precision_reference import FloatingDtypeAudit,precision_decomposition
from fastglycan.paired_teacher_protocol import sha256,write_json


def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root.resolve();out=root/'run';out.mkdir(exist_ok=False)
 lock=rt.load_json(root/'lock.json');earlyroot=Path(lock['early_root']);lateroot=Path(lock['late_root']);nearroot=Path(lock['near_root'])
 for f,h in lock['source_sha256'].items():assert sha256(Path(__file__).resolve().parents[1]/f)==h,f
 for f,h in lock['input_sha256'].items():assert sha256(Path(f))==h,f
 prior=rt.load_json(lateroot/'control/report.json');ebase=torch.load(earlyroot/'control/baseline.pt',map_location='cpu',weights_only=False);lbase=torch.load(lateroot/'control/baseline.pt',map_location='cpu',weights_only=False)
 seq=rt.load_json(nearroot/'lock.json')['cases']['control']['sequence'];report=dict(complete=False,stage='load',coarse_rows=[],precision_rows=[],lock_sha256=sha256(root/'lock.json'));start=time.monotonic()
 def save():write_json(out/'report.json',report)
 save();runner=rt.runner_setup(out/'work');model=runner.model.eval().requires_grad_(False);torch.serialization.add_safe_globals([argparse.Namespace])
 from protenix.data.esm.compute_esm import load_esm_model
 esm,alphabet=load_esm_model('esm2-3b',local_esm_dir=runner.configs.load_checkpoint_dir);esm.eval().requires_grad_(False)
 templates={aa:native_sequence_features(aa*len(seq)) for aa in AMINO_ACIDS};chart=SequenceChart(seq,model,esm,alphabet,templates)
 engine=PairformerStages(model,chart.native).eval();q0=ebase['q'].cuda();directions=[v.cuda() for v in ebase['directions']];lam={k:v.cuda() for k,v in lbase['lambda_'].items()}
 import protenix.model.modules.primitives as primitives
 import protenix.model.modules.pairformer as pairformer
 import protenix.model.triangular.layers as triangular_layers
 report['runtime']=dict(torch=torch.__version__,hip=torch.version.hip,device=torch.cuda.get_device_name(),matmul_precision=torch.get_float32_matmul_precision(),allow_tf32=torch.backends.cuda.matmul.allow_tf32,msa_blocks=model.msa_module.n_blocks,template_blocks=model.template_embedder.n_blocks,pairformer_blocks=model.pairformer_stack.n_blocks,
  triangle_multiplicative=model.configs.triangle_multiplicative,triangle_attention=model.configs.triangle_attention,
  norms={n:dict(class_name=type(m).__module__+'.'+type(m).__name__,eps=getattr(m,'eps',None)) for n,m in model.named_modules() if 'LayerNorm' in type(m).__name__},
  sources={m.__name__:dict(path=inspect.getfile(m),sha256=sha256(Path(inspect.getfile(m)))) for m in [primitives,pairformer,triangular_layers]})
 report['stage']='baseline_replay_and_adjoint';save()
 with torch.no_grad():
  f0=chart.features(q0.softmax(-1));c0=early_interface(f0);states=engine.trace(c0);final=engine.final(states[-1]);point=full_recycle_pairformer(model,f0,N_cycle=4,inplace_safe=False,mc_dropout=False);native=make_interface(point,f0)
  assert all(torch.equal(final[k],native[k]) and torch.equal(final[k].cpu(),lbase['interface'][k]) for k in final)
  assert all(torch.equal(c0[k].cpu(),ebase['early'][k]) for k in c0)
 # Direct native early-interface VJP and independently detached stage pullbacks.
 def native_path(c):
  f=early_features(chart.native,c);point=full_recycle_pairformer(model,f,N_cycle=4,inplace_safe=False,mc_dropout=False)
  return make_interface(point,f)
 direct,_=pullback(native_path,c0,lam)
 adjoints=[None]*6;adjoints[-1],_=pullback(engine.final,states[-1],lam)
 for i in reversed(range(5)):adjoints[i],replay=pullback(lambda state,i=i:engine.step(i,state),states[i],adjoints[i+1]);assert all(torch.equal(replay[k],states[i+1][k]) for k in replay)
 def difference(x,y):
  err=sum((x[k].double()-y[k].double()).square().sum() for k in x).sqrt();norm=sum(y[k].double().square().sum() for k in x).sqrt()
  return dict(l2=float(err),relative_l2=float(err/norm),norm=float(norm),max_abs=max(float((x[k]-y[k]).abs().max()) for k in x))
 chain=difference(adjoints[0],direct);previous=difference(direct,{k:v.cuda() for k,v in ebase['mu'].items()})
 report.update(baseline_exact=True,chain_reconstruction=chain,previous_early_vjp_difference=previous,feature_reads=sorted(engine.reads),state_keys=[list(x) for x in states])
 allowed=set(EARLY_NAMES)|{'profile','d_lm','v_lm','pad_info'};fcheck=early_features(chart.native,{k:v.detach().requires_grad_(True) for k,v in c0.items()})
 report['omitted_differentiable_reads']=[k for k in engine.reads if isinstance(fcheck.get(k),torch.Tensor) and fcheck[k].requires_grad and k not in allowed]
 assert not report['omitted_differentiable_reads'];assert chain['l2']<=1e-10+1e-4*chain['norm'];assert previous['l2']<=1e-10+1e-4*previous['norm']
 torch.save(dict(states=cast_tree(states,torch.float32,'cpu'),adjoints=cast_tree(adjoints,torch.float32,'cpu'),direct=cast_tree(direct,torch.float32,'cpu')),out/'coarse_baseline.pt')
 del fcheck,point,native,final,direct;gc.collect();torch.cuda.empty_cache();save()
 for old in prior['rows']:
  di=old['direction'];h=old['h'];v=directions[di];report['stage']=f'capture_d{di}_h{h}';save()
  with torch.no_grad():
   fp=chart.features((q0+h*v).softmax(-1));sp=engine.trace(early_interface(fp));fm=chart.features((q0-h*v).softmax(-1));sm=engine.trace(early_interface(fm))
   oldfile=lateroot/'control'/old['artifact'];assert sha256(oldfile)==old['artifact_sha256'];past=torch.load(oldfile,map_location='cpu',weights_only=False);bp=engine.final(sp[-1]);bm=engine.final(sm[-1]);exact=all(torch.equal((bp[k].double()-bm[k].double()).cpu(),past['delta'][k]) for k in bp);assert exact,'late secant replay failed'
   projections=[float(tree_dot(g,{k:p[k].double()-m[k].double() for k in p})/(2*h)) for g,p,m in zip(adjoints,sp,sm)];dev=[y-x for x,y in zip(projections[:-1],projections[1:])]
   filename=f'endpoints_d{di}_h{h}.pt';torch.save(dict(plus=cast_tree(sp,torch.float32,'cpu'),minus=cast_tree(sm,torch.float32,'cpu')),out/filename)
   report['coarse_rows'].append(dict(direction=di,h=h,projections=projections,deviations=dev,numerator_deviations=[2*h*x for x in dev],late_delta_exact=exact,artifact=filename,artifact_sha256=sha256(out/filename)))
   del fp,fm,sp,sm,past,bp,bm
  save()
 primary=next(r for r in report['coarse_rows'] if r['direction']==2 and r['h']==.003);selected=max(range(5),key=lambda i:abs(primary['deviations'][i]));report['selection']=dict(index=selected,name='input_initialization' if selected==0 else f'recycle{selected}',primary_direction=2,primary_h=.003,deviation=primary['deviations'][selected])
 # No ESM or diffusion computation below. Reuse full extended endpoints.
 del chart,esm,templates,native_path;gc.collect();torch.cuda.empty_cache()
 native_engine=engine;ref32,over32=reference_copy(engine,torch.float32);ref64,over64=reference_copy(engine,torch.float64);report['precision_overrides']=dict(reference32=over32,reference64=over64)
 u0=states[selected];mu=adjoints[selected+1];gradients={};outputs0={}
 for label,eng,dtype in [('native32',native_engine,torch.float32),('reference32',ref32,torch.float32),('reference64',ref64,torch.float64)]:
  report['stage']='baseline_'+label;save();point=cast_tree(u0,dtype);cot=cast_tree(mu,dtype)
  if label=='native32':g,y=pullback(lambda x:eng.step(selected,x),point,cot)
  else:
   with reference_attention():g,y=pullback(lambda x:eng.step(selected,x),point,cot)
  gradients[label]=g;outputs0[label]=cast_tree(y,dtype,'cpu')
 assert all(torch.equal(outputs0['native32'][k],states[selected+1][k].cpu()) for k in mu)
 report['local_chain']=difference(gradients['native32'],adjoints[selected]);assert report['local_chain']['l2']<=1e-10+1e-4*report['local_chain']['norm']
 report['reference32_baseline_max_abs']=max(float((outputs0['native32'][k]-outputs0['reference32'][k]).abs().max()) for k in mu)
 audit=FloatingDtypeAudit();records=[]
 with torch.no_grad(),reference_attention(records),audit:ref64.step(selected,cast_tree(u0,torch.float64))
 report['dtype_audit']=dict(counts=audit.counts,non_double=audit.non_double,attention_records=records);save();assert not audit.non_double,'hidden low precision in reference'
 torch.save(dict(gradients={k:cast_tree(g,g[next(iter(g))].dtype,'cpu') for k,g in gradients.items()},outputs=outputs0,mu=cast_tree(mu,torch.float32,'cpu'),selected=selected),out/'precision_baseline.pt')
 for row in report['coarse_rows']:
  h=row['h'];di=row['direction'];report['stage']=f'precision_d{di}_h{h}';save();packet=torch.load(out/row['artifact'],map_location='cpu',weights_only=False);up=cast_tree(packet['plus'][selected],torch.float32,'cuda');um=cast_tree(packet['minus'][selected],torch.float32,'cuda');vh={k:(up[k].double()-um[k].double())/(2*h) for k in up}
  values={};ys={};jvps={}
  for label,eng,dtype in [('native32',native_engine,torch.float32),('reference32',ref32,torch.float32),('reference64',ref64,torch.float64)]:
   with torch.no_grad():
    if label=='native32':yp=eng.step(selected,up);ym=eng.step(selected,um)
    else:
     with reference_attention():yp=eng.step(selected,cast_tree(up,dtype));ym=eng.step(selected,cast_tree(um,dtype))
   values[label]=dict(S=float(tree_dot(mu,{k:yp[k].double()-ym[k].double() for k in mu})/(2*h)),A=float(tree_dot(gradients[label],vh)))
   ys[label]=dict(plus=cast_tree(yp,dtype,'cpu'),minus=cast_tree(ym,dtype,'cpu'));del yp,ym
   if label!='native32':
    names=list(u0);point=cast_tree(u0,dtype);vd=cast_tree(vh,dtype)
    def function(*inputs):return tuple(eng.step(selected,dict(zip(names,inputs))).values())
    try:
     with reference_attention():_,tangent=torch.func.jvp(function,tuple(point.values()),tuple(vd.values()))
     j=float(tree_dot(mu,dict(zip(mu,tangent))));rev=float(tree_dot(gradients[label],vd));jvps[label]=dict(supported=True,jvp=j,vjp_same_cast=rev,absolute_error=abs(j-rev),relative_error=abs(j-rev)/max(abs(j),abs(rev),1e-30));del tangent
    except (NotImplementedError,RuntimeError) as error:jvps[label]=dict(supported=False,error=str(error))
  exact=all(torch.equal(ys['native32']['plus'][k],packet['plus'][selected+1][k]) and torch.equal(ys['native32']['minus'][k],packet['minus'][selected+1][k]) for k in mu);assert exact,'native frozen endpoint replay mismatch'
  midpoint={k:(up[k].double()+um[k].double())/2-u0[k].double() for k in u0};radii=[sum((side[k].double()-u0[k].double()).square().sum() for k in u0).sqrt() for side in [up,um]]
  result=precision_decomposition(values['native32']['S'],values['native32']['A'],values['reference64']['S'],values['reference64']['A'],h)|dict(direction=di,h=h,values=values,jvp=jvps,native_endpoint_exact=exact,midpoint_offset_norm=float(sum(x.square().sum() for x in midpoint.values()).sqrt()),endpoint_radius=max(float(x) for x in radii),reference32_max_abs=max(float((ys['native32'][side][k]-ys['reference32'][side][k]).abs().max()) for side in ['plus','minus'] for k in mu))
  filename=f'precision_d{di}_h{h}.pt';torch.save(ys,out/filename);result.update(artifact=filename,artifact_sha256=sha256(out/filename));report['precision_rows'].append(result);save();del packet,up,um,vh,ys
 report.update(complete=True,stage='complete',elapsed_seconds=time.monotonic()-start,peak_memory_gib=torch.cuda.max_memory_allocated()/2**30,baseline_sha256=sha256(out/'coarse_baseline.pt'),precision_baseline_sha256=sha256(out/'precision_baseline.pt'),model_deployment_accepted=False);save()
if __name__=='__main__':main()
