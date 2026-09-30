from pathlib import Path
import os,json,time,subprocess,traceback
r=Path(__file__).parent;start=time.monotonic()
(r/'preflight_handle.json').write_text(json.dumps(dict(pid=os.getpid(),started_unix=time.time()))+'\n')
root='/data/user/shuang886/Folding/folding_global_parameter_training_v1_20260930';base='/data/user/shuang886/Folding'
proot=str(r/'tools/proot/usr/bin/proot');python='/home/pc/anaconda3/envs/fold/bin/python'
commands=[]
try:
 while not (r/'verification.json').exists():
  if time.monotonic()-start>7500:raise TimeoutError('no verification result; no automatic restart')
  time.sleep(5)
 assert json.loads((r/'verification.json').read_text())['complete'], 'migration hash verification failed'
 mirror=Path('/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding')
 assert not (mirror/'folding_global_parameter_training_v1_20260930/lock.json').exists(), 'preserve existing run'
 env=dict(os.environ,ROCR_VISIBLE_DEVICES='0',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',LAYERNORM_TYPE='torch',PROTENIX_ROOT_DIR=base+'/protenix_stage0_pkg/v1_1/runtime',PYTHONPATH=root+'/code/src:'+root+'/code/scripts:'+root+'/code')
 for mode in ['prepare','preflight']:
  cmd=[proot,'-b',str(mirror)+':'+base,python,'-u',root+'/code/scripts/train_folding_global_parameter.py','--root',root,'--mode',mode,'--baseline',base+'/folding_global_distance_training_v1_20260930','--calibration',base+'/folding_parameter_budget_v1_20260930_retry1']
  with (r/f'model_{mode}.log').open('w') as log:
   p=subprocess.Popen(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
   commands.append(dict(mode=mode,pid=p.pid,command=cmd));(r/'model_preflight_commands.json').write_text(json.dumps(commands,indent=2)+'\n')
   code=p.wait(timeout=3600);commands[-1]['exit_code']=code
  assert code==0,(mode,code)
 result=dict(complete=True,commands=commands,training_started=False,scope='unchanged prepare/preflight checks on ROCm only; review hardware migration before training',seconds_including_wait=time.monotonic()-start)
except subprocess.TimeoutExpired:
 p.terminate();p.wait(timeout=60);result=dict(complete=False,commands=commands,error='preflight timed out; no restart',training_started=False)
except Exception:result=dict(complete=False,commands=commands,error=traceback.format_exc(),training_started=False)
(r/'model_preflight_execution.json').write_text(json.dumps(result,indent=2)+'\n')
