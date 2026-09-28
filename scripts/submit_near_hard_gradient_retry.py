#!/usr/bin/env python3
"""Bounded, idempotent retry of the already authorized DiamondHill submission."""
import argparse,io,json,shlex,subprocess,tarfile,time
from pathlib import Path

p=argparse.ArgumentParser();p.add_argument('--attempts',type=int,default=5);p.add_argument('--interval',type=int,default=60);a=p.parse_args();repo=Path(__file__).resolve().parents[1];report=repo/'reports/mini_near_hard_gradient_2026-09-28';lock=json.load(open(report/'lock.json'))
remote_root='/media/PM982/onestepfold/mini_near_hard_gradient_v1_20260928'
remote='''import os,sys,json,tarfile,hashlib,subprocess
from pathlib import Path
r=Path('/media/PM982/onestepfold/mini_near_hard_gradient_v1_20260928')
if (r/'controller_launch.json').exists():
 print(json.dumps(dict(status='already_submitted',launch=json.load(open(r/'controller_launch.json')))));sys.exit(0)
if (r/'submission.lock').exists():raise RuntimeError('submission lock exists; inspect before any retry')
if not (r/'code/src/fastglycan/stage0_confirm_runtime.py').exists():raise RuntimeError('base code snapshot absent')
with tarfile.open(fileobj=sys.stdin.buffer,mode='r|') as archive:archive.extractall(r,filter='data')
lock=json.load(open(r/'lock.json'))
for name,h in lock['source_sha256'].items():
 if hashlib.sha256((r/'code'/name).read_bytes()).hexdigest()!=h:raise RuntimeError('source mismatch '+name)
if hashlib.sha256((r/'protocol.md').read_bytes()).hexdigest()!=lock['protocol_sha256']:raise RuntimeError('protocol mismatch')
fd=os.open(r/'submission.lock',os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
with open(r/'controller.log','w') as log:
 process=subprocess.Popen(['/home/pc/anaconda3/envs/fold/bin/python',str(r/'code/scripts/launch_near_hard_gradient.py'),'--root',str(r)],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
launch=dict(pid=process.pid);(r/'controller_launch.json').write_text(json.dumps(launch));print(json.dumps(dict(status='submitted',launch=launch)))
'''
buffer=io.BytesIO()
with tarfile.open(fileobj=buffer,mode='w') as archive:
 names=set(lock['source_sha256'])|{'scripts/launch_near_hard_gradient.py','scripts/score_near_hard_gradient.py','scripts/report_near_hard_gradient.py'}
 for name in sorted(names):archive.add(repo/name,arcname='code/'+name)
 archive.add(report/'lock.json',arcname='lock.json');archive.add(report/'protocol.md',arcname='protocol.md')
command=['ssh','-o','ConnectTimeout=10','-o','ConnectionAttempts=1','-o','ServerAliveInterval=10','-o','ServerAliveCountMax=2','pc@DiamondHill','/home/pc/anaconda3/envs/fold/bin/python -c '+shlex.quote(remote)]
history=[]
for attempt in range(1,a.attempts+1):
 try:
  result=subprocess.run(command,input=buffer.getvalue(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=45)
  row=dict(attempt=attempt,returncode=result.returncode,stdout=result.stdout.decode(errors='replace'),stderr=result.stderr.decode(errors='replace'))
 except subprocess.TimeoutExpired:row=dict(attempt=attempt,returncode=None,stderr='local45s SSH deadline')
 history.append(row);(report/'submission_retry.json').write_text(json.dumps(dict(complete=False,attempts=history),indent=2))
 if row['returncode']==0:
  (report/'submission_retry.json').write_text(json.dumps(dict(complete=True,submitted=True,attempts=history),indent=2));print(row['stdout']);break
 if row['returncode'] not in (255,None):
  (report/'submission_retry.json').write_text(json.dumps(dict(complete=True,submitted=False,requires_inspection=True,attempts=history),indent=2));raise RuntimeError(row)
 if attempt<a.attempts:time.sleep(a.interval)
else:(report/'submission_retry.json').write_text(json.dumps(dict(complete=True,submitted=False,attempts=history),indent=2))
