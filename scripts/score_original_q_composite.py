#!/usr/bin/env python3
"""Recompute original-q JVP/VJP projections from saved tensors on CPU."""
import argparse,json
from pathlib import Path
import torch
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.interface_decomposition import dot64
from fastglycan.pairformer_precision import tree_dot
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root.resolve();out=root/'composite'
r=json.loads((out/'report.json').read_text());assert r['complete']
assert sha256(out/'baseline.pt')==r['baseline_sha256']
b=torch.load(out/'baseline.pt',map_location='cpu',weights_only=False)
lock=json.loads((root/'lock.json').read_text());f=Path(lock['prior_root'])/'run/coarse_baseline.pt'
assert sha256(f)==r['input_sha256'][str(f)]
c=torch.load(f,map_location='cpu',weights_only=False)
audit=dict(complete=False,rows=0,projections=0,max_absolute_recompute_error=0.,artifacts={'composite/report.json':sha256(out/'report.json'),'composite/baseline.pt':sha256(out/'baseline.pt')})
def check(actual,expected):
 error=abs(float(actual)-expected);assert error<1e-9,(actual,expected)
 audit['max_absolute_recompute_error']=max(audit['max_absolute_recompute_error'],error);audit['projections']+=1
for row in r['directions']:
 f=out/row['artifact'];assert sha256(f)==row['artifact_sha256'];t=torch.load(f,map_location='cpu',weights_only=False)
 check(dot64(b['gradient'],b['directions'][row['direction']]),row['analytic'])
 if row['full_jvp']['supported']:check(dot64(b['w'],t['full_coordinate_tangent']),row['full_jvp']['comparison']['left'])
 for i,boundary in enumerate(row['boundaries']):
  name=boundary['name']
  if name=='coordinates':check(dot64(b['w'],t['composed_coordinate_tangent']),boundary['projection'])
  else:check(tree_dot(c['adjoints'][i],t[name]),boundary['projection'])
 audit['rows']+=1;audit['artifacts']['composite/'+row['artifact']]=sha256(f)
audit.update(complete=True,model_deployment_accepted=False);write_json(out/'audit.json',audit)
