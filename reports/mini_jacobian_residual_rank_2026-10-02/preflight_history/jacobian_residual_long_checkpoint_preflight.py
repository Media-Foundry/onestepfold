import argparse,json,time,traceback
from pathlib import Path
import torch
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.models.soft_sequence_chart import SequenceChart,native_sequence_features
from fastglycan.models.soft_esm import AMINO_ACIDS,sequence_probabilities
from fastglycan.models.differentiable_mini import full_recycle_pairformer
from fastglycan.jacobian_residual_rank import checkpointed_reverse
from fastglycan.composite_derivatives import without_checkpoint_wrappers
from fastglycan.paired_teacher_protocol import write_json
root=Path('/data/user/shuang886/Folding/jacobian_residual_long_checkpoint_preflight_20261002');root.mkdir(exist_ok=True)
r=dict(complete=False,stage='load');start=time.monotonic()
def save():write_json(root/'report.json',r)
save()
try:
 torch.set_num_threads(1);lock=json.load(open(root.parent/'global_response_rank_v1_20261002/lock.json'));pi=7;row=lock['rows'][pi];seq=row['sequence'];index=next(i for i,ids in enumerate(lock['assignments']) if pi in ids);pos=row['positions'][0];aa=next(a for a in AMINO_ACIDS if a!=seq[pos])
 runner=rt.runner_setup(root/'work');runner.configs.dtype='fp32';m=runner.model.eval().requires_grad_(False);torch.serialization.add_safe_globals([argparse.Namespace])
 from protenix.data.esm.compute_esm import load_esm_model
 esm,alphabet=load_esm_model('esm2-3b',local_esm_dir=runner.configs.load_checkpoint_dir);esm.eval().requires_grad_(False)
 templates={a:native_sequence_features(a*len(seq)) for a in AMINO_ACIDS};chart=SequenceChart(seq,m,esm,alphabet,templates)
 p=sequence_probabilities(seq,device='cuda');d=torch.zeros_like(p);d[pos,AMINO_ACIDS.index(seq[pos])]=-1;d[pos,AMINO_ACIDS.index(aa)]=1
 wt=torch.load(Path(lock['states'])/f'worker_{index}/p{pi}_wt_conditioning.pt',map_location='cuda',weights_only=False)['conditioning'][1:]
 def f(p):return full_recycle_pairformer(m,chart.features(p,check_chart=False),N_cycle=4,inplace_safe=False,mc_dropout=False)[1:]
 with without_checkpoint_wrappers(m):
  r['stage']='primal';save()
  with torch.no_grad():base=f(p)
  r['primal_max']=[float((a-b).abs().max()) for a,b in zip(base,wt)];r['primal_exact']=[torch.equal(a,b) for a,b in zip(base,wt)];save();assert all(r['primal_exact']),'chart/native WT mismatch'
  r['stage']='jvp';save();torch.cuda.synchronize();t=time.monotonic()
  with torch.no_grad():primal,tangent=torch.func.jvp(f,(p,),(d,))
  torch.cuda.synchronize();r['jvp_seconds']=time.monotonic()-t;r['jvp_primal_exact']=[torch.equal(a,b) for a,b in zip(base,primal)];r['tangent_norms']=[float(x.double().norm()) for x in tangent];r['finite']=all(bool(torch.isfinite(x).all()) for x in tangent);save();assert all(r['jvp_primal_exact']) and r['finite']
  with checkpointed_reverse(m):
   r['stage']='vjp';save();pp=p.detach().requires_grad_();out=f(pp);assert all(torch.equal(a,b) for a,b in zip(out,base));gen=torch.Generator(device='cuda').manual_seed(228101);r['duality']=[]
   for i in range(2):
    w=[torch.randn(x.shape,device='cuda',generator=gen)/x.numel()**.5 for x in out];loss=sum((x.double()*v.double()).sum() for x,v in zip(out,w));g,=torch.autograd.grad(loss,pp,retain_graph=i==0);a=float((g.double()*d.double()).sum());b=float(sum((x.double()*v.double()).sum() for x,v in zip(tangent,w)));err=abs(a-b);r['duality'].append(dict(vjp=a,jvp=b,relative=err/max(abs(a),abs(b),1e-30),passed=err<=1e-6+.005*max(abs(a),abs(b))));save()
  assert all(x['passed'] for x in r['duality'])
  torch.save(dict(probabilities=p.cpu(),direction=d.cpu(),tangents=[x.cpu() for x in tangent]),root/'tangent.pt')
 r.update(complete=True,stage='complete',seconds=time.monotonic()-start,peak_allocated=torch.cuda.max_memory_allocated());save()
except Exception:
 r.update(stage='failed',error=traceback.format_exc(),seconds=time.monotonic()-start);save();raise
