#!/usr/bin/env python3
"""One isolated engineering update; no method quality or deployment acceptance."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import time
import traceback

import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256, write_json


def adapter_preflight(root):
    from fastglycan import stage0_confirm_runtime as rt
    from fastglycan.models.soft_sequence_chart import device_tree
    from fastglycan.models.differentiable_mini import full_recycle_pairformer, diffusion_from_conditioning, prepare_atom_pairs
    from fastglycan.models.diffusion_adapter import attach_diffusion_adapter, merge_diffusion_adapter
    from fastglycan.hybrid_proposals import identity_noise
    from fastglycan.hybrid_geometry import GeometryTopology
    from fastglycan.experimental_training import observed_aligned_mse
    from fastglycan.scaling_metrics import lddt_observed
    from fastglycan.sequence_isolation import read_hsps
    base=root.parent;source=base/'fresh_contact_source_v1_20260930'
    assert not (root/'lock.json').exists()
    selection_lock=json.loads((source/'selection_lock.json').read_text())
    for name,key in [('preflight.json','preflight_sha256'),('data_manifest.json','manifest_sha256'),('source_lock.json','source_lock_sha256'),('selection.json','selection_sha256')]:
        assert sha256(source/name)==selection_lock[key]
    source_lock=json.loads((source/'source_lock.json').read_text())
    for path,digest in source_lock['source_hashes'].items():assert sha256(Path(path))==digest
    previous=json.loads((base/'failure_step_reference_v1_20260930/lock.json').read_text())
    for path,digest in {**previous['hashes'],**previous['weights_sha256']}.items():assert sha256(Path(path))==digest
    chosen=json.loads((source/'selection.json').read_text());used={r['group_id'] for r in chosen}
    passed=[r for r in json.loads((source/'preflight.json').read_text()) if r['passed'] and r['group_id'] not in used]
    assert len(passed)==1 and passed[0]['pdb_id']=='1u07'
    row=next(r for r in json.loads((source/'candidates.json').read_text()) if r['group_id']==passed[0]['group_id'])
    edges={tuple(sorted((int(h.query[1:]),int(h.subject[1:])))) for h in read_hsps(base/'connection_calibration_extension_v1_20260930/pairs.tsv') if h.query!=h.subject and h.evidence()['excluded']}
    assert all(row['pdb_id']!=r['pdb_id'] and not set(row['accessions']).intersection(r['accessions']) and tuple(sorted((row['pool_index'],r['pool_index']))) not in edges for r in chosen)
    packet=source/'chemistry'/row['group_id'];data=source/'data/examples'/row['group_id']
    hashes={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.md']}
    manifest=json.loads((source/'data_manifest.json').read_text())
    for p in list(packet.iterdir())+list(data.iterdir()):
        if p.is_file():
            assert sha256(p)==manifest[str(p.relative_to(source))];hashes[str(p)]=sha256(p)
    hashes.update({str(source/name):sha256(source/name) for name in ['selection_lock.json','selection.json','preflight.json','source_lock.json','candidates.json','data_manifest.json']})
    write_json(root/'lock.json',dict(row=row,seed=500009,rank=8,adapter_seed=20260930,updates=1,lr=1e-5,
        hashes=hashes,previous_lock_sha256=sha256(base/'failure_step_reference_v1_20260930/lock.json'),
        weights_sha256=previous['weights_sha256'],source_isolation='inherited historical exclusions plus fresh8 pair/PDB/accession checks',
        scope='engineering preflight only; not efficacy or deployment'))
    start=time.monotonic();report=dict(complete=False,lock_sha256=sha256(root/'lock.json'))
    try:
        torch.set_num_threads(1)
        runner=rt.runner_setup(root/'work');runner.configs.dtype='fp32'
        assert Path(runner.configs.load_checkpoint_dir).resolve()==(base/'protenix_stage0_pkg/v1_1/runtime/checkpoint').resolve()
        model=runner.model.eval().requires_grad_(False)
        assert all(p.dtype==torch.float32 for p in model.parameters() if p.is_floating_point())
        original={n:p.detach().cpu().clone() for n,p in model.named_parameters()}
        state_keys=set(model.state_dict())
        torch.serialization.add_safe_globals([argparse.Namespace])
        from protenix.data.esm.compute_esm import load_esm_model
        esm,alphabet=load_esm_model('esm2-3b',local_esm_dir=runner.configs.load_checkpoint_dir)
        esm.eval().requires_grad_(False)
        native=torch.load(packet/'native.pt',map_location='cpu',weights_only=False);atoms=native['atoms']
        counts=dict(pairformer=0,diffusion=0)
        ph=model.pairformer_stack.register_forward_hook(lambda *unused:counts.__setitem__('pairformer',counts['pairformer']+1))
        dh=model.diffusion_module.register_forward_hook(lambda *unused:counts.__setitem__('diffusion',counts['diffusion']+1))
        with torch.no_grad():
            features=device_tree(native['features'],'cuda')
            tokens=alphabet.get_batch_converter()([('sequence',row['sequence'])])[2].cuda()
            features['esm_token_embedding']=esm(tokens,repr_layers=[esm.num_layers],return_contacts=False)['representations'][esm.num_layers][0,1:-1]
            del esm,tokens;torch.cuda.empty_cache()
            features=prepare_atom_pairs(model.relative_position_encoding.generate_relp(copy.deepcopy(features)))
            point=full_recycle_pairformer(model,features,N_cycle=4,inplace_safe=False,mc_dropout=False)
            sizes=[x.numel() for x in point];shapes=[x.shape for x in point]
            conditioning=tuple(x.reshape(s) for x,s in zip(torch.cat([x.flatten() for x in point]).split(sizes),shapes))
            del point
            noise=identity_noise(atoms,500009,device='cuda')
            baseline=diffusion_from_conditioning(model,features,noise.clone(),conditioning,steps=1).reshape(-1,3)
            teacher=diffusion_from_conditioning(model,features,noise.clone(),conditioning,steps=2).reshape(-1,3)
        mapping=dict(np.load(packet/'mapping.npz'));assert mapping['mask'].all()
        gt=torch.tensor(mapping['coordinates'],device='cuda',dtype=torch.float32)
        mask=torch.ones(len(gt),device='cuda',dtype=torch.bool)
        torch.save(dict(baseline=baseline.cpu(),teacher=teacher.cpu(),gt=gt.cpu(),noise=noise.cpu()),root/'targets.pt')
        adapters=attach_diffusion_adapter(model)
        params=[p for a in adapters.values() for p in a.parameters()]
        assert len(adapters)==56 and len(params)==112
        assert {id(p) for p in params}=={id(p) for p in model.parameters() if p.requires_grad}
        initial={name:{k:v.detach().cpu().clone() for k,v in adapter.state_dict().items()} for name,adapter in adapters.items()}
        with torch.no_grad():
            zero=diffusion_from_conditioning(model,features,noise.clone(),conditioning,steps=1).reshape(-1,3)
            assert torch.equal(zero,baseline),'zero-init parity failed'
        optimizer=torch.optim.AdamW(params,lr=1e-5,betas=(.9,.999),eps=1e-8,weight_decay=0)
        pred=diffusion_from_conditioning(model,features,noise.clone(),conditioning,steps=1).reshape(-1,3)
        lt=observed_aligned_mse(pred,teacher,mask);lg=observed_aligned_mse(pred,gt,mask)
        teacher_grads=torch.autograd.grad(lt,params,retain_graph=True)
        gt_grads=torch.autograd.grad(lg,params,retain_graph=True)
        tvec=torch.cat([g.detach().flatten().double() for g in teacher_grads]);gvec=torch.cat([g.detach().flatten().double() for g in gt_grads])
        assert torch.isfinite(tvec).all() and torch.isfinite(gvec).all() and tvec.norm()>0 and gvec.norm()>0
        (lt+lg).backward()
        assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in params)
        assert all(p.grad is None for p in model.parameters() if not p.requires_grad)
        norm=torch.nn.utils.clip_grad_norm_(params,1.,error_if_nonfinite=True);optimizer.step()
        trained={name:{k:v.detach().cpu().clone() for k,v in adapter.state_dict().items()} for name,adapter in adapters.items()}
        for name,value in original.items():
            current=model.get_parameter(name.rsplit('.',1)[0]+'.parametrizations.weight.original') if name.endswith('.weight') and name[:-7] in adapters else model.get_parameter(name)
            assert torch.equal(current.detach().cpu(),value),'base weight changed: '+name
        with torch.no_grad():
            updated=diffusion_from_conditioning(model,features,noise.clone(),conditioning,steps=1).reshape(-1,3)
            assert torch.isfinite(updated).all() and not torch.equal(updated,baseline)
            after=dict(teacher=float(observed_aligned_mse(updated,teacher,mask)),gt=float(observed_aligned_mse(updated,gt,mask)))
            for adapter in adapters.values():adapter.up.zero_()
            restored=diffusion_from_conditioning(model,features,noise.clone(),conditioning,steps=1).reshape(-1,3)
            assert torch.equal(restored,baseline)
            torch.save(dict(schema='diffusion_adapter_preflight_v1',rank=8,names=list(adapters),initial=initial,trained=trained,lock_sha256=sha256(root/'lock.json')),root/'adapter.pt')
            saved=torch.load(root/'adapter.pt',map_location='cpu',weights_only=False)
            for name,adapter in adapters.items():adapter.load_state_dict(saved['trained'][name])
            replay=diffusion_from_conditioning(model,features,noise.clone(),conditioning,steps=1).reshape(-1,3)
            assert torch.equal(replay,updated)
            merge_diffusion_adapter(model,adapters)
            assert set(model.state_dict())==state_keys
            merged=diffusion_from_conditioning(model,features,noise.clone(),conditioning,steps=1).reshape(-1,3)
            assert torch.equal(merged,updated)
        model.requires_grad_(False)
        live=tuple(x.detach().clone().requires_grad_(True) for x in conditioning)
        mx=diffusion_from_conditioning(model,features,noise.clone(),live,steps=1).reshape(-1,3)
        input_grads=torch.autograd.grad(observed_aligned_mse(mx,gt,mask),live)
        assert all(torch.isfinite(g).all() and g.norm()>0 for g in input_grads)
        assert counts==dict(pairformer=4,diffusion=10)
        outputs=dict(native_s1=baseline,reference_s2=teacher,zero_adapter=zero,updated_s1=updated,restored_s1=restored,reloaded_s1=replay,merged_s1=merged)
        topology=GeometryTopology(atoms,mapping['reference']);scores={}
        for name,coordinate in outputs.items():
            array=coordinate.detach().cpu().numpy();np.save(root/f'{name}.npy',array)
            _,geometry=topology.terms(torch.tensor(array,dtype=torch.float64))
            scores[name]=dict(aa_lddt=lddt_observed(array,mapping['coordinates'],mapping['residue_ids'])['score'],geometry=geometry)
        ph.remove();dh.remove()
        report.update(complete=True,counts=counts,zero_parity=True,original_parameters_unchanged=len(original),
            restored_parity=True,reloaded_parity=True,merged_parity=True,native_state_keys_restored=True,
            adapter_matrices=len(adapters),trainable_parameters=sum(p.numel() for p in params),
            losses_before=dict(teacher=float(lt.detach()),gt=float(lg.detach())),losses_after=after,
            teacher_grad_norm=float(tvec.norm()),gt_grad_norm=float(gvec.norm()),
            gradient_cosine=float(torch.dot(tvec,gvec)/(tvec.norm()*gvec.norm())),unclipped_grad_norm=float(norm),
            conditioning_gradient_norms=[float(g.norm()) for g in input_grads],scores=scores,
            peak_gpu_bytes=torch.cuda.max_memory_allocated(),checkpoint_sha256=sha256(root/'adapter.pt'),
            resolved_config=runner.configs.to_dict(),torch_version=torch.__version__,device=torch.cuda.get_device_name(0),
            scope='one engineering update; no efficacy/generalization/soft-sequence/deployment claim')
    except Exception:report['error']=traceback.format_exc()
    finally:
        report['seconds']=time.monotonic()-start;write_json(root/'report.json',report)
    if not report['complete']:raise RuntimeError(report.get('error','incomplete'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args()
    assert Path(os.environ['PROTENIX_ROOT_DIR']).resolve()==(a.root.parent/'protenix_stage0_pkg/v1_1/runtime').resolve()
    assert os.environ.get('LAYERNORM_TYPE')=='torch'
    adapter_preflight(a.root)
