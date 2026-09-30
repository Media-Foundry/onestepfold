#!/usr/bin/env python3
"""Bounded cross-backend measurement; never relax a gate or update parameters."""
import argparse
import hashlib
import json
import time
from pathlib import Path
import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.teacher_pairing import feature_digest, tensor_digest


def replay_difference(predicted, reference, ca):
    x=np.asarray(predicted,dtype=np.float64);y=np.asarray(reference,dtype=np.float64)
    if x.shape!=y.shape or x.ndim!=2 or x.shape[1]!=3 or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError('finite matched atom coordinates required')
    a=x[ca];b=y[ca]
    if len(a)<3:raise ValueError('need at least three CA atoms')
    a=a-a.mean(0);b=b-b.mean(0);u,_,vh=np.linalg.svd(a.T@b)
    rotation=u@np.diag([1.,1.,np.linalg.det(u@vh)])@vh
    return dict(max_abs=float(np.max(np.abs(x-y))),atom_rms=float(np.sqrt(np.mean(np.sum((x-y)**2,-1)))),
                ca_aligned_rmsd=float(np.sqrt(np.mean(np.sum((a@rotation-b)**2,-1)))),
                exact=bool(np.array_equal(predicted,reference)))


def run_backend_replay_probe(output, source, index):
    from fastglycan import stage0_confirm_runtime as rt
    from fastglycan.models.differentiable_mini import diffusion_from_conditioning
    from fastglycan.models.diffusion_scope import load_dense_diffusion_checkpoint
    from fastglycan.diffusion_pilot_metrics import prepare_pilot_scoring, score_diffusion_pilot
    import train_folding_scale as trainer
    output.mkdir(parents=True,exist_ok=False);start=time.monotonic();torch.set_num_threads(1)
    lock=json.loads((source/'lock.json').read_text());g=lock['engineering_groups'][index]
    row=next(r for r in lock['rows'] if r['group_id']==g);seed=lock['training_seeds'][0]
    runner=rt.runner_setup(output/'work');runner.configs.dtype='fp32';model=runner.model.eval().requires_grad_(False)
    features,cond,noise,labels,teacher,atoms=trainer.folding_training_input(lock,g,seed,set())
    public_checkpoint=Path('/data/user/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime/checkpoint/protenix_mini_esm_v0.5.0.pt')
    assert sha256(public_checkpoint)=='1301bba9ad322518eace60fd244ded7904439f55317e90d402cc7a0c06026664'
    names={n:p for n,p in model.named_parameters()}
    def fingerprints():return {n:hashlib.sha256(p.detach().contiguous().cpu().numpy().tobytes()).hexdigest() for n,p in names.items()}
    initial=fingerprints()
    mapping=dict(np.load(Path(lock['source'])/'chemistry'/g/'mapping.npz'));ca=mapping['atom_names']=='CA'
    context=prepare_pilot_scoring(mapping,atoms.bonds.as_array(),row['sequence'])
    calibration=json.loads((source/'code/docs/connection_reference_bands.json').read_text())
    hashes=dict(conditioning=feature_digest(cond),features=feature_digest(features),noise=tensor_digest(noise))
    np.save(output/'noise.npy',noise.cpu().numpy())
    # Readback fingerprints intentionally recorded before forwards, with unchanged inputs.
    report=dict(complete=False,group_id=g,pdb_id=row['pdb_id'],length=len(row['sequence']),seed=seed,
        source_lock_sha256=sha256(source/'lock.json'),script_sha256=sha256(Path(__file__)),
        input_hashes=hashes,torch=torch.__version__,numpy=np.__version__,hip=torch.version.hip,
        device=torch.cuda.get_device_name(0),calls=0,stages={},scope='two engineering TRAIN cases; cross-backend measurement, not quality/generalization acceptance')
    for stage in ['public','retained']:
        if stage=='retained':
            cp=Path(lock['initial_checkpoint']);assert sha256(cp)=='7fc01820269b6f376f8313b79c4ab2bf8fcfd2a0b2a017a432033a51b73fd829'
            state=torch.load(cp,map_location='cpu',weights_only=False)
            load_dense_diffusion_checkpoint(model,state,arm='diffusion_dense',expected_names=lock['selected_names'])
        before=fingerprints()
        reference=Path(lock['cache'])/'examples'/g/f's1_seed{seed}.npy' if stage=='public' else Path(lock['global_distance']['retained_engineering_coordinates'][g]['path'])
        expected=np.load(reference);saved=[];times=[]
        with torch.no_grad():
            for repeat in range(2):
                cpu=torch.get_rng_state().clone();gpu=torch.cuda.get_rng_state().clone();torch.cuda.synchronize();t=time.monotonic()
                value=diffusion_from_conditioning(model,features,noise.clone(),cond,steps=1).reshape(-1,3)
                torch.cuda.synchronize();times.append(time.monotonic()-t)
                assert torch.isfinite(value).all() and torch.equal(cpu,torch.get_rng_state()) and torch.equal(gpu,torch.cuda.get_rng_state())
                x=value.cpu().numpy();np.save(output/f'{stage}_{repeat}.npy',x);saved.append(x);report['calls']+=1
        assert fingerprints()==before
        if stage=='public':assert before==initial
        else:
            archived=json.loads((source/'expanded/initial_fingerprints.json').read_text());assert before==archived
        item=dict(reference_sha256=sha256(reference),reference=str(reference),seconds=times,
            versus_hpc3=[replay_difference(x,expected,ca) for x in saved],repeat=replay_difference(saved[1],saved[0],ca),
            reference_quality=score_diffusion_pilot(expected,context,calibration),
            measured_quality=score_diffusion_pilot(saved[0],context,calibration),parameters_unchanged=True,
            parameter_fingerprints_sha256=hashlib.sha256(json.dumps(before,sort_keys=True).encode()).hexdigest())
        report['stages'][stage]=item;write_json(output/'report.json',report)
    assert hashes==dict(conditioning=feature_digest(cond),features=feature_digest(features),noise=tensor_digest(noise))
    report.update(complete=True,seconds=time.monotonic()-start,parameter_updates=0,peak_gpu_bytes=torch.cuda.max_memory_allocated())
    write_json(output/'report.json',report)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--source',type=Path,required=True);p.add_argument('--index',type=int,choices=[0,1],required=True)
    a=p.parse_args();run_backend_replay_probe(a.output.resolve(),a.source.resolve(),a.index)
