import json,subprocess,time,shlex
from pathlib import Path
r=Path('/home/husrcf/Code/onestepfold/reports/esmc_29769_extraction_2026-09-27/diamondhill');out=r/'transfer_jobs.json';assert not out.exists()
dest='/media/PM982/onestepfold/data/esmc_29769_layers_12_24_36_v1_20260927'
commands=[]
for part in range(3):
 source=('/home/husrcf/Code/onestepfold_runtime/esmc_29769' if part==0 else '/media/990Pro/onestepfold/esmc_29769_20260927')+f'/part-{part:03d}/'
 cmd=['rsync','-a','--partial','--partial-dir=.rsync-partial','--info=stats2','-e','ssh -o BatchMode=yes -o ConnectTimeout=20',source,'pc@'+('DiamondHill' if part==0 else '10.120.16.9')+':'+dest+f'/part-{part:03d}/']
 if part:cmd=['ssh','-o','ConnectTimeout=20','Precision',shlex.join(cmd)]
 commands.append(cmd)
active=[];records=[]
for part,cmd in enumerate(commands):
 f=(r/f'part-{part}.log').open('x');p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT)
 active.append((part,p,f));records.append({'partition':part,'pid':p.pid,'command':cmd,'started':time.time()})
 out.write_text(json.dumps(records,indent=2)+'\n')
print(json.dumps(records),flush=True)
results=[]
for part,p,f in active:
 code=p.wait();f.close();results.append({'partition':part,'returncode':code,'finished':time.time()})
 (r/'transfer_exit.json').write_text(json.dumps(results,indent=2)+'\n')
assert all(x['returncode']==0 for x in results),results
cmd=['ssh','pc@DiamondHill','OMP_NUM_THREADS=4 /home/pc/anaconda3/envs/fold/bin/python '+dest+'/verify_esmc_29769_transfer.py --root '+dest]
with (r/'verification.log').open('x') as f:rc=subprocess.call(cmd,stdout=f,stderr=subprocess.STDOUT)
(r/'verification_exit.json').write_text(json.dumps({'returncode':rc,'finished':time.time()})+'\n');assert rc==0
print('Transfers and destination verification complete',flush=True)
