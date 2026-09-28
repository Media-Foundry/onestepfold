#!/usr/bin/env python3
"""CPU audit of extended-state projections, precision terms, and carry directions."""
import argparse,json
from pathlib import Path
import torch
from fastglycan.pairformer_precision import tree_dot
from fastglycan.esm_precision_reference import precision_decomposition
from fastglycan.paired_teacher_protocol import sha256,write_json
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root.resolve();out=root/'run'
assert json.loads((root/'exit.json').read_text())['success']
r=json.loads((out/'report.json').read_text());assert r['complete'] and not r['dtype_audit']['non_double'];assert not r['omitted_differentiable_reads']
assert sha256(out/'coarse_baseline.pt')==r['baseline_sha256'];assert sha256(out/'precision_baseline.pt')==r['precision_baseline_sha256']
b=torch.load(out/'coarse_baseline.pt',map_location='cpu',weights_only=False);pb=torch.load(out/'precision_baseline.pt',map_location='cpu',weights_only=False);selected=r['selection']['index']
audit=dict(complete=False,coarse_rows=0,precision_rows=0,max_error=0.,artifacts={})
lines=['# Pairformer extended-state precision diagnosis','',f"Selected: {r['selection']['name']}; selection rule: {r['selection'].get('rule', 'maximum primary-row signed-deviation magnitude')}. Carried s_init/z_init/s_inputs and all early input sources retain their own positive/negative endpoint values.",'',f"Chain reconstruction relative L2: {r['chain_reconstruction']['relative_l2']:.8g}. Native local chain: {r['local_chain']['relative_l2']:.8g}. Reference32 baseline max difference: {r['reference32_baseline_max_abs']:.8g}.",'','## Coarse signed deviations','','| Direction | h | Initialization | Recycle1 | Recycle2 | Recycle3 | Recycle4 |','|---:|---:|---:|---:|---:|---:|---:|']
for row in r['coarse_rows']:
 f=out/row['artifact'];assert sha256(f)==row['artifact_sha256'];packet=torch.load(f,map_location='cpu',weights_only=False)
 projections=[float(tree_dot(g,{k:up[k].double()-um[k].double() for k in up})/(2*row['h'])) for g,up,um in zip(b['adjoints'],packet['plus'],packet['minus'])]
 err=max(abs(x-y) for x,y in zip(projections,row['projections']));assert err<1e-10;audit['max_error']=max(audit['max_error'],err);audit['coarse_rows']+=1;audit['artifacts']['run/'+row['artifact']]=sha256(f)
 lines.append('| '+str(row['direction'])+' | '+str(row['h'])+' | '+' | '.join(f'{v:.8g}' for v in row['deviations'])+' |')
lines+=['','## Frozen-endpoint precision terms','','| Direction | h | S32 | A32 | S64 | A64 | S32−S64 | S64−A64 | A64−A32 |','|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
for row,coarse in zip(r['precision_rows'],r['coarse_rows']):
 f=out/row['artifact'];assert sha256(f)==row['artifact_sha256'];ys=torch.load(f,map_location='cpu',weights_only=False);packet=torch.load(out/coarse['artifact'],map_location='cpu',weights_only=False);h=row['h']
 vh={k:(packet['plus'][selected][k].double()-packet['minus'][selected][k].double())/(2*h) for k in packet['plus'][selected]};values={}
 for mode,g in pb['gradients'].items():
  s=float(tree_dot(pb['mu'],{k:ys[mode]['plus'][k].double()-ys[mode]['minus'][k].double() for k in pb['mu']})/(2*h));ad=float(tree_dot(g,vh));values[mode]=dict(S=s,A=ad)
  err=max(abs(s-row['values'][mode]['S']),abs(ad-row['values'][mode]['A']));assert err<1e-10;audit['max_error']=max(audit['max_error'],err)
 d=precision_decomposition(values['native32']['S'],values['native32']['A'],values['reference64']['S'],values['reference64']['A'],h)
 err=max(abs(d[k]-row[k]) for k in d);assert err<1e-10;audit['max_error']=max(audit['max_error'],err);audit['precision_rows']+=1;audit['artifacts']['run/'+row['artifact']]=sha256(f)
 lines.append('| '+str(row['direction'])+' | '+str(h)+' | '+' | '.join(f'{d[k]:.8g}' for k in ['S32','A32','S64','A64','forward_difference','reference_remainder','ad_difference'])+' |')
for name in ['coarse_baseline.pt','precision_baseline.pt','report.json']:audit['artifacts']['run/'+name]=sha256(out/name)
audit['complete']=True;write_json(root/'audit.json',audit);(root/'report.md').write_text('\n'.join(lines).rstrip()+'\n')
write_json(root/'acceptance.json',dict(complete=True,model_deployment_accepted=False,audit_sha256=sha256(root/'audit.json'),report_sha256=sha256(root/'report.md')))
