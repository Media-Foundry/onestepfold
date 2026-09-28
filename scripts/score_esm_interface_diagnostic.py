#!/usr/bin/env python3
"""CPU replay of early-interface projections and nested response deviations."""
import argparse,json
from pathlib import Path
import torch
from fastglycan.interface_decomposition import dot64
from fastglycan.esm_interface_diagnostics import nested_decomposition,EARLY_NAMES
from fastglycan.paired_teacher_protocol import sha256,write_json
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root.resolve();out=root/'control'
assert json.loads((root/'exit.json').read_text())['success']
r=json.loads((out/'report.json').read_text());assert r['complete'] and r['cut_forward_exact'] and r['archived_interface_exact']
assert not r['omitted_differentiable_reads'];assert sha256(out/'baseline.pt')==r['baseline_sha256']
b=torch.load(out/'baseline.pt',map_location='cpu',weights_only=False)
audit=dict(complete=False,rows=[],max_projection_error=0.,artifacts={'control/baseline.pt':sha256(out/'baseline.pt'),'control/report.json':sha256(out/'report.json')})
lines=['# ESM-output interface localization','','Only control_a1_s1, unchanged q/directions/h. n projects the complete ESM-output/token/chemistry interface; m projects the complete diffusion interface. No chemistry acceptance prerequisite.','',f"Cut exact: {r['cut_forward_exact']}; archived b0 exact: {r['archived_interface_exact']}; chain relative L2 error: {r['chain_relative_l2_error']:.8g}; previous direct-gradient relative L2 difference: {r['previous_direct_relative_l2']:.8g}.",'','| Direction | h | a | n | m | d | n−a | m−n | d−m |','|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
for row in r['rows']:
 assert row['late_delta_exact'];f=out/row['artifact'];assert sha256(f)==row['artifact_sha256'];delta=torch.load(f,map_location='cpu',weights_only=False)
 parts={k:float(dot64(b['mu'][k],delta[k])/(2*row['h'])) for k in EARLY_NAMES}
 analytic=float(dot64(b['direct'],b['directions'][row['direction']]))
 new=nested_decomposition(analytic,sum(parts.values()),row['prior_m'],row['d']);error=max(abs(new[k]-row[k]) for k in new)
 assert error<1e-10,(row['direction'],row['h'],error)
 audit['max_projection_error']=max(audit['max_projection_error'],error);audit['rows'].append(dict(direction=row['direction'],h=row['h'],components=parts,**new));audit['artifacts']['control/'+row['artifact']]=sha256(f)
 lines.append('| '+str(row['direction'])+' | '+str(row['h'])+' | '+' | '.join(f'{new[k]:.8g}' for k in ['a','n','m','d','before_esm_output','input_embedder_and_pairformer','diffusion'])+' |')
audit['complete']=True;write_json(root/'audit.json',audit);(root/'report.md').write_text('\n'.join(lines).rstrip()+'\n')
write_json(root/'acceptance.json',dict(complete=True,model_deployment_accepted=False,audit_sha256=sha256(root/'audit.json'),report_sha256=sha256(root/'report.md')))
