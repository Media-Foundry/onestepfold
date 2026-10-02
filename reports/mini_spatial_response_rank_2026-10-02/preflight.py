import torch,time,json,sys
sys.path.insert(0,'/tmp')
from spatial_response_rank import SpatialResponseBasis
from pathlib import Path
base=Path('/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/functional_response_rank_v1_20261002/worker_0')
w=torch.load(base/'p7_wt_conditioning.pt',weights_only=False,map_location='cpu')['conditioning'][2].cuda()
p=next(base.glob('p7_s40_*_conditioning.pt'));z=torch.load(p,weights_only=False,map_location='cpu')['conditioning'][2].cuda()
torch.set_num_threads(1);torch.cuda.synchronize();t=time.monotonic();b=SpatialResponseBasis(w,z);torch.cuda.synchronize();seconds=time.monotonic()-t
r=dict(complete=True,shape=list(z.shape),path=str(p),decomposition_seconds=seconds,full=[])
for v in ('channel','shared'):
 torch.cuda.synchronize();t=time.monotonic();x=b.reconstruct(v,'full');torch.cuda.synchronize();r['full'].append(dict(variant=v,error=float((x-z).abs().max()),seconds=time.monotonic()-t));assert float((x-z).abs().max())<1e-5
print(json.dumps(r));Path('/tmp/spatial_preflight.json').write_text(json.dumps(r,indent=2))
