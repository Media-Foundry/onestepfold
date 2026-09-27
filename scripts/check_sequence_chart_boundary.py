#!/usr/bin/env python3
"""Probe the actual first argmax boundary along a saved optimization displacement."""
import argparse,json
from pathlib import Path
import torch
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.models.soft_sequence_chart import SequenceChart,native_sequence_features,first_argmax_boundary
from fastglycan.models.soft_esm import AMINO_ACIDS,hard_sequence
from fastglycan.models.differentiable_mini import fixed_graph_coordinates
from fastglycan.paired_teacher_protocol import write_json




def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();run=a.run.resolve();out=a.out.resolve();out.mkdir(exist_ok=False)
 values=torch.load(run/'logits.pt',map_location='cpu',weights_only=True);q0=values['initial_logits'];q1=values['final_logits'];t=first_argmax_boundary(q0,q1)
 result=dict(complete=False,crossing_t=t,rows=[],scope='actual argmax boundary of saved logit displacement; C4S1 fixed noise')
 write_json(out/'report.json',result)
 runner=rt.runner_setup(out/'work');runner.configs.dtype='fp32';model=runner.model.eval().requires_grad_(False)
 torch.serialization.add_safe_globals([argparse.Namespace])
 from protenix.data.esm.compute_esm import load_esm_model
 esm,alphabet=load_esm_model('esm2-3b',local_esm_dir=runner.configs.load_checkpoint_dir);esm.eval().requires_grad_(False)
 templates={aa:native_sequence_features(aa*len(q0)) for aa in AMINO_ACIDS};charts={}
 with torch.no_grad():
  for h in (1e-3,1e-4,1e-5):
   ca=[];seqs=[];probs=[];counts=[]
   for side in (-1,1):
    q=(q0.double()+(t+side*h)*(q1.double()-q0.double())).float().cuda();probability=q.softmax(-1);seq=hard_sequence(probability)
    if seq not in charts:charts[seq]=SequenceChart(seq,model,esm,alphabet,templates)
    c=charts[seq];x=fixed_graph_coordinates(model,c.features(probability),c.initial_noise(103),stable_euler=True)
    ca.append(x[0,c.ca_indices].double());seqs.append(seq);probs.append(probability);counts.append(len(c.atoms))
   left,right=[x-x.mean(0) for x in ca];u,_,vh=torch.linalg.svd(left.T@right);diag=torch.eye(3,device='cuda',dtype=torch.float64);diag[-1,-1]=torch.linalg.det(u@vh)
   rmsd=float(((left@(u@diag@vh)-right).square().sum(-1).mean()).sqrt())
   result['rows'].append(dict(h=h,probability_max_difference=float((probs[0]-probs[1]).abs().max()),different_hard_sequences=seqs[0]!=seqs[1],atom_counts=counts,aligned_ca_rmsd=rmsd))
   write_json(out/'report.json',result)
 result['complete']=True;write_json(out/'report.json',result)
if __name__=='__main__':main()
