#!/usr/bin/env python3
"""Bounded inference-only C4S1 persistence and common-noise attribution."""
import argparse,copy,gzip,hashlib,json,time
from pathlib import Path
import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.teacher_pairing import feature_digest
from fastglycan import stage0_confirm_runtime as rt

rt.SETTINGS['c4_s1']=(4,1)
SETTINGS=('c4_s1','c4_s2','c4_s5')

class CommonNoise:
    """Temporary identity-augmentation control; no installed source modifications."""
    def __init__(self,runner,group,replica):
        self.runner=runner;self.seed=int(hashlib.sha256(f'attribution-v1:{group}:{replica}'.encode()).hexdigest()[:8],16)%(2**31-1)
        self.record={};self.arrays={}
    def __enter__(self):
        from protenix.model import generator
        self.generator=generator;self.augment=generator.centre_random_augmentation
        self.sampler=self.runner.model.sample_diffusion
        self.dropout=self.runner.configs.mc_dropout_apply_rate;self.runner.configs.mc_dropout_apply_rate=0.0
        def augmentation(x_input_coords,N_sample=1,**kwargs):
            assert N_sample==1 and not kwargs
            if 'initial_coordinate' not in self.arrays:
                self.arrays['initial_coordinate']=x_input_coords.detach().float().cpu().numpy()
                self.record['initial_coordinate_sha256']=feature_digest(x_input_coords)
            return (x_input_coords-x_input_coords.mean(-2,keepdim=True)).unsqueeze(-3)
        def sampler(*args,**kwargs):
            rt.seed_prediction(self.seed)
            self.record['sampling_seed']=self.seed
            return self.sampler(*args,**kwargs)
        def denoiser(module,args,kwargs):
            if 'first_noisy' in self.arrays:return
            self.arrays['first_noisy']=kwargs['x_noisy'].detach().float().cpu().numpy()
            self.record['first_noisy_sha256']=feature_digest(kwargs['x_noisy'])
            self.record['conditioning_sha256']=feature_digest({k:kwargs[k] for k in ('s_inputs','s_trunk','z_trunk','pair_z','p_lm','c_l')})
        generator.centre_random_augmentation=augmentation
        self.runner.model.sample_diffusion=sampler
        self.hook=self.runner.model.diffusion_module.register_forward_pre_hook(denoiser,with_kwargs=True)
        return self
    def __exit__(self,*exc):
        self.hook.remove();self.generator.centre_random_augmentation=self.augment
        self.runner.model.sample_diffusion=self.sampler;self.runner.configs.mc_dropout_apply_rate=self.dropout


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--mode',choices=['preflight','prepare_b','a','b'],required=True);p.add_argument('--worker',type=int,default=0);a=p.parse_args()
    root=a.root.resolve();lock=rt.load_json(root/'lock.json');old=Path(lock['old_root']);prep=rt.load_json(old/'repeat/preparation.json')
    for rel,digest in lock['bound_old_files'].items():assert sha256(old/rel)==digest,rel
    for rel,digest in rt.load_json(root/'source_manifest.json')['files'].items():assert sha256(root/'code_v1'/rel)==digest,rel
    folder=root/(a.mode if a.mode in ('preflight','prepare_b') else f'{a.mode}_{a.worker}')
    folder.mkdir(exist_ok=False);runner=rt.runner_setup(folder/'work');env=rt.environment(runner)
    for k in ('checkpoint_sha256','esm_checkpoint_sha256','runtime_source_sha256'):assert env[k]==prep['environment'][k],k
    assert 'H100' in env['runtime']['gpu'],env['runtime']['gpu']
    for k in ('torch','cuda','matmul_tf32','cudnn_tf32','deterministic_algorithms'):
        assert env['runtime'][k]==prep['environment']['runtime'][k],(k,env['runtime'][k],prep['environment']['runtime'][k])
    write_json(folder/'environment.json',env)
    def packet(g):
        if g in prep['packets']:return rt.verify_packet(old/'repeat/packets'/f'{g}.pt',prep['packets'][g])
        info=rt.load_json(root/'prepare_b/preparation.json')['packets'][g]
        return rt.verify_packet(root/'prepare_b/packets'/f'{g}.pt',info)
    if a.mode=='preflight':
        refs={}
        for w in range(16):
            d=rt.load_json(old/'repeat'/f'worker_{w}/progress.json')
            for r in d['records']:refs[(r['group_id'],r['seed'],r['setting'])]=r
        groups=sorted(lock['panel_a'],key=lambda g:(prep['packets'][g]['length'],g));checks=[]
        for g in (groups[0],groups[-1]):
            pack=packet(g)
            for seed in lock['seeds']:
                for s in ('c4_s2','c4_s5'):
                    pred,coords,r=rt.predict(runner,pack['data'],s,seed,None)
                    assert r['coordinate_sha256']==refs[(g,seed,s)]['coordinate_sha256'],(g,seed,s,'historical replay')
                    checks.append(dict(group=g,seed=seed,setting=s,exact=True));del pred
                pred,x,_=rt.predict(runner,pack['data'],'c4_s1',seed,None);del pred
                with rt.Trace(runner.model) as trace:pred,y,r=rt.predict(runner,pack['data'],'c4_s1',seed,trace)
                assert np.array_equal(x,y) and r['noise_schedule']==[2560.,0.];del pred
                checks.append(dict(group=g,seed=seed,setting='c4_s1',exact=True,trace=r))
                write_json(folder/'progress.json',checks)
            common=[]
            for s in (*SETTINGS,'c4_s1'):
                with CommonNoise(runner,g,103) as control:
                    with rt.Trace(runner.model) as trace:pred,x,r=rt.predict(runner,pack['data'],s,103,trace)
                assert not r['mc_dropout_applied'];common.append(control.record|dict(setting=s,coordinate_sha256=r['coordinate_sha256']));del pred
            for k in ('initial_coordinate_sha256','first_noisy_sha256','conditioning_sha256'):
                assert len({x[k] for x in common})==1,(g,k)
            assert common[0]['coordinate_sha256']==common[-1]['coordinate_sha256']
            checks.append(dict(group=g,controlled_checks=common));write_json(folder/'progress.json',checks)
        write_json(folder/'complete.json',dict(complete=True,checks=checks,lock_sha256=sha256(root/'lock.json')));return
    assert rt.load_json(root/'preflight/complete.json')['complete']
    if a.mode=='prepare_b':
        rows=rt.load_json(root/'manifest.json');new=[g for g in lock['panel_b'] if g not in prep['packets']]
        path=folder/'input.json';write_json(path,[dict(name=g,sequences=[dict(proteinChain=dict(sequence=rows[g]['sequence'],count=1))]) for g in new])
        runner.configs.input_json_path=str(path);runner.configs.num_workers=0;rt.seed_prediction(101)
        from protenix.data.inference.infer_dataloader import get_inference_dataloader
        dataset=get_inference_dataloader(configs=runner.configs).dataset;(folder/'packets').mkdir()
        info=dict(complete=False,packets={})
        for i,g in enumerate(new):
            rt.seed_prediction(101);d,atoms,error=dataset[i];assert not error and d['sample_name']==g,error
            path=folder/'packets'/f'{g}.pt';torch.save(dict(data=d,atoms=atoms),path)
            info['packets'][g]=dict(packet_sha256=sha256(path),feature_sha256=feature_digest(d['input_feature_dict']),length=rows[g]['sequence_length'])
            write_json(folder/'preparation.json',info)
        info['complete']=True;write_json(folder/'preparation.json',info);return
    if a.mode=='a':
        seed=lock['seeds'][a.worker//4];groups=lock['panel_a'][a.worker%4::4]
    else:
        assert rt.load_json(root/'prepare_b/preparation.json')['complete']
        seed=lock['seeds'][a.worker//2];groups=lock['panel_b'][a.worker%2::2]
    result=dict(complete=False,mode=a.mode,worker=a.worker,seed=seed,records=[],lock_sha256=sha256(root/'lock.json'));start=time.monotonic()
    for g in groups:
        pack=packet(g)
        modes=['native'] if a.mode=='a' else (['controlled'] if g in lock['panel_a'] else ['native','controlled'])
        for mode in modes:
            common=[]
            for s in (('c4_s1',) if a.mode=='a' else SETTINGS):
                control=None
                if mode=='controlled':
                    with CommonNoise(runner,g,seed) as control:
                        with rt.Trace(runner.model) as trace:pred,x,r=rt.predict(runner,pack['data'],s,seed,trace)
                    assert not r['mc_dropout_applied'];r['controlled']=control.record;common.append(control.record)
                    saved=folder/f'{g}_{seed}_{s}_random_inputs.npz';np.savez_compressed(saved,**control.arrays);r['random_inputs']=dict(path=saved.name,sha256=sha256(saved))
                else:
                    with rt.Trace(runner.model) as trace:pred,x,r=rt.predict(runner,pack['data'],s,seed,trace)
                assert r['sampler_parameters']==dict(gamma0=0,gamma_min=1,noise_scale_lambda=1.003,step_scale_eta=1)
                artifact=rt.save_prediction(folder/mode,s,seed,g,pred,pack)
                artifact['cif']=str(Path(mode)/artifact['cif'])
                r.update(group_id=g,condition=mode,artifact=artifact,feature_sha256=feature_digest(pack['data']['input_feature_dict']))
                result['records'].append(r);del pred
            if mode=='controlled':
                for k in ('initial_coordinate_sha256','first_noisy_sha256','conditioning_sha256'):assert len({x[k] for x in common})==1,(g,k)
        result['elapsed_seconds']=time.monotonic()-start;write_json(folder/'progress.json',result)
        print(a.mode,a.worker,len(result['records']),g,flush=True)
    result['complete']=True;write_json(folder/'progress.json',result)
    write_json(folder/'complete.json',dict(complete=True,progress_sha256=sha256(folder/'progress.json')))
if __name__=='__main__':main()
