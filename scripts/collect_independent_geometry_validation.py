#!/usr/bin/env python3
"""Experimental GT scoring after inference/repair, with fixed96-instance denominator."""
import argparse,json,traceback
from pathlib import Path
import numpy as np
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.independent_geometry_eval import experimental_quality,continuation_screen

p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();r=a.root;panel=json.loads((r/'panel32.json').read_text());rows=[]
for protein in panel:
 g=protein['group_id'];folder=r/'proteins'/g;packet=Path(protein['chemistry']['packet_dir'])/'mapping.npz';assert sha256(packet)==protein['chemistry']['files']['mapping.npz']
 with np.load(packet) as f:mapping=dict(f)
 reports={}
 for objective in ['mean','tail']:
  f=folder/objective/'report.json';reports[objective]=json.loads(f.read_text()) if f.exists() else dict(cases=[])
 for seed in [300007,300017,300023]:
  row=dict(group_id=g,pdb_id=protein['pdb_id'],stratum=protein['stratum'],length=len(protein['sequence']),seed=seed,source_context='homooligomer_chain' if 'source_context' in protein else 'monomer',quality={},errors={})
  rawfile=folder/'raw'/f'{seed}.npz'
  try:
   raw=np.load(rawfile)['coordinates'];row['quality']['raw']=experimental_quality(raw,mapping,protein['sequence'])
  except Exception:row['errors']['raw']=traceback.format_exc();raw=None
  for objective in ['mean','tail']:
   result=next((x for x in reports[objective]['cases'] if x.get('seed')==seed and x.get('success')),None)
   if result is None:row['errors'][objective]='missing/failed fixed-budget repair';row[objective+'_joint_pass']=False;continue
   path=folder/objective/'cases'/f"{result['case']:02d}"/'coordinates.npz';assert sha256(path)==result['coordinates_sha256']
   data=np.load(path);assert raw is not None and np.array_equal(data['raw'],raw)
   try:
    row['quality'][objective]=experimental_quality(data['final'],mapping,protein['sequence'])
    row[objective+'_joint_pass']=result['metrics']['final']['joint_pass'];row['raw_joint_pass']=result['metrics']['raw']['joint_pass']
    row[objective+'_metrics']=result['metrics']['final'];d=np.linalg.norm(data['final']-raw,axis=-1);bone=np.isin(mapping['atom_names'],['N','CA','C','O'])
    row[objective+'_displacement']=dict(backbone_max=float(d[bone].max()),sidechain_max=float(d[~bone].max()) if (~bone).any() else None,atoms_over2=int((d>2).sum()),atoms_over5=int((d>5).sum()),residues_over2=len(set(mapping['residue_ids'][d>2].tolist())),residues_over5=len(set(mapping['residue_ids'][d>5].tolist())))
   except Exception:row['errors'][objective]=traceback.format_exc();row[objective+'_joint_pass']=False
  rows.append(row)
report=dict(complete=True,rows=rows,screen=continuation_screen(rows,[x['group_id'] for x in panel]),runtime_lock_sha256=sha256(r/'runtime_lock.json'),source_context_counts=dict(monomer=28,homooligomer_chain=4),scope='32 fixed proteins, three noises; iterative geometry/GT validation, no design or solver derivative claim')
audit_path=r/'audit_summary.json'
audit=json.loads(audit_path.read_text()) if audit_path.exists() else dict(complete=False,passed=0)
report['independent_audit']=audit
if not audit.get('complete') or audit.get('passed')!=64:report['screen']['continuation_screen']=False
write_json(r/'report.json',report);print(json.dumps(report['screen']))
