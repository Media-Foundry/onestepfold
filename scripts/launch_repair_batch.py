#!/usr/bin/env python3
"""Detach the locked batch after the already-running first case, without duplication."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from fastglycan.paired_teacher_protocol import sha256, write_json

p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--first-pid',type=int,required=True)
a=p.parse_args();root=a.out.resolve();first=root/'cases/000/report.json'
proc=Path(f'/proc/{a.first_pid}')
if proc.exists():
    command=(proc/'cmdline').read_bytes().replace(b'\0',b' ')
    if b'run_geometry_repair.py' not in command or b'--case 0' not in command:
        raise RuntimeError('first-case PID identity mismatch')
    start_ticks=int((proc/'stat').read_text().split()[21])
else:
    start_ticks=None
status=dict(controller_pid=os.getpid(),first_pid=a.first_pid,first_start_ticks=start_ticks,
    lock_sha256=sha256(root/'lock.json'),source_sha256=sha256(Path(__file__)),phase='waiting_first_case')
write_json(root/'controller.json',status)
while not first.exists() and proc.exists():
    if int((proc/'stat').read_text().split()[21])!=start_ticks:
        break
    elapsed=float(Path('/proc/uptime').read_text().split()[0])-start_ticks/os.sysconf('SC_CLK_TCK')
    if elapsed>=1800:
        os.kill(a.first_pid,signal.SIGTERM)
        time.sleep(2)
        if proc.exists() and int((proc/'stat').read_text().split()[21])==start_ticks:
            os.kill(a.first_pid,signal.SIGKILL)
        break
    time.sleep(5)
if not first.exists():
    write_json(first,dict(case=0,index=0,seed=211,success=False,error='first case timeout or interrupted process',lock_sha256=status['lock_sha256']))
status['phase']='batch';write_json(root/'controller.json',status)
code=subprocess.run([sys.executable,str(Path(__file__).with_name('run_geometry_repair.py')),'--out',str(root)]).returncode
status.update(phase='finished',returncode=code);write_json(root/'controller.json',status)
sys.exit(code)
