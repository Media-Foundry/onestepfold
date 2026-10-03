import torch
from fastglycan.student_probe import tensor_diversity


def test_exact_candidate_collapse_is_distinct_from_zero_output():
    x=torch.ones(19,4,3,requires_grad=True)
    a=tensor_diversity(x)
    assert a['candidate_identical'] and a['candidate_centered_rms']==0 and a['rms']==1
    y=x.detach().clone();y[0,0,0]+=1
    b=tensor_diversity(y)
    assert not b['candidate_identical'] and b['candidate_centered_rms']>0
    z=tensor_diversity(torch.full((19,3),-10.))
    assert z['below_minus6_fraction']==1 and z['zero_fraction']==0
