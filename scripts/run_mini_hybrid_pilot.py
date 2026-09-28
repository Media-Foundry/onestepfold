#!/usr/bin/env python3
"""Locked segmented FD and one-round gradient-vs-random hard mutation pilot."""
import argparse,json,time
from pathlib import Path
from dataclasses import asdict
import numpy as np
import torch
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.paired_teacher_protocol import write_json,sha256
from fastglycan.models.soft_esm import AMINO_ACIDS,sequence_probabilities,soft_esm2
from fastglycan.models.soft_sequence_chart import SequenceChart,native_sequence_features,device_tree
from fastglycan.models.differentiable_mini import fixed_graph_coordinates,full_recycle_pairformer,diffusion_from_conditioning,prepare_atom_pairs
from fastglycan.sequence_gate_metrics import contact_objective,directional_finite_differences
from fastglycan.hybrid_geometry import GeometryTopology,GeometryRules,hard_accept
from fastglycan.hybrid_proposals import mutation_proposals,identity_noise


def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--case',required=True);p.add_argument('--steps',type=int,default=1,choices=(1,2));p.add_argument('--derivatives-only',action='store_true');a=p.parse_args()
 root=a.root.resolve();lock=rt.load_json(root/'lock.json');case=lock['cases'][a.case];seq=case['sequence']
 out=root/f'{a.case}_s{a.steps}';out.mkdir(exist_ok=False)
 if asdict(GeometryRules())!=lock['geometry_rules']:raise ValueError('geometry rule drift')
 source=Path(__file__).resolve().parents[1]
 for name,digest in lock['source_sha256'].items():
  if sha256(source/name)!=digest:raise ValueError('source drift '+name)
 report=dict(complete=False,case=case,steps=a.steps,scope='fixed-chart proposals plus independent hard acceptance',lock_sha256=sha256(root/'lock.json'),stage='load',segments={},candidates=[])
 def save():write_json(out/'report.json',report)
 save();runner=rt.runner_setup(out/'work');runner.configs.dtype='fp32';model=runner.model.eval().requires_grad_(False)
 torch.serialization.add_safe_globals([argparse.Namespace])
 from protenix.data.esm.compute_esm import load_esm_model
 esm,alphabet=load_esm_model('esm2-3b',local_esm_dir=runner.configs.load_checkpoint_dir);esm.eval().requires_grad_(False)
 report['stage']='prepare';save();templates={aa:native_sequence_features(aa*len(seq)) for aa in AMINO_ACIDS}
 chart=SequenceChart(seq,model,esm,alphabet,templates);topology=GeometryTopology(chart.atoms,chart.native['ref_pos'].cpu().numpy())
 q0=sequence_probabilities(seq,device='cuda')*4;p0=q0.softmax(-1);initial=identity_noise(chart.atoms,211,device='cuda')
 def loss_parts(x):
  task=contact_objective(x,chart.ca_indices)[0];terms,_=topology.terms(x)
  total=task+terms['bond']+2*terms['peptide']+terms['clash']+.2*terms['chirality']
  return dict(old=task,new=total)
 with torch.no_grad():
  features=chart.features(p0);conditioning=full_recycle_pairformer(model,features,N_cycle=4,inplace_safe=False,mc_dropout=False)
  x0=diffusion_from_conditioning(model,features,initial,conditioning,steps=a.steps)
  direct=fixed_graph_coordinates(model,features,initial,steps=a.steps,stable_euler=True)
  report['split_forward_max_abs']=float((x0-direct).abs().max())
  if not torch.equal(x0,direct):raise RuntimeError('segmented forward differs from combined path')
  import importlib.util
  reference_path=Path(lock['reference_source'])
  if sha256(reference_path)!=lock['reference_source_sha256']:raise ValueError('reference source changed')
  spec=importlib.util.spec_from_file_location('frozen_reference',reference_path);reference=importlib.util.module_from_spec(spec);spec.loader.exec_module(reference)
  old=reference.fixed_graph_coordinates(model,features,initial,steps=a.steps,stable_euler=True)
  report['frozen_forward_max_abs']=float((old-x0).abs().max())
  if not torch.equal(old,x0):raise RuntimeError('refactor changed frozen forward')
  del old
 # Coordinate→loss FP64 is only this tested segment, not an FP64 folding claim.
 for name in ('old','new'):
  for dtype in (torch.float32,torch.float64):
   key=f'coordinates_{name}_{str(dtype).split(".")[-1]}';report['stage']=key;save()
   _,r=directional_finite_differences(lambda x:loss_parts(x)[name],x0.to(dtype),directions=3)
   report['segments'][key]=r;save()
 shapes=[v.shape for v in conditioning];sizes=[v.numel() for v in conditioning]
 packed=torch.cat([v.flatten() for v in conditioning]).detach()
 def unpack(v):return tuple(t.reshape(shape) for t,shape in zip(v.split(sizes),shapes))
 for name in ('old','new'):
  key='conditioning_'+name;report['stage']=key;save()
  _,r=directional_finite_differences(lambda v:loss_parts(diffusion_from_conditioning(model,features,initial,unpack(v),steps=a.steps))[name],packed,directions=3)
  report['segments'][key]=r;save()
 def sequence_loss(q,name):
  probability=q.softmax(-1)
  # Chart guard rejects any positive/negative perturbation crossing discrete state.
  f=chart.features(probability,check_chart=True)
  value=loss_parts(fixed_graph_coordinates(model,f,initial,steps=a.steps,stable_euler=True))[name]
  if name=='new':value=value+.01*(probability*(probability.log()-p0.log())).sum(-1).mean()
  return value
 for name in ('old','new'):
  key='sequence_'+name;report['stage']=key;save()
  _,r=directional_finite_differences(lambda q:sequence_loss(q,name),q0,directions=3)
  report['segments'][key]=r;save()
 if a.derivatives_only:
  report.update(complete=True,stage='complete');save();return
 report['stage']='proposals';save();start=time.monotonic()
 probability=p0.detach().clone().requires_grad_(True)
 x=fixed_graph_coordinates(model,chart.features(probability),initial,steps=1,stable_euler=True)
 value=loss_parts(x)['new']+.01*(probability*(probability.log()-p0.log())).sum(-1).mean()
 gradient,=torch.autograd.grad(value,probability)
 proposals=mutation_proposals(seq,gradient,budget=lock['candidate_budget'],seed=lock['random_proposal_seed'])
 report['proposal_seconds']=time.monotonic()-start;report['proposals']=proposals;save()
 del x,value,gradient,conditioning,packed,features,direct,x0
 torch.cuda.empty_cache()
 cache={}
 def evaluate(sequence):
  if sequence in cache:return cache[sequence]
  started=time.monotonic();native,atoms=native_sequence_features(sequence);f=device_tree(native,'cuda');f=model.relative_position_encoding.generate_relp(f)
  with torch.no_grad():
   f['esm_token_embedding']=soft_esm2(esm,alphabet,sequence_probabilities(sequence,device='cuda'))
   f=prepare_atom_pairs(f);hard_topology=GeometryTopology(atoms,f['ref_pos'].cpu().numpy());ca=torch.tensor(np.flatnonzero(atoms.atom_name=='CA'),device='cuda');values={}
   for seed in lock['evaluation_seeds']:
    x=fixed_graph_coordinates(model,f,identity_noise(atoms,seed,device='cuda'),steps=1,stable_euler=True)
    task=float(contact_objective(x,ca)[0]);_,geometry=hard_topology.terms(x)
    file=f'candidate{len(cache):03d}_seed{seed}.npz'
    np.savez_compressed(out/file,coordinates=x.cpu().numpy(),sequence=sequence,atom_names=atoms.atom_name,residue_ids=atoms.res_id,chain_ids=atoms.chain_id)
    values[str(seed)]=dict(task=task,geometry=geometry,coordinate_file=file,coordinate_sha256=sha256(out/file))
  result=dict(values=values,seconds=time.monotonic()-started);cache[sequence]=result;return result
 baseline=evaluate(seq);report['baseline']=baseline;report['stage']='hard_candidates';save()
 for arm,options in proposals.items():
  for index,option in enumerate(options):
   candidate=evaluate(option['sequence']);decisions={}
   for seed in lock['evaluation_seeds']:
    b=baseline['values'][str(seed)];c=candidate['values'][str(seed)]
    decisions[str(seed)]=hard_accept(c['task'],b['task'],c['geometry'],b['geometry'])
   report['candidates'].append(dict(arm=arm,index=index,proposal=option,hard=candidate,decisions=decisions));save()
 for arm in proposals:
  accepted=[r for r in report['candidates'] if r['arm']==arm and r['decisions']['211']['accepted']]
  chosen=min(accepted,key=lambda r:r['hard']['values']['211']['task']) if accepted else None
  report.setdefault('arm_summary',{})[arm]=dict(proposals=len(proposals[arm]),accepted_on_selection_noise=len(accepted),
    retained_on_confirmation_noise=sum(r['decisions']['223']['accepted'] for r in accepted),
    selected_index=chosen['index'] if chosen else None,
    selected_confirmed=chosen['decisions']['223']['accepted'] if chosen else False)
 report.update(complete=True,stage='complete',unique_hard_sequences_including_baseline=len(cache),
               peak_memory_gib=torch.cuda.max_memory_allocated()/2**30,model_deployment_accepted=False)
 save()
if __name__=='__main__':main()
