#!/usr/bin/env python3
"""Parent-only original and controlled S5 comparison; no search or training."""
import argparse,copy,inspect,time
from pathlib import Path
import numpy as np
import torch
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.models.soft_sequence_chart import native_sequence_features,device_tree
from fastglycan.models.differentiable_mini import full_recycle_pairformer,diffusion_from_conditioning,prepare_atom_pairs
from fastglycan.hybrid_geometry import GeometryTopology
from fastglycan.hybrid_proposals import identity_noise
from fastglycan.collision_audit import collision_records
from fastglycan.sequence_gate_metrics import contact_objective

def packed(point):
 shapes=[x.shape for x in point];sizes=[x.numel() for x in point]
 return tuple(x.reshape(s) for x,s in zip(torch.cat([x.flatten() for x in point]).split(sizes),shapes))

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--input',type=Path,required=True);a=p.parse_args();root=a.root.resolve();source=a.input.resolve()
 old=rt.load_json(source/'report.json');assert sha256(source/'report.json')==rt.load_json(source/'audit.json')['report_sha256'];parent=old['parent'];seeds=[211,200003,200009];start=time.monotonic()
 report=dict(complete=False,stage='loading',results={},scope='one already-seen parent; no prevalence or deployment claim',original_report_sha256=sha256(source/'report.json'))
 def save():write_json(root/'report.json',report)
 save();runner=rt.runner_setup(root/'work');runner.configs.dtype='fp32';model=runner.model.eval().requires_grad_(False)
 torch.serialization.add_safe_globals([argparse.Namespace])
 from protenix.data.esm.compute_esm import load_esm_model
 from protenix.model import generator,protenix
 esm,alphabet=load_esm_model('esm2-3b',local_esm_dir=runner.configs.load_checkpoint_dir);esm.eval().requires_grad_(False)
 checkpoint=Path(runner.configs.load_checkpoint_dir)/(rt.MODEL+'.pt')
 report.update(model=rt.MODEL,checkpoint_sha256=sha256(checkpoint),resolved_config=runner.configs.to_dict(),
   sources={str(Path(inspect.getfile(m))):sha256(Path(inspect.getfile(m))) for m in [generator,protenix]},
   source_sha256=sha256(Path(__file__)),protocol_sha256=sha256(root/'code/docs/mini_c4s5_collision_control_v1.md'))
 save()
 native,atoms=native_sequence_features(parent['sequence']);base=device_tree(native,'cuda')
 with torch.no_grad():
  tokens=alphabet.get_batch_converter()([('parent',parent['sequence'])])[2].cuda()
  base['esm_token_embedding']=esm(tokens,repr_layers=[esm.num_layers],return_contacts=False)['representations'][esm.num_layers][0,1:-1]
  features=prepare_atom_pairs(model.relative_position_encoding.generate_relp(copy.deepcopy(base)))
  top=GeometryTopology(atoms,features['ref_pos'].cpu().numpy());ca=torch.tensor(np.flatnonzero(atoms.atom_name=='CA'))
  oldtop=torch.load(source/'worker0'/parent['topology_file'],map_location='cpu',weights_only=False)
  for key,array in [('atom_names',atoms.atom_name),('residue_ids',atoms.res_id),('chain_ids',atoms.chain_id)]:assert np.array_equal(oldtop[key],array)
  for name in ['bonds','ideal','pairs','centres','volumes']:assert torch.equal(getattr(top,name),getattr(oldtop['topology'],name))
  torch.save(oldtop,root/'topology.pt');report['topology_sha256']=sha256(root/'topology.pt')
  report['stage']='controlled';save()
  conditioning=packed(full_recycle_pairformer(model,features,N_cycle=4,inplace_safe=False,mc_dropout=False))
  def record(arm,seed,x,trace):
   x=x.detach().cpu();task,_=contact_objective(x,ca);terms,g=top.terms(x)
   file=root/f'{arm}_{seed}.npz';np.savez_compressed(file,coordinates=x.numpy(),atom_names=atoms.atom_name,residue_ids=atoms.res_id,chain_ids=atoms.chain_id,sequence=parent['sequence'])
   pairs=collision_records(x.numpy(),top,atoms.atom_name,atoms.res_id,atoms.chain_id,parent['sequence'])
   report['results'].setdefault(arm,{})[str(seed)]=dict(task=float(task),geometry=g,terms={k:float(v) for k,v in terms.items()},pairs=pairs,trace=trace,coordinate_file=file.name,coordinate_sha256=sha256(file));save()
  for seed in seeds:
   noise=identity_noise(atoms,seed,device='cuda')
   for steps in [1,5]:
    x=diffusion_from_conditioning(model,features,noise,conditioning,steps=steps)
    if steps==1:
     f=source/'worker0'/parent['values'][str(seed)]['coordinate_file'];assert sha256(f)==parent['values'][str(seed)]['coordinate_sha256']
     assert torch.equal(x.cpu(),torch.from_numpy(np.load(f)['coordinates'])),'controlled S1 archive drift'
    record(f'controlled_s{steps}',seed,x,dict(cycles=4,steps=steps,initial_noise='identity-key',rotation='identity',mc_dropout=False,gamma0=0,noise_scale_lambda=1,step_scale_eta=1,schedule=model.inference_noise_scheduler(N_step=steps,device='cpu',dtype=torch.float32).tolist()))
  report['stage']='native_s5';save()
  with rt.Trace(model) as trace:
   for seed in seeds:
    prediction,coords,recorded=rt.predict(runner,{'input_feature_dict':base},'c4_s5',seed,trace)
    record('native_s5',seed,prediction['coordinate'],recorded)
 report.update(complete=True,stage='complete',seconds=time.monotonic()-start);save()
if __name__=='__main__':main()
