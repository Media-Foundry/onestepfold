#!/usr/bin/env python3
"""CPU verification of saved reference-diffusion projections and full VJPs."""
import argparse,json
from pathlib import Path
import torch
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.interface_decomposition import dot64
from fastglycan.pairformer_precision import tree_dot
from fastglycan.vjp_comparison import compare_fields
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);root=p.parse_args().root.resolve();out=root/'diffusion_jvp_reference';r=json.loads((out/'report.json').read_text());assert r['complete'];assert sha256(out/'baseline.pt')==r['baseline_sha256'];assert sha256(root/'composite/report.json')==r['composite_report_sha256']
b=torch.load(out/'baseline.pt',map_location='cpu',weights_only=False);v=compare_fields(b['gradients']['native32'],b['gradients']['math32']);assert v==r['full_vjp_comparison']
audit=dict(complete=False,rows=0,max_projection_error=0.,artifacts={'diffusion_jvp_reference/report.json':sha256(out/'report.json'),'diffusion_jvp_reference/baseline.pt':sha256(out/'baseline.pt')})
for row in r['rows']:
 f=out/row['artifact'];assert sha256(f)==row['artifact_sha256'];x=torch.load(f,map_location='cpu',weights_only=False)
 values=[float(dot64(b['w'],x['coordinate_tangent'])),float(tree_dot(b['gradients']['native32'],x['tangent'])),float(tree_dot(b['gradients']['math32'],x['tangent']))]
 expected=[row[k] for k in ['reference_jvp','native_interface_vjp','reference_interface_vjp']]
 error=max(abs(a-b) for a,b in zip(values,expected));assert error<1e-9;audit['max_projection_error']=max(audit['max_projection_error'],error);audit['rows']+=1;audit['artifacts']['diffusion_jvp_reference/'+row['artifact']]=sha256(f)
audit['complete']=True;write_json(out/'audit.json',audit)
