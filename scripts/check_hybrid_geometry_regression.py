#!/usr/bin/env python3
import argparse,json
from pathlib import Path
import numpy as np
import torch
from fastglycan.models.soft_sequence_chart import native_sequence_features
from fastglycan.hybrid_geometry import GeometryTopology,hard_accept,GeometryRules
from fastglycan.sequence_gate_metrics import contact_objective
from fastglycan.paired_teacher_protocol import write_json
from dataclasses import asdict

p=argparse.ArgumentParser();p.add_argument('--old-root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
rows=[]
for case in ('8bzn','control'):
 for seed in (103,107):
  values={}
  for label in ('initial','optimized'):
   path=a.old_root/f'gate_v2_{case}_s1'/f'{label}_seed{seed}_s1.npz'
   with np.load(path) as d:
    features,atoms=native_sequence_features(str(d['sequence']))
    assert np.array_equal(atoms.atom_name,d['atom_names'])
    x=torch.tensor(d['coordinates'],dtype=torch.float64)
    topology=GeometryTopology(atoms,features['ref_pos'].numpy())
    terms,geometry=topology.terms(x)
    ca=torch.tensor(np.flatnonzero(atoms.atom_name=='CA'))
    task=float(contact_objective(x,ca)[0]);total=task+float(terms['bond']+2*terms['peptide']+terms['clash']+.2*terms['chirality'])
    values[label]=dict(task=task,geometry=geometry,total=total)
  b=values['initial'];c=values['optimized'];decision=hard_accept(c['task'],b['task'],c['geometry'],b['geometry'])
  rows.append(dict(case=case,seed=seed,**values,decision=decision))
assert not any(r['decision']['accepted'] for r in rows),'known geometry collapse was accepted'
write_json(a.out,dict(complete=True,rules=asdict(GeometryRules()),rows=rows))
