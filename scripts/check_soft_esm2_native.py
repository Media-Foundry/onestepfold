#!/usr/bin/env python3
import argparse, json, time
from pathlib import Path
import torch
from fastglycan.models.soft_esm import soft_esm2, sequence_probabilities
from fastglycan.paired_teacher_protocol import write_json

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 a.out.mkdir(exist_ok=False)
 torch.serialization.add_safe_globals([argparse.Namespace])
 from protenix.data.esm.compute_esm import load_esm_model
 m,alphabet=load_esm_model('esm2-3b',local_esm_dir='/media/PM982/onestepfold/protenix_stage0_pkg/v1_1/runtime/checkpoint');m.eval().requires_grad_(False)
 info=json.load(open(a.root/'packets.json'));g=min(info,key=lambda g:(info[g]['length'],g));manifest=json.load(open(a.root/'manifest.json'));seq=manifest[g]['sequence'];p0=sequence_probabilities(seq,device='cuda')
 _,_,tokens=alphabet.get_batch_converter()([('probe',seq)])
 with torch.no_grad():
  native=m(tokens.cuda(),repr_layers=[36])['representations'][36][0,1:-1]
  soft=soft_esm2(m,alphabet,p0)
 report=dict(group=g,length=len(seq),hard_embedding_max_abs=float((native-soft).abs().max()),complete=False)
 write_json(a.out/'report.json',report)
 torch.testing.assert_close(native,soft,rtol=1e-5,atol=1e-5)
 q=(p0*4).requires_grad_();value=soft_esm2(m,alphabet,q.softmax(-1)).square().mean();grad,=torch.autograd.grad(value,q)
 report.update(complete=True,logit_gradient_finite=bool(grad.isfinite().all()),logit_gradient_norm=float(grad.norm()),peak_memory_gib=torch.cuda.max_memory_allocated()/2**30)
 write_json(a.out/'report.json',report)
if __name__=='__main__':main()
