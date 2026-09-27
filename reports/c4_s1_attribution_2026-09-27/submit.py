import json,subprocess,time
from pathlib import Path
r=Path('/data/user/shuang886/Folding/c4_s1_attribution_v1_20260927');assert not (r/'jobs.json').exists()
assert json.loads((r/'preflight/complete.json').read_text())['complete']
jobs=dict(preflight='656868')
def submit(name,script,extra):
 cmd=['sbatch','--parsable','--kill-on-invalid-dep=yes',f'--job-name=s1-{name}',f'--output={r}/logs/{name}-%A_%a.log',*extra,str(r/script)]
 job=subprocess.check_output(cmd,text=True).strip().split(';')[0];jobs[name]=job;(r/'jobs.json').write_text(json.dumps(jobs,indent=2)+'\n');return job
a=submit('panel_a','gpu.sh',['--array=0-15%8','--export=ALL,MODE=a'])
p=submit('prepare_b','gpu.sh',['--export=ALL,MODE=prepare_b'])
b=submit('panel_b','gpu.sh',['--array=0-7%8',f'--dependency=afterok:{p}','--export=ALL,MODE=b'])
s=submit('score','score.sh',[f'--dependency=afterok:{a}:{b}','--export=ALL,PRECISION_FLAG='])
f=submit('fp32','precision.sh',['--array=0-7%8',f'--dependency=afterok:{b}'])
submit('score_fp32','score.sh',[f'--dependency=afterok:{f}:{s}','--export=ALL,PRECISION_FLAG=--precision'])
print(json.dumps(jobs,indent=2))
