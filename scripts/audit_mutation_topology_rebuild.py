#!/usr/bin/env python3
"""CPU-only chemical featurizer replay; no ESM/folding model loaded."""
import argparse,json
from pathlib import Path
import numpy as np
import torch
from fastglycan.models.soft_sequence_chart import native_sequence_features
from fastglycan.hybrid_geometry import GeometryTopology
from fastglycan.paired_teacher_protocol import sha256,write_json
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);root=p.parse_args().root.resolve();report=json.loads((root/'report.json').read_text());rows={0:report['parent']}
for c in report['candidates']:rows[c['hard']['index']]=c['hard']
r=dict(complete=False,source_sha256=sha256(Path(__file__)),scope='same native CCD featurizer replay on CPU; no model or coordinate prediction',rows=[])
for index,row in sorted(rows.items()):
 f=root/f'worker{index%4}'/row['topology_file'];assert sha256(f)==row['topology_sha256'];old=torch.load(f,map_location='cpu',weights_only=False);features,atoms=native_sequence_features(row['sequence']);new=GeometryTopology(atoms,features['ref_pos'].numpy());saved=old['topology']
 for label,a in [('atom_names',atoms.atom_name),('residue_ids',atoms.res_id),('chain_ids',atoms.chain_id)]:assert np.array_equal(old[label],a)
 fields={k:torch.equal(getattr(saved,k),getattr(new,k)) for k in ['bonds','peptide','ideal','radii','centres','volumes']};assert all(fields.values()),(index,fields)
 r['rows'].append(dict(index=index,atom_count=len(atoms),fields_exact=fields));write_json(root/'reanalysis/topology_rebuild.json',r)
r['complete']=True;write_json(root/'reanalysis/topology_rebuild.json',r)
