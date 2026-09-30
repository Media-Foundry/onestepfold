#!/usr/bin/env python3
"""Frozen native conditioning and TRAIN-only references for the locked pilot."""
import argparse
import copy
import json
import os
from pathlib import Path
import shutil
import time
import traceback

import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256, write_json


def prepare_adapter_cache(root):
    assert not (root/'lock.json').exists()
    base=root.parent;source=base/'diffusion_training_sources_v1_20260930'
    source_lock=json.loads((source/'selection_lock.json').read_text());audit=json.loads((source/'audit.json').read_text())
    assert source_lock['complete'] and audit['verified_sources'] and audit['selection_complete']
    assert audit['selection_lock_sha256']==sha256(source/'selection_lock.json')
    assert sha256(source/'selection.json')==source_lock['selection_sha256']
    assert sha256(source/'data_manifest.json')==source_lock['data_manifest_sha256']
    rows=json.loads((source/'selection.json').read_text());assert len(rows)==160
    inputs={str(source/f):sha256(source/f) for f in ['selection_lock.json','selection.json','audit.json','data_manifest.json']}
    manifest=json.loads((source/'data_manifest.json').read_text())
    for row in rows:
        for folder in ['chemistry','data/examples']:
            for file in (source/folder/row['group_id']).iterdir():
                if file.is_file():
                    assert sha256(file)==manifest[str(file.relative_to(source))];inputs[str(file)]=sha256(file)
    previous=base/'failure_step_reference_v1_20260930/lock.json'
    model_lock=json.loads(previous.read_text())
    for path,digest in {**model_lock['weights_sha256'],**model_lock['hashes']}.items():assert sha256(Path(path))==digest
    assert shutil.disk_usage(root).free>80*1024**3,'insufficient cache disk reserve'
    hashes={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.md']}
    for file in ['differentiable_mini.py','soft_sequence_chart.py','soft_esm.py']:
        assert sha256(root/'code/src/fastglycan/models'/file)==sha256(base/'failure_step_reference_v1_20260930/code/src/fastglycan/models'/file)
    assignments=[[] for _ in range(8)];loads=[0]*8
    for row in sorted(rows,key=lambda r:(-len(r['sequence']),r['group_id'])):
        i=min(range(8),key=lambda j:(loads[j],j));assignments[i].append(row);loads[i]+=len(row['sequence'])**2
    write_json(root/'lock.json',dict(source=str(source),rows=rows,assignments=assignments,estimated_loads=loads,
        input_hashes=inputs,hashes=hashes,weights_sha256=model_lock['weights_sha256'],
        weight_stats=model_lock['weight_stats'],model_runtime_lock=str(previous),model_runtime_lock_sha256=sha256(previous),
        train_seeds=[600001,600011],validation_seeds=[600029,600043],dtype='fp32',cycles=4,
        validation_predictions=False,training_started=False,workers=8,planned_conditioning=160,planned_train_outputs=512))
    print('locked160conditioning,512TRAIN reference outputs; no validation outputs',flush=True)


def run_adapter_cache(root,index):
    from fastglycan import stage0_confirm_runtime as rt
    from fastglycan.models.soft_sequence_chart import device_tree
    from fastglycan.models.differentiable_mini import full_recycle_pairformer, diffusion_from_conditioning, prepare_atom_pairs
    from fastglycan.hybrid_proposals import identity_noise
    from fastglycan.adapter_supervision import build_adapter_supervision
    lock=json.loads((root/'lock.json').read_text());source=Path(lock['source']);rows=lock['assignments'][index]
    folder=root/f'worker_{index}';folder.mkdir(exist_ok=False);start=time.monotonic()
    report=dict(complete=False,index=index,rows=[],lock_sha256=sha256(root/'lock.json'))
    try:
        for path,digest in lock['hashes'].items():assert sha256(Path(path))==digest
        for path,stat in lock['weight_stats'].items():assert [Path(path).stat().st_size,Path(path).stat().st_mtime_ns]==stat
        torch.set_num_threads(1);runner=rt.runner_setup(folder/'work');runner.configs.dtype='fp32'
        assert Path(runner.configs.load_checkpoint_dir).resolve()==(root.parent/'protenix_stage0_pkg/v1_1/runtime/checkpoint').resolve()
        model=runner.model.eval().requires_grad_(False)
        assert all(p.dtype==torch.float32 for p in model.parameters() if p.is_floating_point())
        torch.serialization.add_safe_globals([argparse.Namespace])
        from protenix.data.esm.compute_esm import load_esm_model
        esm,alphabet=load_esm_model('esm2-3b',local_esm_dir=runner.configs.load_checkpoint_dir)
        esm.eval().requires_grad_(False)
        counts=dict(pairformer=0,diffusion=0)
        ph=model.pairformer_stack.register_forward_hook(lambda *unused:counts.__setitem__('pairformer',counts['pairformer']+1))
        dh=model.diffusion_module.register_forward_hook(lambda *unused:counts.__setitem__('diffusion',counts['diffusion']+1))
        report['resolved_config']=runner.configs.to_dict();report['device']=torch.cuda.get_device_name(0)
        with torch.no_grad():
            for row in rows:
                g=row['group_id'];target=root/'examples'/g;target.mkdir(parents=True,exist_ok=False);begin=time.monotonic()
                packet=source/'chemistry'/g
                for name in ['native.pt','mapping.npz']:
                    path=packet/name;assert sha256(path)==lock['input_hashes'][str(path)]
                native=torch.load(packet/'native.pt',map_location='cpu',weights_only=False);atoms=native['atoms']
                features=device_tree(native['features'],'cuda')
                tokens=alphabet.get_batch_converter()([('sequence',row['sequence'])])[2].cuda()
                features['esm_token_embedding']=esm(tokens,repr_layers=[esm.num_layers],return_contacts=False)['representations'][esm.num_layers][0,1:-1]
                features=prepare_atom_pairs(model.relative_position_encoding.generate_relp(copy.deepcopy(features)))
                pf_before=counts['pairformer'];diff_before=counts['diffusion']
                point=full_recycle_pairformer(model,features,N_cycle=4,inplace_safe=False,mc_dropout=False)
                shapes=[tuple(x.shape) for x in point];sizes=[x.numel() for x in point]
                flat=torch.cat([x.flatten() for x in point]);conditioning=tuple(x.reshape(s) for x,s in zip(flat.split(sizes),shapes))
                assert flat.dtype==torch.float32 and torch.isfinite(flat).all()
                cached=dict(schema='native_diffusion_pilot_cache_v1',group_id=g,role=row['role'],
                    conditioning_flat=flat.cpu(),shapes=shapes,sizes=sizes,features=device_tree(features,'cpu'),
                    native_sha256=sha256(packet/'native.pt'),lock_sha256=sha256(root/'lock.json'))
                torch.save(cached,target/'conditioning.pt')
                outputs=[]
                if row['role']=='train':
                    for seed in lock['train_seeds']:
                        noise=identity_noise(atoms,seed,device='cuda')
                        for steps in [1,2]:
                            cpu_rng=torch.get_rng_state().clone();gpu_rng=torch.cuda.get_rng_state().clone()
                            coordinate=diffusion_from_conditioning(model,features,noise.clone(),conditioning,steps=steps).reshape(-1,3)
                            assert torch.isfinite(coordinate).all()
                            assert torch.equal(cpu_rng,torch.get_rng_state()) and torch.equal(gpu_rng,torch.cuda.get_rng_state())
                            file=target/f's{steps}_seed{seed}.npy';np.save(file,coordinate.cpu().numpy())
                            outputs.append(dict(seed=seed,steps=steps,sha256=sha256(file),name=file.name,
                                schedule=model.inference_noise_scheduler(N_step=steps,device='cuda',dtype=torch.float32).cpu().tolist()))
                    loaded=torch.load(target/'conditioning.pt',map_location='cpu',weights_only=False)
                    restored=loaded['conditioning_flat'].cuda();restored_features=device_tree(loaded['features'],'cuda')
                    restored_conditioning=tuple(x.reshape(s) for x,s in zip(restored.split(loaded['sizes']),loaded['shapes']))
                    replay=diffusion_from_conditioning(model,restored_features,identity_noise(atoms,lock['train_seeds'][0],device='cuda'),restored_conditioning,steps=1).reshape(-1,3)
                    assert np.array_equal(replay.cpu().numpy(),np.load(target/f's1_seed{lock["train_seeds"][0]}.npy')),'cache reload changed S1'
                    mapping=dict(np.load(packet/'mapping.npz'))
                    supervision=build_adapter_supervision(mapping,atoms.bonds.as_array(),row['sequence'])
                    torch.save(supervision,target/'gt_supervision.pt')
                    del loaded,restored,restored_features,restored_conditioning,replay,mapping,supervision,noise,coordinate
                assert counts['pairformer']-pf_before==4
                assert counts['diffusion']-diff_before==(7 if row['role']=='train' else 0)
                result=dict(group_id=g,role=row['role'],length=len(row['sequence']),seconds=time.monotonic()-begin,
                    outputs=outputs,reload_replay=row['role']=='train',counts=dict(pairformer=4,diffusion=counts['diffusion']-diff_before),
                    files={p.name:sha256(p) for p in target.iterdir() if p.is_file()})
                write_json(target/'report.json',result);report['rows'].append(result);write_json(folder/'report.json',report)
                del native,features,tokens,point,flat,conditioning,cached,atoms
                torch.cuda.empty_cache()
        assert counts==dict(pairformer=4*len(rows),diffusion=7*sum(r['role']=='train' for r in rows))
        ph.remove();dh.remove()
        report.update(complete=True,counts=counts,peak_gpu_bytes=torch.cuda.max_memory_allocated(),torch_version=torch.__version__)
    except Exception:report['error']=traceback.format_exc()
    finally:report['seconds']=time.monotonic()-start;write_json(folder/'report.json',report)
    if not report['complete']:raise RuntimeError(report.get('error','incomplete'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--index',type=int)
    p.add_argument('--mode',choices=['prepare','worker'],required=True);a=p.parse_args()
    assert Path(os.environ['PROTENIX_ROOT_DIR']).resolve()==(a.root.parent/'protenix_stage0_pkg/v1_1/runtime').resolve()
    assert os.environ.get('LAYERNORM_TYPE')=='torch'
    if a.mode=='prepare':prepare_adapter_cache(a.root)
    else:run_adapter_cache(a.root,a.index)
