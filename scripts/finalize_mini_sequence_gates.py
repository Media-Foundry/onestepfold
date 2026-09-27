#!/usr/bin/env python3
"""Wait for specified live workers, then independently audit their frozen outputs."""
import argparse,json,os,subprocess,time
from pathlib import Path
from fastglycan.paired_teacher_protocol import write_json


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args()
    root=a.root.resolve();launch=json.loads((root/'gate_launch_v2.json').read_text())
    runs=[root/f'gate_v1_s{s}' for s in (1,2)]
    runs += [root/f'gate_v2_{w["label"]}_s{w["arm"]}' for w in launch['workers']]
    deadline=time.monotonic()+5500
    while True:
        live=[];missing=[]
        for w in launch['workers']:
            folder=root/f'gate_v2_{w["label"]}_s{w["arm"]}'
            handle=Path('/proc')/str(w['pid'])
            if handle.exists():
                # Verify PID still refers to this worker rather than an unrelated process.
                try:
                    command=(handle/'cmdline').read_bytes().replace(b'\0',b' ').decode()
                except (FileNotFoundError, ProcessLookupError):
                    command=''  # Worker exited between exists() and reading /proc.
                if str(folder) in command:live.append(w['pid'])
            report=folder/'report.json'
            if not report.exists() or not json.loads(report.read_text()).get('complete'):
                missing.append(str(folder))
        write_json(root/'finalizer_status.json',dict(stage='wait',live=live,missing=missing))
        if not live:
            if missing:raise RuntimeError(f'terminal incomplete workers: {missing}')
            break
        if time.monotonic()>deadline:raise TimeoutError('worker deadline exceeded; workers not restarted')
        time.sleep(20)
    script=Path(__file__).resolve().with_name('score_mini_sequence_gates.py')
    env=os.environ.copy();env['ROCR_VISIBLE_DEVICES']=''
    write_json(root/'finalizer_status.json',dict(stage='score'))
    cmd=[os.sys.executable,str(script),'--runs',*[str(p) for p in runs],'--out',str(root/'final_audit_v2')]
    with open(root/'final_score_v2.log','w') as log:
        rc=subprocess.call(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
    write_json(root/'finalizer_status.json',dict(stage='complete' if rc==0 else 'failed',scorer_exit_code=rc))
    if rc:raise RuntimeError(f'scorer exit {rc}')

if __name__=='__main__':main()
