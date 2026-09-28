#!/usr/bin/env python3
"""CPU-only full VJP metrics from already saved local-precision artifacts."""
import argparse,json
from pathlib import Path
import torch
from fastglycan.vjp_comparison import compare_fields
from fastglycan.esm_interface_diagnostics import EARLY_NAMES
from fastglycan.paired_teacher_protocol import sha256,write_json
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--include-recycle',action='store_true');a=p.parse_args();root=a.root.resolve()
sources={'esm25_36':Path('/media/PM982/onestepfold/mini_esm_segment_precision_v1_20260928/run/precision_baseline.pt'),'initialization':Path('/media/PM982/onestepfold/mini_pairformer_precision_v1_20260928/run/precision_baseline.pt')}
if a.include_recycle:sources['recycle1']=root/'run/precision_baseline.pt'
r=dict(complete=True,scope='fixed output cotangent full VJP, not full Jacobian',sources={},comparisons={})
for label,f in sources.items():
 b=torch.load(f,map_location='cpu',weights_only=False);g32=b['gradients']['native32'];g64=b['gradients']['reference64'];identity=None
 if isinstance(g32,torch.Tensor):g32={'hidden':g32};g64={'hidden':g64}
 elif label=='initialization':identity={k:b['mu'][k] for k in EARLY_NAMES}
 elif label=='recycle1':identity={k:b['mu'][k] for k in g32 if k not in ('s','z')}
 r['sources'][label]=dict(path=str(f),sha256=sha256(f));r['comparisons'][label]=compare_fields(g32,g64,identity)
write_json(root/'full_vjp_comparison.json',r)
