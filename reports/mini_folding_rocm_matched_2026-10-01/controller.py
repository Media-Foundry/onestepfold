import hashlib,json,os,signal,subprocess,sys,time,traceback
from pathlib import Path
root=Path(__file__).parent;virtual='/data/user/shuang886/Folding/rocm_matched_training_v1_20261001'
base='/data/user/shuang886/Folding';start=time.monotonic();history=[]
sys.path.insert(0,str(root/'weak/code/src'))
from fastglycan.rocm_matched_training import validate_rocm_pair

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def launch(mode,arm):
 code=virtual+'/'+arm+'/code';env=dict(os.environ,ROCR_VISIBLE_DEVICES={'weak':'0','strong':'2'}[arm],OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',LAYERNORM_TYPE='torch',PROTENIX_ROOT_DIR=base+'/protenix_stage0_pkg/v1_1/runtime',PYTHONPATH=code+'/src:'+code+'/scripts:'+code)
 command=['/media/IntelSSD/onestepfold/diamondhill_migration_20261001/tools/proot/usr/bin/proot','-b','/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding:'+base,'/home/pc/anaconda3/envs/fold/bin/python','-u',code+'/scripts/train_folding_rocm_matched.py','--root',virtual+'/'+arm,'--arm',arm,'--mode',mode]
 log=(root/f'{arm}_{mode}.log').open('w');p=subprocess.Popen(command,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 record=dict(mode=mode,arm=arm,pid=p.pid,start_unix=time.time(),command=command);history.append(record)
 (root/'handles.json').write_text(json.dumps(dict(controller=os.getpid(),jobs=history),indent=2)+'\n')
 return p,log,record
def finish(item,budget):
 p,log,record=item
 try:code=p.wait(timeout=max(.1,budget-(time.time()-record['start_unix'])))
 except subprocess.TimeoutExpired:
  os.killpg(p.pid,signal.SIGTERM)
  try:code=p.wait(timeout=60)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);code=p.wait()
  record['timed_out']=True
 log.close();record['exit_code']=code;record['seconds']=time.time()-record['start_unix']
 (root/'handles.json').write_text(json.dumps(dict(controller=os.getpid(),jobs=history),indent=2)+'\n')
 return code
try:
 for mode in ['prepare','preflight']:
  jobs=[launch(mode,a) for a in ['weak','strong']];codes=[finish(j,1800) for j in jobs]
  assert codes==[0,0],(mode,codes)
 locks={a:json.loads((root/a/'lock.json').read_text()) for a in ['weak','strong']}
 reports={a:json.loads((root/a/'preflight/report.json').read_text()) for a in locks}
 for a in locks:assert reports[a]['lock_sha256']==digest(root/a/'lock.json')
 release=validate_rocm_pair(locks,reports);release.update(locks={a:digest(root/a/'lock.json') for a in locks},preflights={a:digest(root/a/'preflight/report.json') for a in locks})
 (root/'pair_release.json').write_text(json.dumps(release,indent=2)+'\n')
 jobs=[launch('train',a) for a in ['weak','strong']];codes=[finish(j,14400) for j in jobs]
 result=dict(complete=codes==[0,0],jobs=history,seconds=time.monotonic()-start,scope='execution only; scientific terminal audit and evaluation remain required')
except Exception:result=dict(complete=False,jobs=history,seconds=time.monotonic()-start,error=traceback.format_exc())
(root/'execution.json').write_text(json.dumps(result,indent=2)+'\n')
