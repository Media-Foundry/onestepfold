#!/usr/bin/env python3
"""Explain existing FD perturbations in units of the near-coincident pair distance."""
import argparse,json,hashlib
from pathlib import Path
import torch

p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
report=json.load(open(a.source/'report.json'));path=a.source/'coordinates.pt'
assert hashlib.sha256(path.read_bytes()).hexdigest()==report['coordinate_sha256']
coordinates=torch.load(path,weights_only=True);base=coordinates['x0'].reshape(-1,3).double();pair=report['rows'][0]['top_pairs'][0];i=pair['first']['index'];j=pair['second']['index'];r0=base[i]-base[j];distance=float(r0.norm());rows=[]
for row in report['rows']:
 h=row['h'];xp=coordinates['plus_'+str(h)].double();xm=coordinates['minus_'+str(h)].double();dp=float(((xp[i]-xp[j])-r0).norm());dm=float(((xm[i]-xm[j])-r0).norm())
 rows.append(dict(h=h,plus_relative_vector_displacement=dp,minus_relative_vector_displacement=dm,rho=max(dp,dm)/distance))
a.out.write_text(json.dumps(dict(source_coordinate_sha256=report['coordinate_sha256'],base_distance=distance,first=pair['first'],second=pair['second'],rows=rows,interpretation='coordinate-scale diagnostic only; original FD gates unchanged; prior signed remainder fractions are not gradient-error fractions'),indent=2)+'\n')
print(json.dumps(rows))
