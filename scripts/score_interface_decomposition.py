#!/usr/bin/env python3
"""Independent CPU projection replay of the full-interface decomposition."""
import argparse,json
from pathlib import Path
import torch
from fastglycan.interface_decomposition import dot64,decompose_response,INTERFACE_NAMES
from fastglycan.paired_teacher_protocol import sha256,write_json
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root.resolve()
assert json.loads((root/'exit.json').read_text())['success']
audit=dict(complete=False,rows=0,max_projection_error=0.,artifacts={},cases={})
lines=['# Complete-interface response decomposition','','All values below concern a fixed coordinate projection, not a geometry acceptance verdict. Full reference chemistry crosses the cut; direct KL is separately recorded.','']
for case in ['control','8bzn']:
 out=root/case;r=json.loads((out/'report.json').read_text());assert r['complete'] and r['cut_forward_exact'] and not r['omitted_differentiable_reads']
 assert sha256(out/'baseline.pt')==r['baseline_sha256']
 b=torch.load(out/'baseline.pt',map_location='cpu',weights_only=False)
 assert r['chain_l2_error']<=1e-10+1e-4*r['direct_gradient_norm']
 lines += [f'## {case}', '',f"Cut forward exact: {r['cut_forward_exact']}; chain relative L2 error: {r['chain_relative_l2_error']:.6g}; archived baseline max difference: {r['archived_forward_max_abs']:.6g}; perturbed replay max difference: {r['max_archived_perturbed_replay_error']:.6g}.",'', '| Direction | h | a: AD | m: interface | d: coordinates | m−a upstream | d−m downstream |','|---:|---:|---:|---:|---:|---:|---:|']
 reconstructed=[]
 for row in r['rows']:
  f=out/row['artifact'];assert sha256(f)==row['artifact_sha256'];audit['artifacts'][str(f.relative_to(root))]=sha256(f)
  payload=torch.load(f,map_location='cpu',weights_only=False);h=row['h'];di=row['direction']
  analytic=float(dot64(b['direct'],b['directions'][di]));parts={k:float(dot64(b['lambda_'][k],payload['delta'][k])/(2*h)) for k in INTERFACE_NAMES}
  d=float(dot64(b['w'],payload['coordinate_delta'])/(2*h));new=decompose_response(analytic,sum(parts.values()),d)
  error=max(abs(new[k]-row[k]) for k in new);assert error<1e-10,(case,di,h,error)
  audit['max_projection_error']=max(audit['max_projection_error'],error);audit['rows']+=1
  reconstructed.append(dict(direction=di,h=h,**new,components=parts))
  lines.append(f"| {di} | {h} | {analytic:.8g} | {new['m']:.8g} | {d:.8g} | {new['upstream_deviation']:.8g} | {new['downstream_deviation']:.8g} |")
  del payload
 audit['cases'][case]=reconstructed;audit['artifacts'][str((out/'baseline.pt').relative_to(root))]=sha256(out/'baseline.pt');audit['artifacts'][str((out/'report.json').relative_to(root))]=sha256(out/'report.json')
 lines += ['', 'Per-component projections and exact FP64 interface-delta tensors are archived on DiamondHill. Upstream/downstream denote numerical and local-linearization deviations, not certified implementation bugs.','']
audit['complete']=True;write_json(root/'audit.json',audit);(root/'report.md').write_text('\n'.join(lines).rstrip()+'\n')
write_json(root/'acceptance.json',dict(complete=True,model_deployment_accepted=False,audit_sha256=sha256(root/'audit.json'),report_sha256=sha256(root/'report.md')))
