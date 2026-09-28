#!/usr/bin/env python3
"""Precompute each ESM probability input once; native graph and chemistry stay fixed."""
import argparse,math,json
from pathlib import Path
import numpy as np
import torch
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.models.soft_esm import AMINO_ACIDS,sequence_probabilities,soft_esm2
from fastglycan.models.soft_sequence_chart import SequenceChart,native_sequence_features,device_tree,REFERENCE_FEATURES
from fastglycan.input_interpolation import probability_interpolation,mix_reference,aligned_rmsd
from fastglycan.paired_teacher_protocol import sha256,write_json


def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--case',required=True);a=p.parse_args();root=a.root.resolve();lock=rt.load_json(root/'lock.json');case=lock['cases'][a.case];seq=case['sequence'];out=root/('prepare_'+a.case);out.mkdir(exist_ok=False)
 runner=rt.runner_setup(out/'work');model=runner.model.eval().requires_grad_(False);torch.serialization.add_safe_globals([argparse.Namespace])
 from protenix.data.esm.compute_esm import load_esm_model
 esm,alphabet=load_esm_model('esm2-3b',local_esm_dir=runner.configs.load_checkpoint_dir);esm.eval().requires_grad_(False)
 templates={aa:native_sequence_features(aa*len(seq)) for aa in AMINO_ACIDS};chart=SequenceChart(seq,model,esm,alphabet,templates);onehot=sequence_probabilities(seq,device='cuda')
 with torch.no_grad():
  hard=chart.features(onehot)
  for name in ('restype','profile',*REFERENCE_FEATURES):
   if not torch.equal(hard[name],chart.native[name]):raise ValueError('non-native hard endpoint '+name)
  _,_,tokens=alphabet.get_batch_converter()([('native',seq)])
  native_esm=esm(tokens.to('cuda'),repr_layers=[esm.num_layers])['representations'][esm.num_layers][0,1:-1]
  esm_error=float((native_esm-hard['esm_token_embedding']).abs().max())
  if esm_error>1e-5:raise ValueError('native ESM endpoint mismatch')
  soft=[]
  for alpha in lock['alphas']:
   probabilities=probability_interpolation(onehot,alpha)
   entry=dict(alpha=alpha,R=probabilities@chart.restype_bank,C=mix_reference(chart.bank,probabilities,chart.token_idx),
     E=hard['esm_token_embedding'] if alpha==0 else soft_esm2(esm,alphabet,probabilities),probabilities=probabilities)
   soft.append(device_tree(entry,'cpu'))
  previous=(4*onehot).softmax(-1)
  legacy=dict(alpha=lock['alphas'][-1],R=previous@chart.restype_bank,C=mix_reference(chart.bank,previous,chart.token_idx),E=soft_esm2(esm,alphabet,previous),probabilities=previous)
  path_error=float((previous-probability_interpolation(onehot,lock['alphas'][-1])).abs().max())
  packet=dict(case=case,atoms=chart.atoms,hard=device_tree(hard,'cpu'),soft=soft,legacy=device_tree(legacy,'cpu'),lock_sha256=sha256(root/'lock.json'))
  path=out/'packet.pt';torch.save(packet,path)
  # Audit contributions without changing or re-aligning any reference coordinates.
  residues=[42,43] if a.case=='8bzn' else [37,194];audit=[]
  for residue in residues:
   selected=np.flatnonzero(chart.atoms.res_id==residue);names=list(chart.atoms.atom_name[selected]);backbone=[names.index(n) for n in ('N','CA','C','O')]
   native_positions=chart.native['ref_pos'][selected].cpu().numpy()
   variants=[]
   for index,aa in enumerate(AMINO_ACIDS):
    source_atoms=templates[aa][1];present_names=set(source_atoms.atom_name[source_atoms.res_id==residue])
    positions=chart.bank['ref_pos'][selected,index].cpu().numpy()
    slots=[]
    for local,atom_index in enumerate(selected):
     slots.append(dict(atom=str(chart.atoms.atom_name[atom_index]),index=int(atom_index),present=str(chart.atoms.atom_name[atom_index]) in present_names,
      ref_pos=positions[local].tolist(),ref_mask=float(chart.bank['ref_mask'][atom_index,index]),ref_charge=float(chart.bank['ref_charge'][atom_index,index]),
      element_mass=float(chart.bank['ref_element'][atom_index,index].sum()),name_mass=float(chart.bank['ref_atom_name_chars'][atom_index,index].sum())))
    variants.append(dict(amino_acid=aa,slots=slots,backbone_unaligned_rmsd=float(np.sqrt(np.mean(np.sum((positions[backbone]-native_positions[backbone])**2,axis=-1)))),
     backbone_aligned_rmsd=aligned_rmsd(positions[backbone],native_positions[backbone])))
   audit.append(dict(residue=residue,native_amino_acid=seq[residue-1],variants=variants))
  write_json(out/'reference_audit.json',dict(case=a.case,rows=audit,missing_slots_use_zero=True,reference_coordinates_not_realigned=True))
  write_json(out/'report.json',dict(complete=True,case=a.case,packet_sha256=sha256(path),reference_audit_sha256=sha256(out/'reference_audit.json'),native_esm_max_abs=esm_error,
    legacy_probability_max_abs=path_error,source_sha256=sha256(Path(__file__)),lock_sha256=sha256(root/'lock.json')))

if __name__=='__main__':main()
