#!/usr/bin/env python3
"""Local q->softmax(q)->pW only; no ESM Transformer/folding evaluation."""
import argparse,json
from pathlib import Path
import torch
from esm.data import Alphabet
from fastglycan.models.soft_esm import AMINO_ACIDS
from fastglycan.interface_decomposition import analytic_embedding_tangent,dot64
from fastglycan.paired_teacher_protocol import sha256,write_json
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root.resolve()
assert json.loads((root/'audit.json').read_text())['complete']
checkpoint=Path('/media/PM982/onestepfold/protenix_stage0_pkg/v1_1/runtime/checkpoint/esm2_t36_3B_UR50D.pt')
state=torch.load(checkpoint,map_location='cpu',weights_only=False,mmap=True)
key='encoder.sentence_encoder.embed_tokens.weight';alphabet=Alphabet.from_architecture('ESM-1b');ids=[alphabet.get_idx(aa) for aa in AMINO_ACIDS]
checkpoint_dtype=str(state['model'][key].dtype);weights=state['model'][key][ids].float().clone();torch.save(dict(weights=weights,ids=ids,amino_acids=AMINO_ACIDS,checkpoint=str(checkpoint),key=key,checkpoint_dtype=checkpoint_dtype,runtime_dtype='torch.float32'),root/'embedding_weights.pt');del state
report=dict(scope='Only softmax and residue-token embedding GEMM; actual FP32 weights promoted for FP64 reference, not higher-precision pretrained weights; no Transformer',device=torch.cuda.get_device_name(),matmul_precision=torch.get_float32_matmul_precision(),allow_tf32=torch.backends.cuda.matmul.allow_tf32,checkpoint_dtype=checkpoint_dtype,arithmetic_dtypes=['torch.float32','torch.float64'],weights_sha256=sha256(root/'embedding_weights.pt'),source_sha256=sha256(Path(__file__)),cases={})
for case in ['control','8bzn']:
 b=torch.load(root/case/'baseline.pt',map_location='cpu',weights_only=False);q=b['q'].cuda();w32=weights.cuda();w64=w32.double();records=[]
 for di,direction in enumerate(b['directions']):
  v=direction.cuda();q64=q.double();v64=v.double();t64=analytic_embedding_tangent(q64,v64,w64)
  checks={}
  for dtype in [torch.float32,torch.float64]:
   z=q.to(dtype);vd=v.to(dtype);w=w32.to(dtype);analytic=analytic_embedding_tangent(z,vd,w)
   _,tangent=torch.func.jvp(lambda z:z.softmax(-1)@w,(z,),(vd,))
   # Fixed unit projection aligned with the independent FP64 analytic tangent.
   probe=(t64/t64.norm()).to(dtype);leaf=z.detach().requires_grad_(True)
   g,=torch.autograd.grad(dot64(leaf.softmax(-1)@w,probe),leaf)
   checks[str(dtype)]=dict(jvp_vs_formula_relative_l2=float((tangent.double()-analytic.double()).norm()/analytic.double().norm()),jvp_vjp_absolute_difference=abs(float(dot64(tangent,probe)-dot64(g,vd))),jvp_projection=float(dot64(tangent,probe)),formula_vs_fp64_relative_l2=float((analytic.double()-t64).norm()/t64.norm()))
  rows=[]
  for h in [.3,.1,.03,.01,.003]:
   qp=q+h*v;qm=q-h*v
   # Reproduce the actual FP32 input perturbations, plus an ideal FP64 perturbation reference.
   fd32=((qp.softmax(-1)@w32).double()-(qm.softmax(-1)@w32).double())/(2*h)
   fd64=((q64+h*v64).softmax(-1)@w64-(q64-h*v64).softmax(-1)@w64)/(2*h)
   fd64rounded=(qp.double().softmax(-1)@w64-qm.double().softmax(-1)@w64)/(2*h)
   rows.append(dict(h=h,fp32_fd_relative_l2=float((fd32-t64).norm()/t64.norm()),fp64_fd_relative_l2=float((fd64-t64).norm()/t64.norm()),fp64_rounded_q_fd_relative_l2=float((fd64rounded-t64).norm()/t64.norm()),fp32_arithmetic_vs_rounded_fp64_relative_l2=float((fd32-fd64rounded).norm()/t64.norm()),tangent_norm=float(t64.norm())))
  records.append(dict(direction=di,checks=checks,rows=rows))
 report['cases'][case]=records
report['complete']=True;write_json(root/'embedding_reference.json',report)
