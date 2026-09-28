#!/usr/bin/env python3
"""Recompute the bounded S5 comparator from saved coordinates on CPU."""
import argparse,json
from pathlib import Path
import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.sequence_gate_metrics import contact_objective
from fastglycan.collision_audit import collision_records
from fastglycan.hybrid_geometry import GeometryRules
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);root=p.parse_args().root.resolve()
r=json.loads((root/'report.json').read_text());assert r['complete'];assert sha256(root/'topology.pt')==r['topology_sha256']
top=torch.load(root/'topology.pt',map_location='cpu',weights_only=False);count=0;error=0.;rows=[];rules=GeometryRules()
for arm,values in r['results'].items():
 for seed,v in values.items():
  file=root/v['coordinate_file'];assert sha256(file)==v['coordinate_sha256'];packet=np.load(file)
  for field in ['atom_names','residue_ids','chain_ids']:assert np.array_equal(packet[field],top[field])
  x=torch.from_numpy(packet['coordinates']);task,_=contact_objective(x,top['ca']);terms,g=top['topology'].terms(x)
  delta=max([abs(float(task)-v['task'])]+[abs(g[k]-v['geometry'][k]) for k in g]);assert delta<1e-6;error=max(error,delta)
  pairs=collision_records(x.numpy(),top['topology'],top['atom_names'],top['residue_ids'],top['chain_ids'],top['sequence']);assert pairs==v['pairs']
  bb=sum(p['severe'] and all(p[k]['name'] in {'N','CA','C','O','OXT'} for k in ['a','b']) for p in pairs)
  okay=(g['bond_rmse']<=rules.bond_rmse_max and g['peptide_mae']<=rules.peptide_mae_max and g['chirality_fraction']>=rules.chirality_fraction_min and g['max_penetration']<=rules.max_penetration_max and g['severe_pairs_per_atom']<=rules.severe_pairs_per_atom_max)
  rows.append(dict(arm=arm,seed=seed,geometry=g,absolute_geometry=okay,severe_backbone_pairs=bb));count+=1
assert count==9
write_json(root/'audit.json',dict(complete=True,coordinate_recomputations=count,max_scalar_error=error,report_sha256=sha256(root/'report.json'),rows=rows))
