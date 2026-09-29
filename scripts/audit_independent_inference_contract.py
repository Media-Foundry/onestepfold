#!/usr/bin/env python3
"""CPU artifact audit of the locked32x3 native FP32/C4/S1 input/output contract."""
import argparse,json
from pathlib import Path
import numpy as np
from fastglycan.paired_teacher_protocol import sha256,write_json

p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=a.root
panel=json.loads((r/'panel32.json').read_text());lock=json.loads((r/'runtime_lock.json').read_text());assert sha256(r/'panel32.json')==lock['panel_sha256']
assert len(panel)==32 and [sum(x['stratum']==i for x in panel) for i in range(4)]==[8]*4
checks=[];missing=[]
for row in panel:
 folder=r/'proteins'/row['group_id'];path=folder/'raw/report.json'
 if not path.exists():missing.append(dict(group_id=row['group_id'],reason='raw report absent'));continue
 report=json.loads(path.read_text());assert report['runtime_lock_sha256']==sha256(r/'runtime_lock.json')
 assert report['group_id']==row['group_id'] and report['pdb_id']==row['pdb_id']
 with np.load(folder/'chemical_reference.npz') as f:reference={k:f[k] for k in ['atom_names','residue_ids','chain_ids']}
 if not report['complete']:missing.append(dict(group_id=row['group_id'],reason='raw report incomplete',error=report.get('error')))
 if 'model' in report:assert report['model']==lock['model']=='protenix_mini_esm_v0.5.0'
 assert set(report['results'])<=set(map(str,lock['noises']))
 if report['results']:
  assert report['conditioning_cycles']==4 and report['conditioning_shared_across_three_noises']
  assert report['resolved_config']['dtype']=='fp32'
 for seed in lock['noises']:
  item=report['results'].get(str(seed))
  if item is None:missing.append(dict(group_id=row['group_id'],seed=seed,reason='prediction missing'));continue
  file=Path(item['file']);assert sha256(file)==item['sha256']
  with np.load(file) as f:
   x=f['coordinates'];assert x.shape==(len(reference['atom_names']),3) and x.dtype==np.float32 and np.isfinite(x).all()
   for k,v in reference.items():assert np.array_equal(f[k],v)
   assert str(f['sequence'])==row['sequence']
  assert item['diffusion_nfe']==1 and item['schedule']==[2560.,0.]
  assert item['initial_noise']=='identity-key' and item['augmentation']=='identity' and item['mc_dropout'] is False
  assert item['gamma0']==0 and item['noise_scale_lambda']==item['step_scale_eta']==1 and item['stable_euler'] is True
  checks.append(dict(group_id=row['group_id'],pdb_id=row['pdb_id'],seed=seed,atoms=len(x),coordinate_sha256=item['sha256'],report_sha256=sha256(path)))
result=dict(complete=len(checks)==96 and not missing,checked=len(checks),expected=96,missing=missing,checks=checks,runtime_lock_sha256=sha256(r/'runtime_lock.json'),script_sha256=sha256(Path(__file__)),scope='artifact identity/dtype/config/call-trace audit, not independent rerun or geometry/quality acceptance')
write_json(a.out,result);print(json.dumps({k:v for k,v in result.items() if k!='checks'}))
