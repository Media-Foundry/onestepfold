#!/usr/bin/env python3
"""Reload a saved checkpoint and exactly replay fixed TRAIN/DEV predictions."""
import argparse
import json
from pathlib import Path
import numpy as np
import torch
from fastglycan.models.esmc_core import ESMCFoldCore
from fastglycan.pretrained_conditioning import install_pretrained_bridge
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.teacher_pairing import feature_digest


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--size',type=int,choices=[2048,8192],required=True)
    p.add_argument('--step',type=int,choices=[0,4096],required=True);a=p.parse_args()
    r=a.root;folder=r/('train_%d'%a.size);out=folder/('checkpoint_audit_%04d.json'%a.step)
    assert not out.exists();lock=json.loads((r/'lock.json').read_text())
    assert torch.cuda.device_count()==1 and torch.cuda.get_device_name()==lock['gpu_model']
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    source=json.loads((r/'code_v1/source_manifest.json').read_text())
    for n,h in source['files'].items():assert sha256(r/'code_v1'/n)==h,n
    for n,h in lock['common_files'].items():assert sha256(r/n)==h,n
    checkpoint=folder/('step_%04d.pt'%a.step)
    saved=torch.load(checkpoint,map_location='cpu',weights_only=True)
    assert saved['step']==a.step and saved['training_size']==a.size and saved['samples_seen']==a.step*4
    assert saved['lock_sha256']==sha256(r/'lock.json')
    assert feature_digest(saved['model'])==saved['model_state_sha256']
    export_path=folder/('evaluation_%04d.json'%a.step);export=json.loads(export_path.read_text())
    assert export['complete'] and export['weights_unchanged'] and export['lock_sha256']==sha256(r/'lock.json')
    assert saved['model_state_sha256']==export['model_state_sha256']
    if a.step==4096:
        worker=json.loads((folder/'report.json').read_text());assert worker['complete'] and worker['steps']==4096
        assert worker['last_checkpoint_sha256']==sha256(checkpoint)
        assert worker['final_model_state_sha256']==saved['model_state_sha256']
    manifest=json.loads((r/'data_manifest.json').read_text());byid={x['group_id']:x for x in manifest['selection']}
    selected=[]
    for split in ['train','validation']:
        groups=(lock['train_probe_groups'] if split=='train' else [g for g,row in byid.items() if row['split']=='validation'])
        ordered=sorted(groups,key=lambda g:(len(byid[g]['sequence']),g))
        selected.extend(ordered[round(i*(len(ordered)-1)/7)] for i in range(8))
    assert len(set(selected))==16
    native={k.removeprefix('module.'):v for k,v in torch.load(r/'native.pt',map_location='cpu',weights_only=True)['model'].items()}
    bridge=torch.load(r/'bridge.pt',map_location='cpu',weights_only=True)
    model=ESMCFoldCore(seed=101,deterministic_capacity=True)
    assert model.config.to_dict()==json.loads((r/'runtime_contract.json').read_text())['config']
    install_pretrained_bridge(model,native,bridge);del native,bridge
    heads=lambda:feature_digest({'confidence':model.core.confidence_head.state_dict(),'distogram':model.core.distogram_head.state_dict()})
    initial_heads=heads();model.load_state_dict(saved['model'],strict=True)
    state=saved['model_state_sha256'];del saved
    assert heads()==initial_heads;model.requires_grad_(False).cuda().eval()
    assert feature_digest(model.state_dict())==state
    from protenix.utils.seed import seed_everything
    counts={};handles=[];sampling={};original=model.core.sample_diffusion
    for name,module in [('trunk',model.core.pairformer_stack),('structure',model.core.diffusion_module),('confidence',model.core.confidence_head)]:
        def hook(*_,name=name):counts[name]+=1
        handles.append(module.register_forward_pre_hook(hook))
    def sampler(**kw):
        sampling.update(noise_schedule=kw['noise_schedule'].detach().cpu().tolist(),N_sample=kw['N_sample'],
                        parameters={k:model.config.sample_diffusion[k] for k in ('gamma0','gamma_min','noise_scale_lambda','step_scale_eta')})
        assert sampling==lock['sampling'];return original(**kw)
    model.core.sample_diffusion=sampler
    expected={(x['group_id'],x['noise']):x for x in export['predictions']};checked=[]
    for g in selected:
        datafile=r/'data'/g/'inputs.pt';assert sha256(datafile)==manifest['data_files'][g]['inputs.pt']
        features=torch.load(datafile,map_location='cpu',weights_only=True)['features']
        for noise in [12345,54321]:
            row=expected[g,noise];path=r/row['path'];assert sha256(path)==row['sha256']
            seed_everything(noise,deterministic=True);counts.update(trunk=0,structure=0,confidence=0)
            with torch.no_grad():x=model(features,confidence=False)['coordinate'][0].cpu().numpy()
            assert counts=={'trunk':1,'structure':1,'confidence':0}
            assert np.array_equal(x,np.load(path,allow_pickle=False)),(g,noise)
            checked.append({'group_id':g,'split':byid[g]['split'],'length':len(byid[g]['sequence']),'noise':noise,'prediction_sha256':row['sha256'],'exact':True})
    assert feature_digest(model.state_dict())==state and heads()==initial_heads
    for h in handles:h.remove()
    write_json(out,{'complete':True,'size':a.size,'step':a.step,'checkpoint_sha256':sha256(checkpoint),
        'model_state_sha256':state,'export_sha256':sha256(export_path),'lock_sha256':sha256(r/'lock.json'),
        'source_sha256':sha256(Path(__file__)),'selection_rule':'8 length-spaced common TRAIN probes and8 length-spaced DEV targets; group_id breaks ties',
        'predictions':checked,'sampling':sampling,'weights_unchanged':True,'frozen_heads_match_initial':True,
        'optimizer_updates':0,'scope':'Checkpoint reconstruction and exact32-prediction replay, not independent training or generalization'})
    print(json.dumps({'complete':True,'size':a.size,'step':a.step,'exact_replays':32}),flush=True)


if __name__=='__main__':main()
