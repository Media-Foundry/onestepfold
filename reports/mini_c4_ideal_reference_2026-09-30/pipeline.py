import json, subprocess, sys, time
from pathlib import Path
root = Path(__file__).parent
started = time.monotonic()
steps = [('batch',['run_connection_window_trial.py','--root',str(root),'--mode','batch']), ('audit',['audit_connection_window_trial.py','--root',str(root)]), ('report',['report_connection_window_trial.py','--root',str(root)]), ('regression_c4',['audit_connection_window_trial.py','--root',str(root/'regression_c4')]), ('regression_fit',['audit_connection_window_trial.py','--root',str(root/'regression_fit')]), ('regression_length',['audit_connection_window_trial.py','--root',str(root/'regression_length')])]
results = []
for name,args in steps:
    with (root/(name+'.log')).open('x') as out:
        p = subprocess.run([sys.executable,str(root/'code/scripts'/args[0]),*args[1:]],stdout=out,stderr=subprocess.STDOUT)
    results.append(dict(step=name,returncode=p.returncode))
    (root/'pipeline_status.json').write_text(json.dumps(dict(steps=results,seconds=time.monotonic()-started),indent=2))
    if p.returncode: break
(root/'pipeline_exit.json').write_text(json.dumps(dict(returncode=p.returncode,steps=results,seconds=time.monotonic()-started),indent=2))
sys.exit(p.returncode)
