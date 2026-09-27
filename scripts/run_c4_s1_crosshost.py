#!/usr/bin/env python3
"""ROCm/CUDA controlled prediction comparison with shared saved random inputs."""
import argparse,importlib,inspect,json,platform,time
from pathlib import Path
import numpy as np
import torch
from run_c4_s1_precision import ReplayNoise,tensor_dtypes
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.teacher_pairing import feature_digest
from fastglycan.paired_teacher_protocol import sha256,write_json
SETTINGS=('c4_s1','c4_s2','c4_s5')

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--worker',type=int,default=0);p.add_argument('--preflight',action='store_true');a=p.parse_args();root=a.root.resolve();l=rt.load_json(root/'lock.json');info=rt.load_json(root/'packets.json');original=rt.load_json(root/'environment_hpc3.json')
 code=Path(__file__).resolve().parents[1]
 for name,digest in rt.load_json(root/'cross_source_manifest.json')['files'].items():assert sha256(code/name)==digest,name
 groups=l['panel_b'][a.worker%2::2];seed=l['seeds'][a.worker//2]
 if a.preflight:
  order=sorted(l['panel_b'],key=lambda g:(info[g]['length'],g));groups=[order[0],order[-1]];seed=103
 else:assert rt.load_json(root/'preflight/complete.json')['complete']
 folder=root/('preflight' if a.preflight else f'worker_{a.worker}');folder.mkdir(exist_ok=False)
 runner=rt.runner_setup(folder/'work');assert torch.version.hip is not None and 'MI250' in torch.cuda.get_device_name()
 assert {p.dtype for p in runner.model.parameters()}=={torch.float32};runner.model.requires_grad_(False)
 checkpoint=Path(runner.configs.load_checkpoint_dir)/'protenix_mini_esm_v0.5.0.pt';assert sha256(checkpoint)==original['checkpoint_sha256']
 hashes={}
 for name,digest in original['runtime_source_sha256'].items():
  hashes[name]=sha256(Path(inspect.getfile(importlib.import_module(name))))
  assert hashes[name]==digest,(name,'runtime source mismatch')
 env=dict(torch=torch.__version__,hip=torch.version.hip,python=platform.python_version(),gpu=torch.cuda.get_device_name(),matmul_tf32=torch.backends.cuda.matmul.allow_tf32,cudnn_tf32=torch.backends.cudnn.allow_tf32,config=runner.configs.to_dict(),runtime_source_sha256=hashes,checkpoint_sha256=sha256(checkpoint),parameter_dtype='float32')
 write_json(folder/'environment.json',env)
 dtypes={}
 for name,mod in [('pairformer',runner.model.pairformer_stack),('diffusion',runner.model.diffusion_module)]:
  def before(module,args,kwargs,name=name):dtypes.setdefault(name,[]).append(dict(enabled=torch.is_autocast_enabled('cuda'),target=str(torch.get_autocast_dtype('cuda')),inputs=sorted(set(tensor_dtypes((args,kwargs))))))
  def after(module,args,output,name=name):dtypes[name][-1]['outputs']=sorted(set(tensor_dtypes(output)))
  mod.register_forward_pre_hook(before,with_kwargs=True);mod.register_forward_hook(after)
 result=dict(complete=False,worker=a.worker,seed=seed,records=[],host='DiamondHill',preflight=a.preflight);start=time.monotonic()
 for i,g in enumerate(groups):
  packet=rt.verify_packet(root/'packets'/f'{g}.pt',info[g]);w=l['seeds'].index(seed)*2+l['panel_b'].index(g)%2;rf=root/f'b_{w}';refdone=rt.load_json(rf/'complete.json');assert sha256(rf/'progress.json')==refdone['progress_sha256']
  refs={r['setting']:r for r in rt.load_json(rf/'progress.json')['records'] if r['group_id']==g and r['condition']=='controlled'}
  for precision in ('bf16','fp32'):
   runner.configs.dtype=precision;assert runner.model.configs.dtype==precision;conditioning=[]
   for s in SETTINGS:
    ref=refs[s];path=rf/ref['random_inputs']['path'];assert sha256(path)==ref['random_inputs']['sha256']
    with np.load(path) as f:arrays=dict(f)
    dtypes.clear()
    with ReplayNoise(runner,g,seed,arrays) as control:
     with rt.Trace(runner.model) as trace:pred,x,r=rt.predict(runner,packet['data'],s,seed,trace)
    for k in ('initial_coordinate','first_noisy'):assert np.array_equal(arrays[k],control.arrays[k]),(g,precision,s,k)
    assert not r['mc_dropout_applied'];conditioning.append(control.record['conditioning_sha256'])
    assert len(dtypes['pairformer'])==4 and len(dtypes['diffusion'])==rt.SETTINGS[s][1]
    if precision=='fp32':
     assert all(not row['enabled'] or row['target']=='torch.float32' for v in dtypes.values() for row in v)
     assert all('torch.bfloat16' not in row['inputs'] and 'torch.float16' not in row['inputs'] and set(row['outputs'])<={'torch.float32'} for v in dtypes.values() for row in v)
    r['dtype_trace']=json.loads(json.dumps(dtypes));r['common_noise']=control.record
    if a.preflight or (i==0 and s=='c4_s1'):
     with ReplayNoise(runner,g,seed,arrays):again,y,_=rt.predict(runner,packet['data'],s,seed,None)
     assert np.array_equal(x,y),(g,precision,s,'same-host replay');del again;r['same_host_exact_replay']=True
    artifact=rt.save_prediction(folder/precision,s,seed,g,pred,packet);artifact['cif']=str(Path(precision)/artifact['cif'])
    r.update(group_id=g,precision=precision,artifact=artifact,feature_sha256=feature_digest(packet['data']['input_feature_dict']),hpc_bf16_coordinate_sha256=ref['coordinate_sha256']);result['records'].append(r);del pred
   assert len(set(conditioning))==1,(g,precision,'conditioning changed across S')
  result['elapsed_seconds']=time.monotonic()-start;write_json(folder/'progress.json',result);print(a.worker,i+1,len(groups),flush=True)
 result['complete']=True;write_json(folder/'progress.json',result);write_json(folder/'complete.json',dict(complete=True,progress_sha256=sha256(folder/'progress.json')))
if __name__=='__main__':main()
