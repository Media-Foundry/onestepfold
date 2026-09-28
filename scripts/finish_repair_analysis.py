#!/usr/bin/env python3
"""Wait for an existing live batch and summarize it once; never launches repair."""
import argparse,json,os,subprocess,sys,time
from pathlib import Path
from fastglycan.paired_teacher_protocol import sha256,write_json
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--controller-pid',type=int,required=True);a=p.parse_args();root=a.root.resolve()
proc=Path(f'/proc/{a.controller_pid}');report=root/'report.json';start=time.monotonic()
if not report.exists():
 assert proc.exists(),'controller absent; inspect before collecting'
 assert b'launch_repair_batch.py' in (proc/'cmdline').read_bytes(),'PID identity mismatch'
 birth=int((proc/'stat').read_text().split()[21])
receipt=dict(pid=os.getpid(),controller_pid=a.controller_pid,source_sha256=sha256(Path(__file__)),phase='waiting')
write_json(root/'analysis_controller.json',receipt)
while not report.exists():
 if time.monotonic()-start>8*3600:
  receipt.update(phase='timeout',note='collection timeout only; no repair processes stopped');break
 if not proc.exists() or int((proc/'stat').read_text().split()[21])!=birth:
  receipt.update(phase='controller_missing',note='no final report; inspect worker state, do not restart automatically');break
 time.sleep(30)
else:
 command=[sys.executable,str(Path(__file__).with_name('summarize_repair_outcomes.py')),'--root',str(root)]
 code=subprocess.run(command).returncode
 receipt.update(phase='finished',returncode=code)
 if code==0:
  receipt['analysis_sha256']=sha256(root/'outcome_analysis.json')
receipt['seconds']=time.monotonic()-start;write_json(root/'analysis_controller.json',receipt)
