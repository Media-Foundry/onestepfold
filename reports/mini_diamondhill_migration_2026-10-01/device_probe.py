import os,sys,json,time,subprocess
from pathlib import Path
root=Path(__file__).parent
if len(sys.argv)>1:
 import torch
 torch.set_num_threads(1)
 start=time.monotonic();torch.cuda.set_device(0)
 a=torch.ones((2048,2048),device='cuda',dtype=torch.float32)
 b=a@a
 assert torch.equal(b,torch.full_like(b,2048.))
 for _ in range(3):assert torch.equal(a@a,b)
 x=torch.linspace(-1,1,1048576,device='cuda',dtype=torch.float32).requires_grad_()
 loss=x.square().sum();g,=torch.autograd.grad(loss,x)
 assert torch.equal(g,2*x.detach()) and torch.isfinite(g).all()
 torch.cuda.synchronize()
 report=dict(complete=True,gcd=int(sys.argv[1]),torch=torch.__version__,hip=torch.version.hip,device=torch.cuda.get_device_name(0),seconds=time.monotonic()-start,peak_bytes=torch.cuda.max_memory_allocated(),scope='bounded arithmetic/repeatability/autograd smoke only; not a full hardware health certification')
 (root/f'gcd_{sys.argv[1]}.json').write_text(json.dumps(report,indent=2)+'\n')
else:
 ps=[]
 for i in range(8):
  env=dict(os.environ,ROCR_VISIBLE_DEVICES=str(i),OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
  log=(root/f'gcd_{i}.log').open('w');p=subprocess.Popen([sys.executable,__file__,str(i)],env=env,stdout=log,stderr=subprocess.STDOUT);ps.append((i,p,log))
 (root/'device_probe_pids.json').write_text(json.dumps({i:p.pid for i,p,_ in ps}))
 results=[]
 for i,p,log in ps:results.append(dict(gcd=i,pid=p.pid,exit_code=p.wait()));log.close()
 (root/'device_probe_execution.json').write_text(json.dumps(dict(complete=all(r['exit_code']==0 for r in results),workers=results),indent=2)+'\n')
