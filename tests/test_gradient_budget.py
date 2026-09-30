import torch
import pytest
from fastglycan.gradient_budget import component_gradient_statistics


def test_gradient_budget_preserves_signed_cancellation():
    names=['coordinate','smooth_lddt','bond','chirality','clash','teacher']
    g=torch.tensor([[2.,0.],[0.,0.],[0.,0.],[0.,0.],[-1.,1.],[0.,1.]],dtype=torch.float64)
    weights={n:1. for n in names};weights['teacher']=.001
    s=component_gradient_statistics(g,names,weights)
    assert s['signed_projection_onto_gt']['coordinate']==pytest.approx(1.)
    assert s['signed_projection_onto_gt']['clash']==pytest.approx(0.)
    assert s['group_cosines']['structure_vs_chemistry']==pytest.approx(-2**-.5)
    assert s['teacher_to_gt_norm_ratio']==pytest.approx(.001/2**.5)
    assert s['pairwise_cosine'][1][0] is None
    # Near cancellation can give negative / >1 projections without an error.
    g[4]=torch.tensor([-1.5,0.]);s=component_gradient_statistics(g,names,weights)
    assert s['signed_projection_onto_gt']['coordinate']==pytest.approx(4.)
    assert s['signed_projection_onto_gt']['clash']==pytest.approx(-3.)
    g[4]=torch.tensor([-2.,0.]);s=component_gradient_statistics(g,names,weights)
    assert s['teacher_to_gt_norm_ratio'] is None
    assert all(v is None for v in s['signed_projection_onto_gt'].values())
