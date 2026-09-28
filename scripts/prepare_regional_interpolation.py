#!/usr/bin/env python3
"""Local42/43 vs complement: fixed source rules, only change softening locations."""
import argparse,json,os,hashlib
from pathlib import Path
import torch
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.models.soft_esm import soft_esm2,sequence_probabilities
from fastglycan.models.soft_sequence_chart import device_tree
from fastglycan.paired_teacher_protocol import sha256,write_json

p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root.resolve();lock=rt.load_json(root/'lock.json');prep=root/'prepare_8bzn';accept=rt.load_json(prep/'report.json');path=prep/'packet.pt';assert sha256(path)==accept['packet_sha256'];packet=torch.load(path,map_location='cpu',weights_only=False)
runner=rt.runner_setup(root/'regional_esm_work');torch.serialization.add_safe_globals([argparse.Namespace])
from protenix.data.esm.compute_esm import load_esm_model
esm,alphabet=load_esm_model('esm2-3b',local_esm_dir=runner.configs.load_checkpoint_dir);esm.eval().requires_grad_(False)
seq=packet['case']['sequence'];onehot=sequence_probabilities(seq);indices=packet['hard']['atom_to_token_idx'].long();base=packet['hard']
for region in ['local42_43','complement']:
 out=root/'regional'/region;out.mkdir(parents=True,exist_ok=False);(out/'code').symlink_to(root/'code',target_is_directory=True);dest=out/'prepare_8bzn';dest.mkdir()
 mask=torch.zeros(len(seq),dtype=torch.bool);mask[41:43]=True
 if region=='complement':mask=~mask
 atom_mask=mask[indices];soft=[]
 with torch.no_grad():
  for index in [0,6,7]:
   entry=packet['soft'][index];prob=torch.where(mask[:,None],entry['probabilities'],onehot)
   chem={name:torch.where(atom_mask.reshape(-1,*([1]*(value.ndim-1))),value,base[name]) for name,value in entry['C'].items()}
   soft.append(dict(alpha=entry['alpha'],probabilities=prob,R=torch.where(mask[:,None],entry['R'],base['restype']),C=chem,
     E=base['esm_token_embedding'] if index==0 else soft_esm2(esm,alphabet,prob.to('cuda')).cpu()))
 region_lock=dict(cases={'8bzn':lock['cases']['8bzn']},alphas=[entry['alpha'] for entry in soft],sources=lock['sources'],region=region,soft_residue_indices_1based=(torch.where(mask)[0]+1).tolist(),
   noise_seed=211,source_sha256=dict(lock['source_sha256']),parent_lock_sha256=sha256(root/'lock.json'),scope='predeclared location diagnosis only; no changed feature formula')
 region_lock['source_sha256']['scripts/run_regional_input_interpolation.py']=sha256(root/'code/scripts/run_regional_input_interpolation.py')
 write_json(out/'lock.json',region_lock)
 output=dict(case=packet['case'],atoms=packet['atoms'],hard=base,soft=soft,lock_sha256=sha256(out/'lock.json'))
 torch.save(output,dest/'packet.pt');write_json(dest/'report.json',dict(complete=True,packet_sha256=sha256(dest/'packet.pt'),lock_sha256=sha256(out/'lock.json'),parent_packet_sha256=accept['packet_sha256']))
write_json(root/'regional_preparation.json',dict(complete=True,regions=['local42_43','complement'],alphas=[0.,.2,lock['alphas'][-1]],source_sha256=sha256(Path(__file__))))
