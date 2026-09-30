import json,os,pathlib,subprocess,time,traceback,hashlib
r=pathlib.Path('/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/noise_diversity_training_v1_20261001_retry1')
v='/data/user/shuang886/Folding/noise_diversity_training_v1_20261001_retry1'
prefix=['/media/IntelSSD/onestepfold/diamondhill_migration_20261001/tools/proot/usr/bin/proot','-b','/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding:/data/user/shuang886/Folding','/home/pc/anaconda3/envs/fold/bin/python','-u']
env=os.environ.copy();env.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',LAYERNORM_TYPE='torch',PROTENIX_ROOT_DIR='/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime',PYTHONPATH=v+'/code/src:'+v+'/code/scripts:'+v+'/code')
assert not (r/'handles.json').exists()
started=time.time();jobs=[];running=[];out=dict(complete=False,controller_pid=os.getpid(),jobs=jobs)
def save():
 (r/'handles.json').write_text(json.dumps(out,indent=2)+'\n')
def launch(script,args,label,gcd):
 command=prefix+[v+'/code/scripts/'+script,'--root',v]+args
 e=dict(env,HIP_VISIBLE_DEVICES=str(gcd),CUDA_VISIBLE_DEVICES=str(gcd))
 with (r/(label+'.log')).open('w') as f:p=subprocess.Popen(command,env=e,stdout=f,stderr=subprocess.STDOUT)
 j=dict(label=label,pid=p.pid,command=command,start_unix=time.time(),gcd=gcd);jobs.append(j);running.append(p);save();return p,j
def join(batch,limit):
 start=time.time()
 for p,j in batch:
  j['exit_code']=p.wait(timeout=max(1,limit-(time.time()-start)));j['observed_seconds']=time.time()-j['start_unix'];save()
 assert all(j['exit_code']==0 for p,j in batch),'stage failed; no automatic retries'
try:
 teachers=[launch('prepare_noise_diversity.py',['--mode','worker','--index',str(i)],f'teacher_{i}',i) for i in range(8)]
 join(teachers,3600)
 (r/'teacher_execution.json').write_text(json.dumps(dict(complete=True,jobs=[dict(j,index=i) for i,(p,j) in enumerate(teachers)]),indent=2)+'\n')
 join([launch('prepare_noise_diversity.py',['--mode','collect'],'teacher_collect',0)],1800)
 for arm,gcd in [('fixed',0),('diverse',2)]:join([launch('train_noise_diversity.py',['--mode','prepare','--arm',arm],'prepare_'+arm,gcd)],1800)
 pre=[launch('train_noise_diversity.py',['--mode','preflight','--arm',a],'preflight_'+a,g) for a,g in [('fixed',0),('diverse',2)]]
 join(pre,1800)
 a=json.loads((r/'fixed/lock.json').read_text());b=json.loads((r/'diverse/lock.json').read_text())
 assert all(a[k]==b[k] for k in a if k not in ['orders','noise_diversity'])
 assert [(x['group_id'],x['epoch']) for x in a['orders']['expanded']]==[(x['group_id'],x['epoch']) for x in b['orders']['expanded']]
 pa=json.loads((r/'fixed/preflight/report.json').read_text());pb=json.loads((r/'diverse/preflight/report.json').read_text())
 assert pa['complete'] and pb['complete'] and pa['initial_sha256']==pb['initial_sha256']
 assert [(x['group_id'],x['loss'],x['gradient_norm']) for x in pa['cases']]==[(x['group_id'],x['loss'],x['gradient_norm']) for x in pb['cases']]
 (r/'pair_release.json').write_text(json.dumps(dict(complete=True,locks={x:hashlib.sha256((r/x/'lock.json').read_bytes()).hexdigest() for x in ['fixed','diverse']},same_start=True,same_preflight_loss_and_gradient_norm=True),indent=2)+'\n')
 training=[launch('train_noise_diversity.py',['--mode','train','--arm',a],'train_'+a,g) for a,g in [('fixed',0),('diverse',2)]]
 join(training,14400)
 out['complete']=True
except Exception:
 out['error']=traceback.format_exc()
 for p in running:
  if p.poll() is None:p.terminate()
finally:
 out['seconds']=time.time()-started
 (r/'controller_execution.json').write_text(json.dumps(out,indent=2)+'\n')
