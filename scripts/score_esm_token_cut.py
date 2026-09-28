#!/usr/bin/env python3
import argparse,json
from pathlib import Path
import torch
from fastglycan.interface_decomposition import dot64
from fastglycan.paired_teacher_protocol import sha256,write_json
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root.resolve();out=root/'token_cut';r=json.loads((out/'report.json').read_text())
assert r['complete'] and r['esm_baseline_exact'] and r['token_input_exact'];assert sha256(out/'baseline.pt')==r['baseline_sha256']
b=torch.load(out/'baseline.pt',map_location='cpu',weights_only=False)
assert r['chain_relative_l2_error']<1e-4
old=json.loads((root/'control/report.json').read_text());audit=dict(complete=False,rows=0,max_error=0.,artifacts={'token_cut/baseline.pt':sha256(out/'baseline.pt'),'token_cut/report.json':sha256(out/'report.json')})
lines=['# ESM token-input cut','','Actual downstream ESM-output VJP. Reuses the same control q, directions and output differences; no folding core run.','', '| Direction | h | a_E | k: token secant | n_E: ESM secant | k−a_E | n_E−k | R/C + accumulation residual |','|---:|---:|---:|---:|---:|---:|---:|---:|']
for row,prior in zip(r['rows'],old['rows']):
 f=out/row['artifact'];assert sha256(f)==row['artifact_sha256'];dT=torch.load(f,map_location='cpu',weights_only=False)['deltaT']
 previous=root/'control'/prior['artifact'];assert sha256(previous)==prior['artifact_sha256'];dH=torch.load(previous,map_location='cpu',weights_only=False)['esm_token_embedding']
 h=row['h'];di=row['direction'];aE=float(dot64(b['gq'],b['directions'][di]));k=float(dot64(b['nu'],dT)/(2*h));nE=float(dot64(b['mu'],dH)/(2*h))
 err=max(abs(aE-row['a_E']),abs(k-row['k']),abs(nE-row['n_E']));assert err<1e-10
 audit['max_error']=max(audit['max_error'],err);audit['rows']+=1;audit['artifacts']['token_cut/'+row['artifact']]=sha256(f)
 lines.append('| '+str(di)+' | '+str(h)+' | '+' | '.join(f'{v:.8g}' for v in [aE,k,nE,k-aE,nE-k,row['rc_and_accumulation_residual']])+' |')
audit['complete']=True;write_json(root/'token_audit.json',audit);(root/'token_report.md').write_text('\n'.join(lines).rstrip()+'\n')
