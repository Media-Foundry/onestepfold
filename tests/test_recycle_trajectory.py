import numpy as np
import pytest
import torch

from fastglycan.models.compensated_recycle import initialize_cached_recycle, native_recycle_step
from fastglycan.models.differentiable_mini import full_recycle_pairformer
from fastglycan.models.prefix_recycle import capture_rng_state, restore_rng_state
from fastglycan.models.recycle_trajectory import (
    transfer_reference_progress, same_rng, capture_recycle_trajectory,
    finish_transferred_candidate,
)
from test_prefix_recycle import example, StochasticMSA


def test_noedit_identity_survives_large_reference_cancellation_and_preserves_inputs():
    first = (torch.full((3,4), 2.**25), torch.full((3,3,4), 2.**25))
    third = (torch.ones(3,4), torch.ones(3,3,4))
    saved = tuple(t.clone() for t in first+third)
    result = transfer_reference_progress(first,first,third)
    assert all(torch.equal(a,b) for a,b in zip(result,third))
    assert all(torch.equal(a,b) for a,b in zip(first+third,saved))
    assert not torch.equal(first[0]+(third[0]-first[0]),third[0])


def test_native_trajectory_split_rng_and_noedit_final_replay():
    model,features = example();model.requires_grad_(False)
    model.msa_module=StochasticMSA()
    initial=capture_rng_state()
    exact=full_recycle_pairformer(model,features,4);final_rng=capture_rng_state()
    initialization=initialize_cached_recycle(model,features,features['x'])
    ambient=capture_rng_state()
    states,rngs=capture_recycle_trajectory(model,features,initialization,initial)
    assert same_rng(ambient,capture_rng_state())
    assert all(torch.equal(a,b) for a,b in zip(states[4],exact[1:]))
    assert same_rng(rngs[4],final_rng)
    torch.rand(7);np.random.random(3)
    restored=native_recycle_step(model,features,initialization,states[3],rng=rngs[3])
    assert all(torch.equal(a,b) for a,b in zip(restored,states[4]))
    assert same_rng(capture_rng_state(),rngs[4])
    before=capture_rng_state()
    predicted3,final=finish_transferred_candidate(model,features,initialization,
                                                 states[1],states[1],states[3],rngs[3])
    assert all(torch.equal(a,b) for a,b in zip(predicted3,states[3]))
    assert all(torch.equal(a,b) for a,b in zip(final,states[4]))
    assert same_rng(before,capture_rng_state())


def test_transport_uses_candidate_response_and_is_order_independent():
    first=(torch.randn(3,4),torch.randn(3,3,4))
    third=(torch.randn(3,4),torch.randn(3,3,4))
    candidate=tuple(t+.25 for t in first)
    other=tuple(t-.5 for t in first)
    expected=transfer_reference_progress(candidate,first,third)
    transfer_reference_progress(other,first,third)
    again=transfer_reference_progress(candidate,first,third)
    assert all(torch.equal(a,b) for a,b in zip(expected,again))
    assert all(torch.allclose(a-b,torch.full_like(b,.25)) for a,b in zip(expected,third))
    with pytest.raises(ValueError,match='shape/dtype/device'):
        transfer_reference_progress(tuple(t.double() for t in candidate),first,third)
    with pytest.raises(ValueError,match='nonfinite'):
        transfer_reference_progress((candidate[0]*float('nan'),candidate[1]),first,third)


def test_rng_compare_detects_each_random_family():
    state=capture_rng_state()
    changed=dict(state,cpu=state['cpu'].clone());changed['cpu'][0]^=1
    assert not same_rng(state,changed)
    changed=dict(state,numpy=(*state['numpy'][:2],state['numpy'][2]+1,*state['numpy'][3:]))
    assert not same_rng(state,changed)
