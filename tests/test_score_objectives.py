import numpy as np
import pytest
import torch
from fastglycan.score_objectives import training_site_weights,score_objective,clipping_counterfactual


def cases():
    return [dict(role='train',parent_index=i,position=0,source_aa='A',wt=0,
                 target_delta=[(np.arange(20)*scale).tolist()]*2) for i,scale in enumerate([0.,.01,1.,100.])]


def test_floor_train_only_and_mean_one():
    c=cases();d=training_site_weights(c);w=[x['weight'] for x in d['sites']]
    assert np.mean(w)==pytest.approx(1) and np.isfinite(w).all() and w[0]>w[-1]>0
    c[0]['role']='confirmation_candidate'
    with pytest.raises(ValueError):training_site_weights(c)
    c=cases();c[0]['target_delta']*=2
    with pytest.raises(ValueError):training_site_weights(c)


def test_centering_uses_prediction_mean_and_retains_units():
    p=torch.arange(19,dtype=torch.float64).requires_grad_();y=p.detach()+5
    a=score_objective(p,y,'A')[1];b=score_objective(p,y,'B')[1]
    assert a.item()==25 and b.item()==0
    assert torch.equal(torch.autograd.grad(b,p)[0],torch.zeros_like(p))
    y=torch.flip(p.detach(),[0]);base,weighted=score_objective(p,y,'C',.125)
    g=torch.autograd.grad(weighted,p,retain_graph=True)[0];g0=torch.autograd.grad(base,p)[0]
    assert torch.allclose(g,g0*.125)


def test_clipping_cancels_scalar_only_when_saturated():
    a=clipping_counterfactual(10.,.1)
    assert a['unweighted_norm']==100 and a['both_clipped']
    assert a['post_vector_multiplier']==pytest.approx(1,abs=1e-6)
    b=clipping_counterfactual(.1,.1)
    assert not b['weighted_clipped'] and b['post_vector_multiplier']==pytest.approx(.1,abs=1e-6)


def test_clipping_counterfactual_matches_actual_torch_vectors():
    for magnitude,weight in [(100.,.1),(.2,2.5),(10.,1e-5)]:
        base=torch.tensor([.6,.8],dtype=torch.float64)*magnitude
        p=torch.nn.Parameter(torch.zeros(2,dtype=torch.float64));q=torch.nn.Parameter(torch.zeros(2,dtype=torch.float64))
        p.grad=base.clone();q.grad=base*weight
        torch.nn.utils.clip_grad_norm_([p],1.);weighted=torch.nn.utils.clip_grad_norm_([q],1.)
        d=clipping_counterfactual(float(weighted),weight)
        assert torch.allclose(q.grad,p.grad*d['post_vector_multiplier'],rtol=1e-10,atol=1e-12)
        assert q.grad.norm().item()==pytest.approx(d['weighted_post_norm'],rel=1e-10)
