#!/usr/bin/env python3
"""One archived failure point; early ESM-output cut with every chemistry path."""
import argparse,gc,time
from pathlib import Path
import torch
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.models.soft_esm import AMINO_ACIDS
from fastglycan.models.soft_sequence_chart import SequenceChart,native_sequence_features
from fastglycan.models.differentiable_mini import full_recycle_pairformer
from fastglycan.interface_decomposition import make_interface,dot64
from fastglycan.esm_interface_diagnostics import EARLY_NAMES,early_interface,early_features,nested_decomposition
from fastglycan.paired_teacher_protocol import sha256,write_json


def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root.resolve();out=root/'control';out.mkdir(exist_ok=False)
 lock=rt.load_json(root/'lock.json');prior=Path(lock['prior_root']);old=rt.load_json(prior/'control/report.json');oldlock=rt.load_json(Path(lock['near_hard_root'])/'lock.json')
 source=Path(__file__).resolve().parents[1]
 for f,h in lock['source_sha256'].items():assert sha256(source/f)==h,f
 assert sha256(prior/'control/baseline.pt')==old['baseline_sha256']
 for f,h in lock['input_sha256'].items():assert sha256(prior/f)==h,f
 base=torch.load(prior/'control/baseline.pt',map_location='cpu',weights_only=False)
 report=dict(complete=False,stage='load',rows=[],lock_sha256=sha256(root/'lock.json'));start=time.monotonic()
 def save():write_json(out/'report.json',report)
 save();runner=rt.runner_setup(out/'work');model=runner.model.eval().requires_grad_(False)
 torch.serialization.add_safe_globals([argparse.Namespace])
 from protenix.data.esm.compute_esm import load_esm_model
 esm,alphabet=load_esm_model('esm2-3b',local_esm_dir=runner.configs.load_checkpoint_dir);esm.eval().requires_grad_(False)
 assert next(model.parameters()).dtype==torch.float32 and next(esm.parameters()).dtype==torch.float32 and not torch.is_autocast_enabled()
 seq=oldlock['cases']['control']['sequence'];templates={aa:native_sequence_features(aa*len(seq)) for aa in AMINO_ACIDS};chart=SequenceChart(seq,model,esm,alphabet,templates)
 fixed=chart.native;q0=base['q'].cuda();lam={k:v.cuda() for k,v in base['lambda_'].items()};directions=[v.cuda() for v in base['directions']];reads=set()
 class ReadDict(dict):
  def __getitem__(self,k):reads.add(k);return super().__getitem__(k)
 def late(f):
  f=ReadDict(f);point=full_recycle_pairformer(model,f,N_cycle=4,inplace_safe=False,mc_dropout=False)
  shapes=[v.shape for v in point];sizes=[v.numel() for v in point];flat=torch.cat([v.flatten() for v in point]);point=tuple(v.reshape(s) for v,s in zip(flat.split(sizes),shapes))
  return make_interface(point,f)
 def middle(c):return late(early_features(fixed,c))
 report['stage']='cut_and_chain';save()
 q=q0.detach().requires_grad_(True);f=chart.features(q.softmax(-1),check_chart=True);c=early_interface(f);b=late(f)
 direct,=torch.autograd.grad(tuple(b.values()),q,grad_outputs=tuple(lam[k] for k in b),retain_graph=True)
 leaves={k:v.detach().requires_grad_(True) for k,v in c.items()};cut=middle(leaves)
 pulled=torch.autograd.grad(tuple(cut.values()),tuple(leaves.values()),grad_outputs=tuple(lam[k] for k in cut),allow_unused=True)
 mu={k:(torch.zeros_like(leaves[k]) if v is None else v).detach() for k,v in zip(EARLY_NAMES,pulled)}
 chain,=torch.autograd.grad(tuple(c.values()),q,grad_outputs=tuple(mu.values()))
 error=chain-direct;archive_error=direct.detach().cpu()-base['direct']
 allowed=set(EARLY_NAMES)|{'profile','d_lm','v_lm','pad_info'}
 omitted=[k for k in reads if isinstance(f.get(k),torch.Tensor) and f[k].requires_grad and k not in allowed]
 report.update(cut_forward_exact=all(torch.equal(cut[k],b[k]) for k in b),archived_interface_exact=all(torch.equal(b[k].detach().cpu(),base['interface'][k]) for k in b),
  chain_relative_l2_error=float(error.norm()/direct.norm()),chain_l2_error=float(error.norm()),direct_gradient_norm=float(direct.norm()),chain_max_abs=float(error.abs().max()),
  previous_direct_gradient_max_abs=float(archive_error.abs().max()),previous_direct_relative_l2=float(archive_error.norm()/base['direct'].norm()),feature_reads=sorted(reads),omitted_differentiable_reads=omitted,
  early_fields=list(c),unused_early_fields=[k for k,v in zip(EARLY_NAMES,pulled) if v is None])
 torch.save(dict(early={k:v.detach().cpu() for k,v in c.items()},mu={k:v.cpu() for k,v in mu.items()},direct=direct.detach().cpu(),chain=chain.detach().cpu(),directions=base['directions'],q=base['q']),out/'baseline.pt');save()
 assert report['cut_forward_exact'] and report['archived_interface_exact'],'forward replay failed'
 assert not omitted,omitted
 assert report['chain_l2_error']<=1e-10+1e-4*report['direct_gradient_norm'],'chain reconstruction failed'
 direct=direct.detach();del q,f,c,b,leaves,cut,chain,error,pulled;gc.collect();torch.cuda.empty_cache()
 for oldrow in old['rows']:
  di=oldrow['direction'];h=oldrow['h'];v=directions[di];report['stage']=f'direction{di}_h{h}';save()
  with torch.no_grad():
   fp=chart.features((q0+h*v).softmax(-1),check_chart=True);cp=early_interface(fp);bp=late(fp)
   fm=chart.features((q0-h*v).softmax(-1),check_chart=True);cm=early_interface(fm);bm=late(fm)
   oldfile=prior/'control'/oldrow['artifact'];assert sha256(oldfile)==oldrow['artifact_sha256'];previous=torch.load(oldfile,map_location='cpu',weights_only=False)
   exact=all(torch.equal((bp[k].double()-bm[k].double()).cpu(),previous['delta'][k]) for k in bp)
   delta={k:cp[k].double()-cm[k].double() for k in cp};components={k:float(dot64(mu[k],dv)/(2*h)) for k,dv in delta.items()}
   analytic=float(dot64(direct,v));n=sum(components.values());m=sum(float(dot64(lam[k],bp[k].double()-bm[k].double())/(2*h)) for k in bp)
   row=nested_decomposition(analytic,n,m,oldrow['d'])|dict(direction=di,h=h,components=components,early_delta_norms={k:float(dv.norm()) for k,dv in delta.items()},late_delta_exact=exact,prior_a=oldrow['a'],prior_m=oldrow['m'])
   filename=f'direction{di}_h{h}.pt';torch.save({k:dv.cpu() for k,dv in delta.items()},out/filename);row.update(artifact=filename,artifact_sha256=sha256(out/filename));report['rows'].append(row);save()
   assert exact,'late secant no longer matches archived function'
   del fp,fm,cp,cm,bp,bm,delta,previous
 report.update(complete=True,stage='complete',baseline_sha256=sha256(out/'baseline.pt'),elapsed_seconds=time.monotonic()-start,model_deployment_accepted=False);save()
if __name__=='__main__':main()
