#!/usr/bin/env python3
"""Only archived recycle1 endpoints; no selection, ESM, or trajectory capture."""
import argparse,gc,time
from pathlib import Path
import torch
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.models.soft_sequence_chart import native_sequence_features,device_tree
from fastglycan.pairformer_precision import PairformerStages,cast_tree,pullback,tree_dot,reference_copy,reference_attention
from fastglycan.esm_precision_reference import FloatingDtypeAudit,precision_decomposition
from fastglycan.paired_teacher_protocol import sha256,write_json


def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root.resolve();out=root/'run';out.mkdir(exist_ok=False)
 lock=rt.load_json(root/'lock.json');prior=Path(lock['prior_root']);old=rt.load_json(prior/'run/report.json');start=time.monotonic()
 for f,h in lock['source_sha256'].items():assert sha256(Path(__file__).resolve().parents[1]/f)==h,f
 for f,h in lock['input_sha256'].items():assert sha256(prior/f)==h,f
 assert old['complete'];packet=torch.load(prior/'run/coarse_baseline.pt',map_location='cpu',weights_only=False)
 (out/'coarse_baseline.pt').symlink_to(prior/'run/coarse_baseline.pt')
 for row in old['coarse_rows']:
  assert sha256(prior/'run'/row['artifact'])==row['artifact_sha256']
  (out/row['artifact']).symlink_to(prior/'run'/row['artifact'])
 report=dict(complete=False,stage='load',coarse_rows=old['coarse_rows'],precision_rows=[],selection=dict(index=1,name='recycle1',rule='explicit_locked_reuse_not_reselection'),lock_sha256=sha256(root/'lock.json'),archived_coarse_report_sha256=sha256(prior/'run/report.json'),omitted_differentiable_reads=old['omitted_differentiable_reads'],chain_reconstruction=old['chain_reconstruction'])
 def save():write_json(out/'report.json',report)
 save();runner=rt.runner_setup(out/'work');model=runner.model.eval().requires_grad_(False)
 seq=rt.load_json(Path(lock['near_root'])/'lock.json')['cases']['control']['sequence'];native,_=native_sequence_features(seq);fixed=model.relative_position_encoding.generate_relp(device_tree(native,'cuda'))
 engine=PairformerStages(model,fixed).eval();states=cast_tree(packet['states'],torch.float32,'cuda');adjoints=cast_tree(packet['adjoints'],torch.float32,'cuda');selected=1
 report['runtime']=old['runtime'];report['runtime']['torch']=torch.__version__
 def difference(x,y):
  err=sum((x[k].double()-y[k].double()).square().sum() for k in x).sqrt();norm=sum(y[k].double().square().sum() for k in x).sqrt()
  return dict(l2=float(err),relative_l2=float(err/norm),norm=float(norm),max_abs=max(float((x[k]-y[k]).abs().max()) for k in x))
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
