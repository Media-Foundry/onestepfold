#!/usr/bin/env python3
"""Forward-only E/R/C interventions; regenerate chemistry-dependent caches."""
import argparse
from pathlib import Path
import numpy as np
import torch
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.models.soft_sequence_chart import device_tree,REFERENCE_FEATURES
from fastglycan.models.differentiable_mini import prepare_atom_pairs,full_recycle_pairformer,diffusion_from_conditioning
from fastglycan.hybrid_proposals import identity_noise
from fastglycan.hybrid_geometry import GeometryTopology
from fastglycan.input_interpolation import source_intervention,tensor_delta,aligned_rmsd,audit_reference_caches
from fastglycan.paired_teacher_protocol import sha256,write_json


def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--case',required=True);p.add_argument('--sources',choices=['E','R','C','ERC','ER','EC','RC'],required=True);a=p.parse_args();root=a.root.resolve();lock=rt.load_json(root/'lock.json');out=root/(a.case+'_'+a.sources);out.mkdir(exist_ok=False)
 source=Path(__file__).resolve().parents[1]
 for name,h in lock['source_sha256'].items():
  if sha256(source/name)!=h:raise ValueError('source drift '+name)
 prep=root/('prepare_'+a.case);accept=rt.load_json(prep/'report.json');path=prep/'packet.pt'
 if not accept['complete'] or sha256(path)!=accept['packet_sha256']:raise ValueError('invalid feature packet')
 packet=torch.load(path,weights_only=False,map_location='cpu')
 if packet['lock_sha256']!=lock.get('preparation_lock_sha256',sha256(root/'lock.json')):raise ValueError('packet protocol mismatch')
 atoms=packet['atoms'];hard=device_tree(packet['hard'],'cuda');topology=GeometryTopology(atoms,packet['hard']['ref_pos'].numpy())
 runner=rt.runner_setup(out/'work');model=runner.model.eval().requires_grad_(False)
 if next(model.parameters()).dtype!=torch.float32 or torch.is_autocast_enabled():raise RuntimeError('not FP32 forward')
 initial=identity_noise(atoms,211,device='cuda');ca=np.flatnonzero(atoms.atom_name=='CA')
 tracked=[(42,'CE1'),(43,'OG1')] if a.case=='8bzn' else [(37,'C'),(194,'CB')]
 indices=[int(np.flatnonzero((atoms.res_id==r)&(atoms.atom_name==n))[0]) for r,n in tracked]
 report=dict(complete=False,case=a.case,sources=a.sources,model_precision='fp32',cycles=4,steps=1,noise_seed=211,
   graph_fixed=True,region=lock['region'],lock_sha256=sha256(root/'lock.json'),packet_sha256=sha256(path),tracked_atoms=tracked,rows=[])
 def forward(f):
  f=prepare_atom_pairs(f)
  with audit_reference_caches(model,f) as records:
   point=full_recycle_pairformer(model,f,N_cycle=4,inplace_safe=False,mc_dropout=False)
   shapes=[v.shape for v in point];sizes=[v.numel() for v in point];packed=torch.cat([v.flatten() for v in point]);point=tuple(v.reshape(s) for v,s in zip(packed.split(sizes),shapes))
   x=diffusion_from_conditioning(model,f,initial,point,steps=1)
  return f,point,x,records
 with torch.no_grad():
  baseline_features,baseline_point,baseline,baseline_records=forward(dict(hard))
  basecpu=baseline[0].cpu().numpy();report['baseline_cache_checks']=baseline_records
  all_entries=list(packet['soft'])
  for index,entry in enumerate(all_entries):
   legacy=index==len(packet['soft']);entry=device_tree(entry,'cuda')
   f=source_intervention(hard,entry['C'],entry['R'],hard['esm_token_embedding'],entry['E'],a.sources)
   f,point,x,records=forward(f)
   if index==0 and not torch.equal(x,baseline):raise RuntimeError('alpha0 does not replay hard endpoint')
   for key in ('atom_to_token_idx','ref_space_uid','token_bonds','bond_mask','asym_id'):
    if not torch.equal(f[key],hard[key]):raise RuntimeError('graph changed '+key)
   geometry=topology.terms(x)[1];coords=x[0].cpu().numpy()
   minimum=float('inf')
   for pairs in topology.pairs.to('cuda').split(65536):minimum=min(minimum,float((x[0,pairs[:,0]]-x[0,pairs[:,1]]).norm(dim=-1).min()))
   coordinate_path=out/('legacy.npz' if legacy else f'alpha_{index:02d}.npz')
   np.savez_compressed(coordinate_path,coordinates=coords,atom_names=atoms.atom_name,residue_ids=atoms.res_id,chain_ids=atoms.chain_id)
   refpairs=topology.bonds.numpy();same=atoms.res_id[refpairs[:,0]]==atoms.res_id[refpairs[:,1]];rp=torch.as_tensor(refpairs[same],device='cuda')
   distances=(f['ref_pos'][rp[:,0]]-f['ref_pos'][rp[:,1]]).norm(dim=-1)
   bd=(hard['ref_pos'][rp[:,0]]-hard['ref_pos'][rp[:,1]]).norm(dim=-1)
   row=dict(alpha=entry['alpha'],legacy_softmax=legacy,geometry=geometry,min_nonbond_distance=minimum,
     tracked_distance=float(np.linalg.norm(coords[indices[0]]-coords[indices[1]])),
     aa_aligned_rmsd=aligned_rmsd(coords,basecpu),ca_aligned_rmsd=aligned_rmsd(coords[ca],basecpu[ca]),
     coordinate_max_abs_from_hard=float(np.abs(coords-basecpu).max()),
     fields={key:tensor_delta(f[key],baseline_features[key]) for key in ['esm_token_embedding','restype','profile',*REFERENCE_FEATURES,'d_lm']},
     conditioning={name:tensor_delta(v,b) for name,v,b in zip(['s_inputs','s','z'],point,baseline_point)},
     ref_intra_bond_ratio_quantiles=torch.quantile(distances/bd,torch.tensor([0.,.05,.5,.95,1.],device='cuda')).cpu().tolist(),
     ref_mask_range=[float(f['ref_mask'].min()),float(f['ref_mask'].max())],cache_checks=records,
     coordinate_file=coordinate_path.name,coordinate_sha256=sha256(coordinate_path))
   report['rows'].append(row);write_json(out/'report.json',report)
  report['complete']=True;write_json(out/'report.json',report)

if __name__=='__main__':main()
