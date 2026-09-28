#!/usr/bin/env python3
"""Re-score saved native hard S1/S2 starts; no inference or optimized sequences."""
import argparse,json
from pathlib import Path
import numpy as np
import torch
from fastglycan.models.soft_sequence_chart import native_sequence_features
from fastglycan.hybrid_geometry import GeometryTopology
from fastglycan.geometry_audit import independent_allowed_pairs,pair_attribution
from fastglycan.paired_teacher_protocol import sha256,write_json


def main():
 p=argparse.ArgumentParser();p.add_argument('--old-root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();rows=[]
 for case,folder in [('initial100','gate_v1_s1'),('8bzn','gate_v2_8bzn_s1'),('control','gate_v2_control_s1'),('9qr4','gate_v2_9qr4_s1')]:
  for seed in (103,107):
   for steps in (1,2):
    path=a.old_root/folder/f'initial_seed{seed}_s{steps}.npz'
    with np.load(path) as d:
     f,atoms=native_sequence_features(str(d['sequence']));t=GeometryTopology(atoms,f['ref_pos'].numpy())
     assert np.array_equal(atoms.atom_name,d['atom_names'])
     x=d['coordinates'];pairs=independent_allowed_pairs(atoms);assert np.array_equal(pairs,t.pairs.numpy())
    rows.append(dict(case=case,seed=seed,steps=steps,artifact=str(path),sha256=sha256(path),
      geometry=t.terms(torch.tensor(x,dtype=torch.float64))[1],
      attribution=pair_attribution(atoms,x,pairs)))
 write_json(a.out,dict(complete=True,scope='archived native initial hard predictions, not new matched seeds211/223',rows=rows))

if __name__=='__main__':main()
