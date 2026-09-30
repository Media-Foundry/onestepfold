#!/usr/bin/env python3
"""Controlled raw S1/S2/S5 attribution with strict archived S1 parity."""
import argparse
import copy
import hashlib
import importlib
import inspect
import json
import os
from pathlib import Path
import time
import traceback

import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256, write_json


def prepare_step_reference(root, previous):
    assert not (root/'lock.json').exists()
    runtime=json.loads((previous/'runtime_lock.json').read_text())
    accepted=json.loads((previous/'raw_acceptance.json').read_text())
    assert accepted['complete'] and accepted['runtime_lock_sha256']==sha256(previous/'runtime_lock.json')
    for path,digest in {**runtime['source_hashes'],**runtime['input_hashes'],**runtime['weights_sha256']}.items():
        assert sha256(Path(path))==digest
    source=Path(runtime['source']);selection=json.loads((source/'selection.json').read_text())
    rows=[next(r for r in selection if r['pdb_id']==name) for name in ['2b0a','2z0j']]
    inputs={str(source/'selection.json'):sha256(source/'selection.json'),
        str(previous/'runtime_lock.json'):sha256(previous/'runtime_lock.json'),
        str(previous/'raw_acceptance.json'):sha256(previous/'raw_acceptance.json')}
    for row in rows:
        packet=source/'chemistry'/row['group_id']
        for p in packet.iterdir():
            if p.is_file():inputs[str(p)]=sha256(p)
        for seed in [400009,400031]:
            file=source/'data'/row['group_id']/f'native_{seed}.npy'
            entry=next(e for e in accepted['predictions'] if e['group_id']==row['group_id'] and e['seed']==seed)
            assert sha256(file)==entry['sha256'];inputs[str(file)]=entry['sha256']
    hashes={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.md']}
    bands=root/'code/docs/connection_reference_bands.json'
    hashes[str(bands)]=sha256(bands)
    for module in ['protenix','esm','runner','configs']:
        folder=Path(inspect.getfile(importlib.import_module(module))).parent
        hashes.update({str(p):sha256(p) for p in folder.rglob('*.py')})
    for name in ['differentiable_mini.py','soft_sequence_chart.py','soft_esm.py']:
        assert sha256(root/'code/src/fastglycan/models'/name)==sha256(previous/'code/src/fastglycan/models'/name)
    write_json(root/'lock.json',dict(source=str(source),rows=rows,seeds=[400009,400031],steps=[1,2,5],
        hashes=hashes,input_hashes=inputs,weights_sha256=runtime['weights_sha256'],
        weight_stats=runtime['weight_stats'],previous=str(previous),planned=12,
        cycles=4,dtype='fp32',workers=2,timeout=5400,scope='selected failure/control; raw forward only; no prevalence claim'))
    print('Locked2 proteins x2 noises x3 schedules',flush=True)


def run_step_reference(root,index):
    from fastglycan import stage0_confirm_runtime as rt
    from fastglycan.models.soft_sequence_chart import device_tree
    from fastglycan.models.differentiable_mini import full_recycle_pairformer, diffusion_from_conditioning, prepare_atom_pairs
    from fastglycan.hybrid_proposals import identity_noise
    lock=json.loads((root/'lock.json').read_text());row=lock['rows'][index];source=Path(lock['source'])
    folder=root/'cases'/row['pdb_id'];folder.mkdir(parents=True,exist_ok=False)
    report=dict(complete=False,index=index,pdb_id=row['pdb_id'],group_id=row['group_id'],results=[],lock_sha256=sha256(root/'lock.json'))
    start=time.monotonic()
    try:
        for path,digest in {**lock['hashes'],**lock['input_hashes']}.items():assert sha256(Path(path))==digest
        for path,stat in lock['weight_stats'].items():assert [Path(path).stat().st_size,Path(path).stat().st_mtime_ns]==stat
        torch.set_num_threads(1)
        runner=rt.runner_setup(folder/'work');runner.configs.dtype='fp32'
        assert Path(runner.configs.load_checkpoint_dir).resolve()==(root.parent/'protenix_stage0_pkg/v1_1/runtime/checkpoint').resolve()
        model=runner.model.eval().requires_grad_(False)
        assert all(p.dtype==torch.float32 for p in model.parameters() if p.is_floating_point())
        assert all(not m.training for m in model.modules())
        torch.serialization.add_safe_globals([argparse.Namespace])
        from protenix.data.esm.compute_esm import load_esm_model
        esm,alphabet=load_esm_model('esm2-3b',local_esm_dir=runner.configs.load_checkpoint_dir)
        esm.eval().requires_grad_(False)
        native=torch.load(source/'chemistry'/row['group_id']/'native.pt',map_location='cpu',weights_only=False)
        atoms=native['atoms'];base=device_tree(native['features'],'cuda')
        counts=dict(pairformer=0,diffusion=0)
        ph=model.pairformer_stack.register_forward_hook(lambda *unused:counts.__setitem__('pairformer',counts['pairformer']+1))
        dh=model.diffusion_module.register_forward_hook(lambda *unused:counts.__setitem__('diffusion',counts['diffusion']+1))
        report.update(resolved_config=runner.configs.to_dict(),device=torch.cuda.get_device_name(0),
            gt_in_model=False,model=rt.MODEL,effective=dict(cycles=4,dtype='fp32',autocast=False,
                gamma0=0,noise_scale_lambda=1,step_scale_eta=1,mc_dropout=False,augmentation='identity',stable_euler=True))
        with torch.no_grad():
            tokens=alphabet.get_batch_converter()([('sequence',row['sequence'])])[2].cuda()
            base['esm_token_embedding']=esm(tokens,repr_layers=[esm.num_layers],return_contacts=False)['representations'][esm.num_layers][0,1:-1]
            del esm,tokens;torch.cuda.empty_cache()
            features=prepare_atom_pairs(model.relative_position_encoding.generate_relp(copy.deepcopy(base)))
            point=full_recycle_pairformer(model,features,N_cycle=4,inplace_safe=False,mc_dropout=False)
            shapes=[x.shape for x in point];sizes=[x.numel() for x in point]
            conditioning=tuple(x.reshape(s) for x,s in zip(torch.cat([x.flatten() for x in point]).split(sizes),shapes))
            del point;assert counts['pairformer']==4
            ch=[hashlib.sha256(x.cpu().numpy().tobytes()).hexdigest() for x in conditioning]
            report['conditioning_hashes']=ch;report['load_conditioning_seconds']=time.monotonic()-start
            for seed in lock['seeds']:
                noise=identity_noise(atoms,seed,device='cuda');original=noise.clone()
                nf=folder/f'noise_{seed}.npy';np.save(nf,noise.cpu().numpy())
                for steps in lock['steps']:
                    cpu_rng=torch.get_rng_state().clone();gpu_rng=torch.cuda.get_rng_state().clone()
                    before=counts['diffusion'];begin=time.monotonic()
                    x=diffusion_from_conditioning(model,features,noise.clone(),conditioning,steps=steps)
                    torch.cuda.synchronize();seconds=time.monotonic()-begin
                    assert counts['diffusion']-before==steps and torch.isfinite(x).all()
                    assert torch.equal(cpu_rng,torch.get_rng_state()) and torch.equal(gpu_rng,torch.cuda.get_rng_state())
                    assert torch.equal(noise,original)
                    assert [hashlib.sha256(v.cpu().numpy().tobytes()).hexdigest() for v in conditioning]==ch
                    array=x.cpu().numpy().reshape(-1,3);assert array.dtype==np.float32
                    if steps==1:
                        previous=source/'data'/row['group_id']/f'native_{seed}.npy'
                        assert np.array_equal(array,np.load(previous)), 'archived S1 parity failed'
                    file=folder/f's{steps}_seed{seed}.npy';np.save(file,array)
                    schedule=model.inference_noise_scheduler(N_step=steps,device='cuda',dtype=torch.float32).cpu().tolist()
                    assert len(schedule)==steps+1 and schedule[0]==2560. and schedule[-1]==0.
                    report['results'].append(dict(seed=seed,steps=steps,file=str(file),sha256=sha256(file),
                        noise_sha256=sha256(nf),seconds=seconds,schedule=schedule,nfe=steps,
                        rng_unchanged=True,conditioning_unchanged=True,archived_s1_exact=steps==1))
                    write_json(folder/'report.json',report)
            assert counts==dict(pairformer=4,diffusion=16)
            ph.remove();dh.remove()
        np.savez_compressed(folder/'identity.npz',atom_names=atoms.atom_name,residue_ids=atoms.res_id,chain_ids=atoms.chain_id)
        report.update(complete=True,counts=counts,identity_sha256=sha256(folder/'identity.npz'),peak_allocated_bytes=torch.cuda.max_memory_allocated())
    except Exception:
        report['error']=traceback.format_exc()
    finally:
        report['seconds']=time.monotonic()-start;write_json(folder/'report.json',report)
    if not report['complete']:raise RuntimeError(report.get('error','incomplete'))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--previous',type=Path);parser.add_argument('--index',type=int)
    parser.add_argument('--mode',choices=['prepare','case'],required=True);args=parser.parse_args()
    assert Path(os.environ['PROTENIX_ROOT_DIR']).resolve()==(args.root.parent/'protenix_stage0_pkg/v1_1/runtime').resolve()
    if args.mode=='prepare':prepare_step_reference(args.root,args.previous)
    else:run_step_reference(args.root,args.index)
