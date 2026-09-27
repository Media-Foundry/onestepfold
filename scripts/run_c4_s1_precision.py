#!/usr/bin/env python3
"""CLI-fp32 versus frozen BF16 controlled-noise predictions, same weights/inputs."""
import argparse,json,time
from pathlib import Path
import numpy as np
import torch
from run_c4_s1_attribution import CommonNoise,SETTINGS
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.teacher_pairing import feature_digest
from fastglycan.paired_teacher_protocol import sha256,write_json

class ReplayNoise(CommonNoise):
    def __init__(self,runner,g,seed,arrays):super().__init__(runner,g,seed);self.expected=arrays
    def __enter__(self):
        super().__enter__();base=self.generator.centre_random_augmentation
        def augment(x_input_coords,N_sample=1,**kwargs):
            if 'initial_coordinate' not in self.arrays:
                x_input_coords=torch.as_tensor(self.expected['initial_coordinate'],device=x_input_coords.device,dtype=x_input_coords.dtype)
                base(x_input_coords,N_sample=N_sample,**kwargs)  # record the same raw random input
                # Pin the actual post-centering denoiser input too, avoiding a
                # precision-dependent centering difference in the noise itself.
                return torch.as_tensor(self.expected['first_noisy'],device=x_input_coords.device,dtype=x_input_coords.dtype).unsqueeze(-3)
            return base(x_input_coords,N_sample=N_sample,**kwargs)
        self.generator.centre_random_augmentation=augment
        return self

def tensor_dtypes(value):
    if isinstance(value,torch.Tensor):return [str(value.dtype)]
    if isinstance(value,dict):return sum([tensor_dtypes(v) for v in value.values()],[])
    if isinstance(value,(tuple,list)):return sum([tensor_dtypes(v) for v in value],[])
    return []

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--worker',type=int,required=True);a=p.parse_args();root=a.root.resolve()
    lock=rt.load_json(root/'lock.json');plock=rt.load_json(root/'precision_lock.json');source=Path(__file__).resolve().parents[1]
    assert sha256(root/'lock.json')==plock['parent_lock_sha256']
    for rel,digest in rt.load_json(root/'precision_source_manifest.json')['files'].items():assert sha256(source/rel)==digest,rel
    seed=lock['seeds'][a.worker//2];groups=lock['panel_b'][a.worker%2::2]
    reference_folder=root/f'b_{a.worker}';complete=rt.load_json(reference_folder/'complete.json');assert complete['complete'] and sha256(reference_folder/'progress.json')==complete['progress_sha256']
    refs={(r['group_id'],r['setting']):r for r in rt.load_json(reference_folder/'progress.json')['records'] if r['condition']=='controlled'}
    old=Path(lock['old_root']);prep=rt.load_json(old/'repeat/preparation.json');new=rt.load_json(root/'prepare_b/preparation.json')
    folder=root/f'precision_{a.worker}';folder.mkdir(exist_ok=False);runner=rt.runner_setup(folder/'work');runner.configs.dtype='fp32'
    assert runner.model.configs.dtype=='fp32'
    assert {p.dtype for p in runner.model.parameters()}=={torch.float32}
    env=rt.environment(runner)
    for k in ('checkpoint_sha256','esm_checkpoint_sha256','runtime_source_sha256'):assert env[k]==prep['environment'][k]
    for k in ('matmul_tf32','cudnn_tf32','deterministic_algorithms','torch','cuda'):assert env['runtime'][k]==prep['environment']['runtime'][k],k
    assert 'H100' in env['runtime']['gpu'];write_json(folder/'environment.json',env)
    dtypes={};handles=[]
    for name,mod in [('pairformer',runner.model.pairformer_stack),('diffusion',runner.model.diffusion_module)]:
        def hook(module,args,kwargs,name=name):
            dtypes.setdefault(name,[]).append(dict(autocast_enabled=torch.is_autocast_enabled('cuda'),dtypes=sorted(set(tensor_dtypes((args,kwargs))))))
        handles.append(mod.register_forward_pre_hook(hook,with_kwargs=True))
    result=dict(complete=False,seed=seed,worker=a.worker,precision='fp32_cli',records=[],precision_lock_sha256=sha256(root/'precision_lock.json'));start=time.monotonic()
    for index,g in enumerate(groups):
        if g in prep['packets']:pack=rt.verify_packet(old/'repeat/packets'/f'{g}.pt',prep['packets'][g])
        else:pack=rt.verify_packet(root/'prepare_b/packets'/f'{g}.pt',new['packets'][g])
        hashes=[]
        for s in SETTINGS:
            ref=refs[(g,s)];path=reference_folder/ref['random_inputs']['path'];assert sha256(path)==ref['random_inputs']['sha256']
            with np.load(path) as f:arrays=dict(f)
            dtypes.clear()
            with ReplayNoise(runner,g,seed,arrays) as control:
                with rt.Trace(runner.model) as trace:pred,x,r=rt.predict(runner,pack['data'],s,seed,trace)
            for k in ('initial_coordinate','first_noisy'):assert np.array_equal(control.arrays[k],arrays[k]),(g,s,k,'noise mismatch')
            assert not r['mc_dropout_applied']
            assert len(dtypes['pairformer'])==4 and len(dtypes['diffusion'])==rt.SETTINGS[s][1]
            assert all(not x['autocast_enabled'] for v in dtypes.values() for x in v)
            assert all('torch.bfloat16' not in x['dtypes'] and 'torch.float16' not in x['dtypes'] for v in dtypes.values() for x in v)
            r['dtype_trace']=json.loads(json.dumps(dtypes));r['controlled']=control.record
            hashes.append(control.record['conditioning_sha256'])
            if index==0 and s=='c4_s1':
                with ReplayNoise(runner,g,seed,arrays):again,y,_=rt.predict(runner,pack['data'],s,seed,None)
                assert np.array_equal(x,y);del again;r['exact_replay']=True
            r.update(group_id=g,condition='fp32_controlled',feature_sha256=feature_digest(pack['data']['input_feature_dict']),artifact=rt.save_prediction(folder,s,seed,g,pred,pack),bf16_reference_sha256=ref['coordinate_sha256'])
            result['records'].append(r);del pred
        assert len(set(hashes))==1
        result['elapsed_seconds']=time.monotonic()-start;write_json(folder/'progress.json',result);print(a.worker,index+1,len(groups),flush=True)
    result['complete']=True;write_json(folder/'progress.json',result);write_json(folder/'complete.json',dict(complete=True,progress_sha256=sha256(folder/'progress.json')))
if __name__=='__main__':main()
