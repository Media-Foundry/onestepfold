import pytest
import torch
from fastglycan.global_response_rank import GlobalResponseBasis, GLOBAL_RANKS
from fastglycan.jacobian_residual_rank import JacobianResidualBasis, hard_replacement_direction


def test_wt_and_mutant_archive_axes_are_distinct():
    import numpy as np
    from fastglycan.jacobian_residual_rank import archived_reference_coordinates
    wt = np.arange(2*17*3).reshape(2, 17, 3)
    first, second = archived_reference_coordinates(wt, is_wt=True)
    assert first is wt and second is wt
    mutant = np.stack([wt+1, wt+2, wt+3])
    first, second = archived_reference_coordinates(mutant, is_wt=False)
    assert np.array_equal(first, wt+1) and np.array_equal(second, wt+2)
    with pytest.raises(ValueError):archived_reference_coordinates(wt, is_wt=False)
    with pytest.raises(ValueError):archived_reference_coordinates(mutant, is_wt=True)


def test_reverse_checkpoint_configuration_is_restored():
    from fastglycan.jacobian_residual_rank import checkpointed_reverse
    from fastglycan.models import soft_sequence_chart as chart
    from fastglycan.models.soft_esm import soft_esm2
    model = torch.nn.Sequential(torch.nn.Linear(2, 2))
    model.blocks_per_ckpt = None
    original = chart.soft_esm2
    with pytest.raises(RuntimeError):
        with checkpointed_reverse(model):
            assert model.blocks_per_ckpt == 1 and chart.soft_esm2 is soft_esm2
            raise RuntimeError('test restoration')
    assert model.blocks_per_ckpt is None and chart.soft_esm2 is original


def test_zero_tangent_and_complete_reconstruction():
    torch.manual_seed(228101)
    s, z = torch.randn(7, 8), torch.randn(7, 7, 4)
    hs, hz = torch.randn(19, 7, 8), torch.randn(19, 7, 7, 4)
    raw = GlobalResponseBasis(s, z, hs, hz)
    zero = JacobianResidualBasis(s, z, hs, hz, torch.zeros_like(hs), torch.zeros_like(hz))
    for metric in ('raw', 'balanced'):
        for k in GLOBAL_RANKS:
            for a, b in zip(raw.reconstruct(3, metric, k), zero.reconstruct(3, metric, k)):
                torch.testing.assert_close(a, b, atol=2e-6, rtol=2e-6)
    ts, tz = torch.randn_like(hs)*3, torch.randn_like(hz)*3
    residual = JacobianResidualBasis(s, z, hs, hz, ts, tz)
    for metric in ('raw', 'balanced'):
        for i in range(19):
            for a, b in zip(residual.reconstruct(i, metric, 18), (hs[i], hz[i])):
                torch.testing.assert_close(a, b, atol=1e-6, rtol=1e-6)
    mean_s = (hs.double()-s.double()-ts.double()).mean(0)
    torch.testing.assert_close(residual.reconstruct(2, 'raw', 0)[0],
        (s.double()+ts[2].double()+mean_s).float(), atol=0, rtol=0)


def test_probability_direction_and_exact_linear_teacher():
    p = torch.nn.functional.one_hot(torch.tensor([0, 3, 5]), 20).float()
    d = hard_replacement_direction(p, 1, 8)
    assert d.sum() == 0 and d.square().sum() == 2
    assert torch.equal(hard_replacement_direction(p, 1, 3), torch.zeros_like(p))
    assert (p+.1*d).min() >= 0
    with pytest.raises(ValueError):hard_replacement_direction(p*.9+.1/20, 1, 8)
    torch.manual_seed(4)
    s, z = torch.randn(2, 4), torch.randn(2, 2, 3)
    ts, tz = torch.randn(19, 2, 4), torch.randn(19, 2, 2, 3)
    hs, hz = s.double()+ts.double(), z.double()+tz.double()
    b = JacobianResidualBasis(s, z, hs, hz, ts, tz)
    for metric in ('raw', 'balanced'):
        out = b.reconstruct(4, metric, 0)
        torch.testing.assert_close(out[0], hs[4], atol=0, rtol=0)
        torch.testing.assert_close(out[1], hz[4], atol=0, rtol=0)
