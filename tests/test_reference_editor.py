import pytest
import torch
from fastglycan.reference_editor import ReferenceEditModel


def fixture():
    torch.manual_seed(22)
    net = ReferenceEditModel(12, 8, 4, width=16, workspace=3, blocks=2, heads=4, pair_width=8, pair_chunk=2)
    reference = (torch.randn(6, 12), torch.randn(6, 8), torch.randn(6, 6, 4))
    return net, reference, [0, 1, 2, 3, 4, 5]


def test_no_edit_cached_rebuilt_and_candidate_order_independence():
    net, raw, sequence = fixture()
    with torch.no_grad():
        cache = net.prepare_reference(raw, sequence)
        edits = [[], [(1, 1, 7)], [(4, 4, 9)], [(1, 1, 1)]]
        output = net(cache, edits)
        reverse = net(cache, edits[::-1])
        fresh = net(net.prepare_reference(raw, sequence), edits)
        for a, b, c, r in zip(output, reverse, fresh, raw):
            assert torch.equal(a[0], r) and torch.equal(a[3], r)
            torch.testing.assert_close(a, b.flip(0))
            assert torch.equal(a, c)
        for i, edit in enumerate(edits):
            alone = net(cache, [edit])
            for a, b in zip(output, alone):
                torch.testing.assert_close(a[i], b[0], rtol=1e-5, atol=2e-6)
        # Off-site, off-row/column outputs can change.
        assert (output[2][1, 3:, 3:] - raw[2][3:, 3:]).abs().max() > 0


def test_multiedit_order_and_invalid_edits():
    net, raw, sequence = fixture()
    cache = net.prepare_reference(raw, sequence)
    a = net(cache, [[(1, 1, 7), (4, 4, 8)]])
    b = net(cache, [[(4, 4, 8), (1, 1, 7)]])
    assert all(torch.equal(x, y) for x, y in zip(a, b))
    with pytest.raises(ValueError):
        net(cache, [[(1, 2, 7)]])
    with pytest.raises(ValueError):
        net(cache, [[(1, 1, 7), (1, 1, 8)]])


def test_training_gradients_and_stale_cache_rejected():
    net, raw, sequence = fixture()
    cache = net.prepare_reference(raw, sequence)
    output = net(cache, [[(1, 1, 7)], [(4, 4, 8)]])
    loss = sum((x - r[None] - .1).square().mean() for x, r in zip(output, raw))
    loss.backward()
    for name in ('inputs.1.weight', 'blocks.0.read.q.weight', 'aa.weight', 'pair_base.1.weight', 'input_out.weight', 'single_out.weight', 'pair_out.3.weight'):
        grad = dict(net.named_parameters())[name].grad
        assert grad is not None and torch.isfinite(grad).all() and grad.abs().sum() > 0, name
    torch.optim.SGD(net.parameters(), lr=.01).step()
    with pytest.raises(RuntimeError, match='parameter version'):
        net(cache, [[]])
    cache = net.prepare_reference(raw, sequence)
    raw[2].add_(1)
    with pytest.raises(RuntimeError, match='modified'):
        net(cache, [[]])
