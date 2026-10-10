import pytest
import torch

from fastglycan.models.normalized_trajectory import (
    normalized_trajectory_transport, channel_error_decomposition,
)


def test_noedit_preserves_third_boundary_exactly_without_aliasing():
    torch.manual_seed(4)
    w1=(torch.randn(5,8)*1e4,torch.randn(5,5,4)*1e3)
    w3=tuple(torch.randn_like(x) for x in w1)
    saved=tuple(x.clone() for x in w3)
    result=normalized_trajectory_transport(w1,w1,w3,(1e-5,1e-5))
    assert all(torch.equal(a,b) for a,b in zip(result,w3))
    result[0].add_(10)
    assert all(torch.equal(a,b) for a,b in zip(saved,w3))


def test_scaled_reference_transports_direction_in_third_boundary_units():
    # Centered, equal-norm first-boundary vectors; exact expected finite-eps law.
    first=torch.tensor([[1.,-1.,0.,0.]])
    candidate=torch.tensor([[0.,0.,1.,-1.]])
    third=3*first+7
    eps=1e-5
    got=normalized_trajectory_transport((candidate,candidate),(first,first),(third,third),(eps,eps))
    ratio=((4.5+eps)/(.5+eps))**.5
    expected=third+ratio*(candidate-first)
    assert torch.allclose(got[0],expected,atol=1e-6,rtol=1e-6)
    assert not torch.allclose(got[0],third+candidate-first)


def test_channel_shift_is_removed_and_candidate_order_is_irrelevant():
    torch.manual_seed(5)
    first=(torch.randn(3,8),torch.randn(3,3,4));third=tuple(2*x for x in first)
    a=tuple(x+.1*torch.randn_like(x) for x in first);b=tuple(x-.2*torch.randn_like(x) for x in first)
    before=tuple(x.clone() for x in a)
    one=normalized_trajectory_transport(a,first,third,(1e-5,1e-5))
    normalized_trajectory_transport(b,first,third,(1e-5,1e-5))
    two=normalized_trajectory_transport(a,first,third,(1e-5,1e-5))
    assert all(torch.equal(x,y) for x,y in zip(one,two))
    assert all(torch.equal(x,y) for x,y in zip(a,before))
    shifted=normalized_trajectory_transport(tuple(x+2 for x in a),first,third,(1e-5,1e-5))
    assert all(torch.allclose(x,y,atol=2e-6,rtol=2e-6) for x,y in zip(one,shifted))


def test_error_decomposition_is_over_channels_not_candidates():
    target=torch.zeros(2,3,dtype=torch.float64)
    pred=torch.tensor([[3.,3.,3.],[1.,-1.,0.]],dtype=torch.float64)
    d=channel_error_decomposition(pred,target)
    assert d['mse']==pytest.approx(29/6)
    assert d['channel_mean_mse']==pytest.approx(4.5)
    assert d['centered_channel_mse']==pytest.approx(1/3)
    assert d['channel_mean_fraction']==pytest.approx(27/29)


def test_rejects_bad_contract_and_nonfinite_states():
    state=(torch.ones(2,3),torch.ones(2,2,4))
    for eps in [(0.,1e-5),(float('nan'),1e-5),(1e-5,)]:
        with pytest.raises(ValueError):normalized_trajectory_transport(state,state,state,eps)
    bad=(torch.full((2,3),float('nan')),state[1])
    with pytest.raises(ValueError):normalized_trajectory_transport(bad,state,state,(1e-5,1e-5))
