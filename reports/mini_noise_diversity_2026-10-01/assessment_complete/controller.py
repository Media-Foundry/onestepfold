import os,json,pathlib,subprocess,time,traceback
r=pathlib.Path('/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/noise_diversity_assessment_v1_20261001_retry1')
v='/data/user/shuang886/Folding/'+r.name
prefix=['/media/IntelSSD/onestepfold/diamondhill_migration_20261001/tools/proot/usr/bin/proot','-b','/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding:/data/user/shuang886/Folding','/home/pc/anaconda3/envs/fold/bin/python','-u']
e=os.environ.copy();e.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',LAYERNORM_TYPE='torch',PROTENIX_ROOT_DIR='/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime',PYTHONPATH=v+'/code/src:'+v+'/code/scripts:'+v+'/code')
assert not (r/'handles.json').exists()
out=dict(complete=False,jobs=[],controller_pid=os.getpid());running=[]
def save(): (r/'handles.json').write_text(json.dumps(out,indent=2)+'\n')
def launch(script,args,label,gcd=0):
 cmd=prefix+[v+'/'+script]+args
 with (r/(label+'.log')).open('w') as f:p=subprocess.Popen(cmd,env=dict(e,HIP_VISIBLE_DEVICES=str(gcd),CUDA_VISIBLE_DEVICES=str(gcd)),stdout=f,stderr=subprocess.STDOUT)
 j=dict(label=label,pid=p.pid,command=cmd,start_unix=time.time(),gcd=gcd);out['jobs'].append(j);running.append(p);save();return p,j
def join(batch,seconds=3600):
 start=time.time()
 for p,j in batch:
  j['exit_code']=p.wait(timeout=max(1,seconds-time.time()+start));j['seconds']=time.time()-j['start_unix'];save()
 assert all(j['exit_code']==0 for p,j in batch),'stage failed'
try:
 assert json.loads((r/'prepare.json').read_text())['complete']
 assert all(not list((r/panel).glob('worker_*')) for panel in ['original','noise'])
 scoring=[]
 for panel in ['original','noise']:
  batch=[launch('code/scripts/evaluate_diffusion_learning.py',['--root',v+'/'+panel,'--mode','worker','--index',str(i)],panel+'_'+str(i),i) for i in range(8)]
  join(batch)
  (r/panel/'execution.json').write_text(json.dumps(dict(complete=True,workers=[dict(j,index=i) for i,(p,j) in enumerate(batch)]),indent=2)+'\n')
  if panel=='original':
   join([launch('tools/assess_noise_diversity.py',['--root',v,'--mode','replay','--arm',a],'replay_'+a,i) for a,i in [('fixed',0),('diverse',2)]])
   for a in ['fixed','diverse']:
    z=json.loads((r/panel/f'flag_replay_{a}/report.json').read_text());assert z['complete'] and z['matched_state_exact']
  scoring.append(launch('tools/assess_noise_diversity.py',['--root',v,'--mode','score','--panel',panel],'score_'+panel))
 join(scoring,7200);out['complete']=True
except Exception:
 out['error']=traceback.format_exc()
 for p in running:
  if p.poll() is None:p.terminate()
finally:
 save();(r/'controller_execution.json').write_text(json.dumps(out,indent=2)+'\n')
