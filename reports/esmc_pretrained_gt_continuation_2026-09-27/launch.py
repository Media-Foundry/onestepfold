import json,subprocess,time
from pathlib import Path
r=Path('/data/user/shuang886/Folding/esmc_pretrained_gt_continuation_v1_20260927')
out=r/'jobs.json';assert not out.exists()
jobs={'root':str(r),'created':time.time(),'training':{},'audit':{},'score':{}}
def submit(script,name,dependency=None,size=None):
 cmd=['sbatch','--parsable','--job-name='+name,'--output='+str(r/(name+'_%j.log'))]
 if dependency:cmd+=['--dependency=afterany:'+str(dependency)]
 if size:cmd+=['--export=ALL,SIZE='+str(size)]
 if script=='train':cmd+=['--nodelist=ACD1-52']
 cmd+=[str(r/'orchestration'/(script+'.sh'))]
 return int(subprocess.check_output(cmd,universal_newlines=True).strip().split(';')[0])
for size in [2048,8192]:
 jobs['training'][str(size)]=submit('train','gtcont'+str(size),size=size)
 out.write_text(json.dumps(jobs,indent=2)+'\n')
for size in [2048,8192]:
 jobs['audit'][str(size)]=submit('audit','gtca'+str(size),jobs['training'][str(size)],size)
 out.write_text(json.dumps(jobs,indent=2)+'\n')
 jobs['score'][str(size)]=submit('score','gtcs'+str(size),jobs['audit'][str(size)],size)
 out.write_text(json.dumps(jobs,indent=2)+'\n')
jobs['report']=submit('report','gtcr',':'.join(str(x) for x in jobs['score'].values()))
out.write_text(json.dumps(jobs,indent=2)+'\n');print(json.dumps(jobs))
