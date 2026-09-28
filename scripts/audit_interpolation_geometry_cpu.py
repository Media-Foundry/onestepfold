#!/usr/bin/env python3
"""Independently recompute every saved interpolation geometry on CPU FP64."""
import argparse,json
from pathlib import Path
import numpy as np
import torch
from fastglycan.hybrid_geometry import GeometryTopology
from fastglycan.paired_teacher_protocol import sha256,write_json
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root.resolve();folders=[root]
if (root/'regional_exit.json').exists():
 assert json.load(open(root/'regional_exit.json'))['success']
 folders += [root/'regional'/name for name in ['local42_43','complement']]
rows=[]
for folder in folders:
 lock=json.load(open(folder/'lock.json'))
 for case in lock['cases']:
  prep=folder/('prepare_'+case);p=prep/'packet.pt';assert sha256(p)==json.load(open(prep/'report.json'))['packet_sha256']
  packet=torch.load(p,weights_only=False,map_location='cpu');topology=GeometryTopology(packet['atoms'],packet['hard']['ref_pos'].numpy())
  for path in sorted(folder.glob(case+'_*/report.json')):
   report=json.load(open(path));assert report['complete']
   for row in report['rows']:
    cp=path.parent/row['coordinate_file'];assert sha256(cp)==row['coordinate_sha256']
    with np.load(cp) as data:x=torch.tensor(data['coordinates'],dtype=torch.float64)
    stats=topology.terms(x)[1]
    for name,value in stats.items():
     if abs(value-row['geometry'][name])>1e-4:raise ValueError(str(cp)+' '+name)
    rows.append(dict(coordinate=str(cp.relative_to(root)),sha256=sha256(cp),maximum_stat_difference=max(abs(v-row['geometry'][k]) for k,v in stats.items())))
write_json(root/'geometry_cpu_acceptance.json',dict(complete=True,coordinate_records=len(rows),rows=rows,source_sha256=sha256(Path(__file__))))
