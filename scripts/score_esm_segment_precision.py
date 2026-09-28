#!/usr/bin/env python3
"""Independent CPU replay of saved boundary and precision-response tensors."""
import argparse,json
from pathlib import Path
import torch
from fastglycan.interface_decomposition import dot64
from fastglycan.esm_precision_reference import precision_decomposition
from fastglycan.paired_teacher_protocol import sha256,write_json
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root.resolve();out=root/'run'
assert json.loads((root/'exit.json').read_text())['success']
r=json.loads((out/'report.json').read_text());assert r['complete'] and not r['dtype_audit']['non_double']
for name,key in [('coarse_baseline.pt','baseline_sha256'),('precision_baseline.pt','precision_baseline_sha256'),('native_rope.pt','rope_sha256')]:assert sha256(out/name)==r[key]
b=torch.load(out/'coarse_baseline.pt',map_location='cpu',weights_only=False);pbase=torch.load(out/'precision_baseline.pt',map_location='cpu',weights_only=False);selected=r['selected_segment']
audit=dict(complete=False,coarse_rows=0,precision_rows=0,max_projection_error=0.,max_decomposition_error=0.,artifacts={})
lines=['# Frozen-endpoint ESM segment precision diagnosis','',f"Selected segment: {r['selection']['start']} → {r['selection']['end']}, by predeclared direction0/h=.003 max absolute deviation.",'',f"Native segment chain relative error: {r['native_local_chain_relative_l2']:.6g}. ReferenceFP32 baseline max difference: {r['reference32_baseline_max_abs']:.6g}. FP64 floating outputs: {r['dtype_audit']['counts']}; hidden lower precision: {r['dtype_audit']['non_double']}.",'','## Coarse signed segment deviations','','| Direction | h | First third | Middle third | Last third | Final norm |','|---:|---:|---:|---:|---:|---:|']
for row in r['coarse_rows']:
 f=out/row['artifact'];assert sha256(f)==row['artifact_sha256'];packet=torch.load(f,map_location='cpu',weights_only=False)
 projections=[float(dot64(g,up.double()-um.double())/(2*row['h'])) for g,up,um in zip(b['lambdas'],packet['plus'],packet['minus'])]
 error=max(abs(x-y) for x,y in zip(projections,row['projections']));assert error<1e-10;audit['max_projection_error']=max(audit['max_projection_error'],error);audit['coarse_rows']+=1
 lines.append('| '+str(row['direction'])+' | '+str(row['h'])+' | '+' | '.join(f'{v:.8g}' for v in row['deviations'])+' |')
 audit['artifacts']['run/'+row['artifact']]=sha256(f)
lines+=['','## Three-term precision decomposition','','Native gap = forward difference + high-precision finite-endpoint remainder + local AD difference. The second term is not labelled pure curvature.','', '| Direction | h | S32 | A32 | S64 | A64 | S32−S64 | S64−A64 | A64−A32 |','|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
for row,coarse in zip(r['precision_rows'],r['coarse_rows']):
 f=out/row['artifact'];assert sha256(f)==row['artifact_sha256'];ys=torch.load(f,map_location='cpu',weights_only=False);endpoints=torch.load(out/coarse['artifact'],map_location='cpu',weights_only=False);h=row['h']
 vh=(endpoints['plus'][selected].double()-endpoints['minus'][selected].double())/(2*h);values={}
 for mode,g in pbase['gradients'].items():
  s=float(dot64(pbase['mu'],ys[mode]['plus'].double()-ys[mode]['minus'].double())/(2*h));ad=float(dot64(g,vh));values[mode]=dict(S=s,A=ad)
  err=max(abs(s-row['values'][mode]['S']),abs(ad-row['values'][mode]['A']));assert err<1e-10;audit['max_projection_error']=max(audit['max_projection_error'],err)
 d=precision_decomposition(values['native32']['S'],values['native32']['A'],values['reference64']['S'],values['reference64']['A'],h)
 error=max(abs(d[k]-row[k]) for k in d);assert error<1e-10;audit['max_decomposition_error']=max(audit['max_decomposition_error'],error);audit['precision_rows']+=1
 lines.append('| '+str(row['direction'])+' | '+str(h)+' | '+' | '.join(f'{d[k]:.8g}' for k in ['S32','A32','S64','A64','forward_difference','reference_remainder','ad_difference'])+' |')
 audit['artifacts']['run/'+row['artifact']]=sha256(f)
for name in ['report.json','coarse_baseline.pt','precision_baseline.pt','native_rope.pt']:audit['artifacts']['run/'+name]=sha256(out/name)
lines+=['','Endpoint midpoint shifts, raw numerator-scaled terms, referenceFP32 controls, JVP/VJP comparisons and dtype records are retained in run/report.json. All same-target direction/h counts are diagnostic, not population statistics.','']
audit['complete']=True;write_json(root/'audit.json',audit);(root/'report.md').write_text('\n'.join(lines).rstrip()+'\n')
write_json(root/'acceptance.json',dict(complete=True,model_deployment_accepted=False,audit_sha256=sha256(root/'audit.json'),report_sha256=sha256(root/'report.md')))
