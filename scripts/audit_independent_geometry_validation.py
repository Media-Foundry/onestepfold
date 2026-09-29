#!/usr/bin/env python3
"""Run the existing independent CPU audit on all64 locked repair groups."""
import argparse,concurrent.futures,json,os,subprocess,sys,time
from pathlib import Path
from fastglycan.paired_teacher_protocol import sha256,write_json

p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();r=a.root;panel=json.loads((r/'panel32.json').read_text())
jobs=[(x['group_id'],method) for x in panel for method in ['mean','tail']]

def audit_one(job):
 g,method=job;folder=r/'proteins'/g/method;t=time.monotonic()
 try:
  with (folder/'audit.log').open('x') as log:
   result=subprocess.run([sys.executable,str(r/'code/scripts/audit_anchored_geometry.py'),'--root',str(folder)],stdout=log,stderr=log,timeout=900,env=dict(os.environ,ROCR_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1'))
  file=folder/'audit.json';ok=result.returncode==0 and file.exists()
  return dict(group_id=g,method=method,passed=ok,returncode=result.returncode,seconds=time.monotonic()-t,audit_sha256=sha256(file) if file.exists() else None)
 except Exception as e:return dict(group_id=g,method=method,passed=False,error=repr(e),seconds=time.monotonic()-t)

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:rows=list(ex.map(audit_one,jobs))
write_json(r/'audit_summary.json',dict(complete=True,groups=64,passed=sum(x['passed'] for x in rows),rows=rows))
