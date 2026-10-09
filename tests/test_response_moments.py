import pytest
import torch
from fastglycan.response_moments import ResponseMoments


def test_streaming_matches_explicit_centering_and_common_decomposition():
    torch.manual_seed(13)
    target=torch.randn(19,5,6,dtype=torch.float64)
    pred=.3*target+torch.randn(5,6,dtype=torch.float64)
    m=ResponseMoments()
    for p,t in zip(pred,target):m.add(p,t)
    r=m.result();pc=pred-pred.mean(0);tc=target-target.mean(0)
    assert r['centered']['nmse']==pytest.approx(float((pc-tc).square().sum()/tc.square().sum()))
    assert r['centered']['cosine']==pytest.approx(1.)
    assert r['raw']['error_energy']==pytest.approx(r['common']['error_energy']+r['centered']['error_energy'])
    zero=ResponseMoments()
    for t in target:zero.add(torch.zeros_like(t),t)
    assert zero.result()['centered']['nmse']==pytest.approx(1.)
    assert zero.result()['centered']['cosine'] is None
    with pytest.raises(ValueError):ResponseMoments().result()
