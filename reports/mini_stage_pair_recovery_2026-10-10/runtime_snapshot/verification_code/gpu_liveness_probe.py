import time
t=time.monotonic()
print('BEGIN',flush=True)
import torch
print('IMPORTED',time.monotonic()-t,flush=True)
x=torch.ones(16,device='cuda')
print('ALLOCATED',time.monotonic()-t,flush=True)
y=(x+1).sum()
torch.cuda.synchronize()
print('COMPLETE',float(y),time.monotonic()-t,flush=True)
