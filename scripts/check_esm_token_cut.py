#!/usr/bin/env python3
"""Only one ESM baseline/gradient; reuse archived soft-ESM output differences."""
import argparse,time
from pathlib import Path
import torch
from fastglycan.models.soft_esm import AMINO_ACIDS,soft_esm2
from fastglycan.interface_decomposition import dot64
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan import stage0_confirm_runtime as rt
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root.resolve();out=root/'token_cut';out.mkdir(exist_ok=False)
previous=rt.load_json(root/'control/report.json');assert previous['complete'];assert sha256(root/'control/baseline.pt')==previous['baseline_sha256']
base=torch.load(root/'control/baseline.pt',map_location='cpu',weights_only=False)
report=dict(complete=False,stage='load',rows=[],script_sha256=sha256(Path(__file__)),input_baseline_sha256=previous['baseline_sha256']);start=time.monotonic()
def save():write_json(out/'report.json',report)
save();torch.serialization.add_safe_globals([argparse.Namespace])
from protenix.data.esm.compute_esm import load_esm_model
esm,alphabet=load_esm_model('esm2-3b',local_esm_dir='/media/PM982/onestepfold/protenix_stage0_pkg/v1_1/runtime/checkpoint');esm.eval().requires_grad_(False)
assert next(esm.parameters()).dtype==torch.float32
q0=base['q'].cuda();mu=base['mu']['esm_token_embedding'].cuda();q=q0.detach().requires_grad_(True)
observed=[]
handle=esm.layers[0].register_forward_pre_hook(lambda module,args:observed.append(args[0]))
try:H=soft_esm2(esm,alphabet,q.softmax(-1))
finally:handle.remove()
assert len(observed)==1
T=observed[0];gT,gq=torch.autograd.grad(dot64(mu,H),(T,q),retain_graph=True)
chain,=torch.autograd.grad(T,q,grad_outputs=gT)
ids=torch.tensor([alphabet.get_idx(aa) for aa in AMINO_ACIDS],device='cuda');weights=esm.embed_tokens.weight

def token_input(q):
 residues=q.softmax(-1)@weights[ids]
 x=esm.embed_scale*torch.cat((weights[alphabet.cls_idx][None],residues,weights[alphabet.eos_idx][None]),dim=0)[None]
 if esm.token_dropout:x=x*(1-.15*.8)
 return x.transpose(0,1)

with torch.no_grad():reconstructed=token_input(q0)
report.update(stage='secants',esm_baseline_exact=torch.equal(H.detach().cpu(),base['early']['esm_token_embedding']),token_input_exact=torch.equal(T,reconstructed),chain_relative_l2_error=float((chain-gq).norm()/gq.norm()),chain_max_abs=float((chain-gq).abs().max()),gradient_norm=float(gq.norm()))
assert report['esm_baseline_exact'] and report['token_input_exact']
assert float((chain-gq).norm())<=1e-10+1e-4*float(gq.norm())
torch.save(dict(T=T.detach().cpu(),nu=gT.detach().cpu(),gq=gq.detach().cpu(),chain=chain.detach().cpu(),mu=mu.cpu(),directions=base['directions'],q=base['q']),out/'baseline.pt')
gq=gq.detach();gT=gT.detach();del q,H,T,chain,observed;save()
for row in previous['rows']:
 h=row['h'];di=row['direction'];v=base['directions'][di].cuda()
 with torch.no_grad():
  deltaT=token_input(q0+h*v).double()-token_input(q0-h*v).double()
  oldfile=root/'control'/row['artifact'];assert sha256(oldfile)==row['artifact_sha256'];deltaH=torch.load(oldfile,map_location='cpu',weights_only=False)['esm_token_embedding'].cuda()
  aE=float(dot64(gq,v));k=float(dot64(gT,deltaT)/(2*h));nE=float(dot64(mu,deltaH)/(2*h))
  name=row['artifact'];torch.save(dict(deltaT=deltaT.cpu()),out/name)
  report['rows'].append(dict(direction=di,h=h,a_E=aE,k=k,n_E=nE,pre_transformer=k-aE,transformer=nE-k,esm_total=nE-aE,early_total=row['before_esm_output'],rc_and_accumulation_residual=row['before_esm_output']-(nE-aE),identity_residual=(nE-aE)-((k-aE)+(nE-k)),artifact=name,artifact_sha256=sha256(out/name)))
 save()
report.update(complete=True,stage='complete',baseline_sha256=sha256(out/'baseline.pt'),elapsed_seconds=time.monotonic()-start);save()
