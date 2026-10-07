import pytest
import torch

from fastglycan.models.compensated_recycle import (
    RecycleCompensator, initialize_cached_recycle, capture_cached_prefix, native_recycle_step,
)
from fastglycan.models.differentiable_mini import full_recycle_pairformer
from fastglycan.models.prefix_recycle import capture_rng_state, restore_rng_state
from test_prefix_recycle import example, StochasticMSA


def test_cached_native_c4_and_split_rng_match_and_bypass_embedder():
    m, f = example(); m.requires_grad_(False); m.msa_module = StochasticMSA()
    rng = capture_rng_state()
    expected = full_recycle_pairformer(m, f, 4)
    expected_rng = capture_rng_state()
    m.input_embedder.register_forward_pre_hook(lambda *a: pytest.fail('input encoder called'))
    restore_rng_state(rng)
    init = initialize_cached_recycle(m, f, f['x'])
    prefix, boundary = capture_cached_prefix(m, f, init)
    saved = tuple(x.clone() for x in prefix)
    torch.rand(100)
    actual = native_recycle_step(m, f, init, prefix, rng=boundary)
    assert all(torch.equal(x, y) for x, y in zip(expected[1:], actual))
    assert torch.equal(capture_rng_state()['cpu'], expected_rng['cpu'])
    assert all(torch.equal(x, y) for x, y in zip(saved, prefix))


def test_zero_initialization_noedit_and_native_gradient_after_update():
    m, f = example(); m.requires_grad_(False)
    init = initialize_cached_recycle(m, f, f['x'])
    prefix, rng = capture_cached_prefix(m, f, init)
    net = RecycleCompensator(4, 4, 16, 8, 2)
    assert net(prefix, 1, 2, 2) is prefix
    corrected = net(prefix, 1, 2, 5)
    assert all(torch.equal(x, y) for x, y in zip(prefix, corrected))
    optim = torch.optim.AdamW(net.parameters(), lr=1e-3)
    for step in range(2):
        optim.zero_grad()
        corrected = net(prefix, 1, 2, 5)
        final = native_recycle_step(m, f, init, corrected, rng=rng)
        sum(x.square().mean() for x in final).backward()
        assert net.single_out.weight.grad.norm() > 0
        assert net.pair_out.weight.grad.norm() > 0
        if step:
            assert net.aa.weight.grad.norm() > 0
            assert net.relation[1].weight.grad.norm() > 0
        optim.step()
    assert all(p.grad is None for p in m.parameters())
    assert net(prefix, 1, 2, 2) is prefix


def test_candidate_isolation_global_update_and_bad_edits():
    torch.manual_seed(17)
    net = RecycleCompensator(4, 4, 16, 8, 2)
    torch.nn.init.normal_(net.single_out.weight, std=.01)
    torch.nn.init.normal_(net.pair_out.weight, std=.01)
    prefix = torch.randn(7, 4), torch.randn(7, 7, 4)
    saved = tuple(t.clone() for t in prefix)
    a = net(prefix, 1, 2, 5); b = net(prefix, 1, 2, 6)
    again = net(prefix, 1, 2, 5)
    assert all(torch.equal(x, y) for x, y in zip(a, again))
    assert not torch.equal(a[1][6, 6], prefix[1][6, 6])
    assert not torch.equal(a[1], b[1])
    assert all(torch.equal(x, y) for x, y in zip(saved, prefix))
    with pytest.raises(ValueError): net(prefix, 7, 2, 5)


def test_empty_constraint_feature_matches_native_none_contract():
    m,f=example();m.requires_grad_(False)
    m.constraint_embedder=lambda _:None
    f['constraint_feature']={}
    expected=full_recycle_pairformer(m,f,4)
    init=initialize_cached_recycle(m,f,f['x'])
    state,rng=capture_cached_prefix(m,f,init)
    actual=native_recycle_step(m,f,init,state,rng=rng)
    assert all(torch.equal(x,y) for x,y in zip(actual,expected[1:]))
