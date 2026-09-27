import json,subprocess
from pathlib import Path
r=Path('/data/user/shuang886/Folding/c4_s1_attribution_v1_20260927');assert json.loads((r/'precision_preflight_v2_0/complete.json').read_text())['complete'];assert not (r/'jobs_precision_v2.json').exists()
p=subprocess.check_output(['sbatch','--parsable','--kill-on-invalid-dep=yes','--array=0-7%8','--job-name=s1-fp32-v2','--export=ALL,PREFLIGHT_FLAG=',f'--output={r}/logs/fp32-v2-%A_%a.log',str(r/'precision_v2.sh')],text=True).strip()
(r/'jobs_precision_v2.json').write_text(json.dumps(dict(preflight='656987',fp32=p),indent=2))
s=subprocess.check_output(['sbatch','--parsable','--kill-on-invalid-dep=yes','--job-name=s1-score-fp32-v2',f'--dependency=afterok:{p}','--export=ALL,PRECISION_FLAG=--precision --precision-prefix precision_v2_',f'--output={r}/logs/score-fp32-v2-%j.log',str(r/'score_v2.sh')],text=True).strip()
(r/'jobs_precision_v2.json').write_text(json.dumps(dict(preflight='656987',fp32=p,score=s),indent=2));print(p,s)
