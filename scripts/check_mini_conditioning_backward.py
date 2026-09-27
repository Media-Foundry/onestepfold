#!/usr/bin/env python3
"""Fixed-graph ESM-feature diagnostic; deliberately NOT a soft-sequence test."""
import argparse
import copy
from pathlib import Path
import json
import numpy as np
import torch
from fastglycan import stage0_confirm_runtime as rt
from fastglycan.models.differentiable_mini import fixed_graph_coordinates, directional_check
from fastglycan.paired_teacher_protocol import write_json
from run_c4_s1_attribution import CommonNoise


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); root=a.root.resolve(); out=a.output.resolve()
    out.mkdir(exist_ok=False)
    info=rt.load_json(root/'packets.json')
    g=min(info, key=lambda g: (info[g]['length'],g))
    packet=rt.verify_packet(root/'packets'/f'{g}.pt',info[g])
    runner=rt.runner_setup(out/'work');runner.configs.dtype='fp32'
    model=runner.model.eval().requires_grad_(False)
    captured={}; original=model.get_pairformer_output
    def capture(*args, **kwargs):
        captured['features']=copy.deepcopy(kwargs.get('input_feature_dict',args[0] if args else None))
        return original(*args, **kwargs)
    model.get_pairformer_output=capture
    try:
        with CommonNoise(runner,g,103) as noise:
            pred, baseline, _=rt.predict(runner,packet['data'],'c4_s1',103,None)
    finally:
        model.get_pairformer_output=original
    del pred
    features=captured['features'];device=next(model.parameters()).device
    initial=torch.tensor(noise.arrays['initial_coordinate'],device=device)
    with torch.no_grad():
        replay=fixed_graph_coordinates(model,features,initial)
    error=float((replay-torch.tensor(baseline,device=device)).abs().max())
    report=dict(scope='fixed_atom_graph_cached_ESM_feature_partial_derivative',group=g,
                length=info[g]['length'],forward_max_abs_error=error,complete=False)
    write_json(out/'report.json',report)
    if error>1e-3: raise RuntimeError('forward replay exceeds 1e-3 A; stop before backward')
    point=features['esm_token_embedding'].detach()
    torch.manual_seed(101); direction=torch.randn_like(point)
    # Translation/rotation invariant distance objective; diagnostic, not design success.
    target=torch.pdist(replay[0,::max(1,replay.shape[-2]//32)]).detach()*0.95
    gradients=[]
    for steps in (1,2):
        def objective(embedding):
            f=dict(features);f['esm_token_embedding']=embedding
            x=fixed_graph_coordinates(model,f,initial,steps=steps)
            distances=torch.pdist(x[0,::max(1,x.shape[-2]//32)])
            return (distances-target).square().mean()
        gradient, fd=directional_check(objective,point,direction)
        repeated,_=directional_check(objective,point,direction,steps=())
        gradients.append(gradient.flatten())
        report[f's{steps}']=dict(finite=bool(torch.isfinite(gradient).all()),
            norm=float(gradient.norm()),max_abs=float(gradient.abs().max()),
            zero_fraction=float((gradient==0).float().mean()),
            repeated_gradient_max_difference=float((gradient-repeated).abs().max()),
            finite_differences=fd)
        write_json(out/'report.json',report)
    report['gradient_cosine']=float(torch.nn.functional.cosine_similarity(*gradients,dim=0))
    report['complete']=True;write_json(out/'report.json',report)

if __name__=='__main__': main()
