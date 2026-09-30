import json,subprocess,sys,time
from pathlib import Path
root=Path(__file__).parent;start=time.monotonic();steps=[]
work=[('batch',['run_connection_window_trial.py','--root',str(root),'--mode','batch']),('audit',['audit_connection_window_trial.py','--root',str(root)]),('report',['report_connection_window_trial.py','--root',str(root)])]
work += [(label,['audit_connection_window_trial.py','--root',str(root/label)]) for label in ['regression_ideal','regression_fitted']]
for name,args in work:
 with (root/(name+'.log')).open('x') as out:p=subprocess.run([sys.executable,str(root/'code/scripts'/args[0]),*args[1:]],stdout=out,stderr=subprocess.STDOUT)
 steps.append(dict(step=name,returncode=p.returncode));(root/'pipeline_status.json').write_text(json.dumps(dict(steps=steps,seconds=time.monotonic()-start),indent=2))
 if p.returncode:break
(root/'pipeline_exit.json').write_text(json.dumps(dict(returncode=p.returncode,steps=steps,seconds=time.monotonic()-start),indent=2));sys.exit(p.returncode)
