import hashlib,json,os,pathlib,subprocess,time,traceback
root=pathlib.Path("/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/noise_transfer_v1_20261001")
virtual="/data/user/shuang886/Folding/noise_transfer_v1_20261001"
proot="/media/IntelSSD/onestepfold/diamondhill_migration_20261001/tools/proot/usr/bin/proot"
python="/home/pc/anaconda3/envs/fold/bin/python"
prefix=[proot,"-b","/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding:/data/user/shuang886/Folding",python,"-u"]
lock_sha=hashlib.sha256((root/"lock.json").read_bytes()).hexdigest()
env=os.environ.copy();env.update(OMP_NUM_THREADS="1",OPENBLAS_NUM_THREADS="1",MKL_NUM_THREADS="1",LAYERNORM_TYPE="torch",PROTENIX_ROOT_DIR="/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime",PYTHONPATH=virtual+"/code/src:"+virtual+"/code/scripts:"+virtual+"/code")
assert not (root/"controller_execution.json").exists() and not (root/"handles.json").exists()
start=time.time();jobs=[];processes=[];output={"complete":False,"jobs":jobs,"lock_sha256":lock_sha,"controller_pid":os.getpid()}
try:
 for index in range(8):
  assert not (root/f"worker_{index}").exists()
  e=dict(env,HIP_VISIBLE_DEVICES=str(index),CUDA_VISIBLE_DEVICES=str(index))
  cmd=prefix+[virtual+"/code/scripts/evaluate_diffusion_learning.py","--root",virtual,"--mode","worker","--index",str(index)]
  log=open(root/f"worker_{index}.log","w");p=subprocess.Popen(cmd,env=e,stdout=log,stderr=subprocess.STDOUT);log.close()
  jobs.append(dict(index=index,pid=p.pid,command=cmd,start_unix=time.time(),gcd=index));processes.append(p)
 (root/"handles.json").write_text(json.dumps(output,indent=2)+"\n")
 for job,p in zip(jobs,processes):
  job["exit_code"]=p.wait(timeout=max(1,3600-(time.time()-start)));job["observed_seconds"]=time.time()-job["start_unix"]
 output["complete"]=all(j["exit_code"]==0 for j in jobs);output["seconds"]=time.time()-start
 (root/"inference_execution.json").write_text(json.dumps(output,indent=2)+"\n")
 assert output["complete"],"inference failure; no automatic retry or score release"
 output["postprocess"]=[]
 for mode in ["score"]:
  cmd=prefix+[virtual+"/code/scripts/probe_noise_transfer.py","--root",virtual,"--mode",mode]
  t=time.time()
  with open(root/f"{mode}.log","w") as log:p=subprocess.Popen(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
  entry=dict(mode=mode,pid=p.pid,command=cmd);output["postprocess"].append(entry)
  (root/"handles.json").write_text(json.dumps(output,indent=2)+"\n")
  entry.update(exit_code=p.wait(timeout=10800),seconds=time.time()-t)
  assert entry["exit_code"]==0,mode+" failed; artifacts retained"
 output["complete"]=True
except Exception:
 output["complete"]=False;output["error"]=traceback.format_exc()
 for p in processes:
  if p.poll() is None:p.terminate()
finally:
 output["seconds"]=time.time()-start
 (root/"controller_execution.json").write_text(json.dumps(output,indent=2)+"\n")
