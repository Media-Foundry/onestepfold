import pytest
import scipy.linalg
import torch

from fastglycan.pair_readout import WeightedReadoutQR, aa_center, site_row_weight


def test_streamed_weighted_fit_matches_dense_svd_and_site_means():
    torch.manual_seed(83)
    xs, ys, weights = [], [], []
    stream = WeightedReadoutQR(5, 3, chunk_rows=7)
    for length, scale in ((2, .2), (5, 4.)):
        x, y = torch.randn(3 * length ** 2, 5, dtype=torch.float64), torch.randn(3 * length ** 2, 3, dtype=torch.float64)
        w = site_row_weight(length, scale, sites=2, candidates=3, channels=3)
        stream.add(x, y, w)
        xs.append(x * w ** .5); ys.append(y * w ** .5); weights.append(w)
    x, y = torch.cat(xs), torch.cat(ys)
    old = torch.randn(5, 3, dtype=torch.float64)
    fitted, audit = stream.solve(old, 1e-10)
    dense = torch.from_numpy(scipy.linalg.lstsq(x.numpy(), y.numpy(), lapack_driver='gelsd', cond=1e-10)[0])
    torch.testing.assert_close(fitted, dense, rtol=1e-10, atol=1e-10)
    assert audit['rows'] == len(x) and audit['rank'] == 5
    assert stream.objective(fitted) == pytest.approx(float((x @ fitted-y).square().sum()), abs=1e-12)
    assert weights[0] / weights[1] == pytest.approx(125.)


def test_rank_deficiency_preserves_original_unidentified_component():
    torch.manual_seed(9)
    x = torch.randn(101, 4, dtype=torch.float64); x[:, 3] = 0
    y = torch.randn(101, 2, dtype=torch.float64)
    old = torch.randn(4, 2, dtype=torch.float64)
    stream = WeightedReadoutQR(4, 2, 13); stream.add(x, y, .03)
    fitted, audit = stream.solve(old, 1e-6)
    assert audit['rank'] == 3
    torch.testing.assert_close(fitted[3], old[3], rtol=0, atol=1e-13)
    assert audit['objective_fit'] <= audit['objective_old']
    assert audit['projected_gradient_norm'] < 1e-12


def test_centered_layernorm_has_expected_null_direction_and_ignores_common_term():
    torch.manual_seed(19)
    x = torch.randn(19, 11, 8, dtype=torch.float64)
    ln = torch.nn.LayerNorm(8).double()
    with torch.no_grad():
        ln.weight.copy_(torch.linspace(.4, 2., 8)); ln.bias.copy_(torch.randn(8))
    h = ln(x).detach(); centered = aa_center(h)
    torch.testing.assert_close(centered @ ln.weight.reciprocal(), torch.zeros(19, 11, dtype=torch.float64), atol=2e-14, rtol=0)
    torch.testing.assert_close(aa_center(h + torch.randn(1, 11, 8)), centered, atol=1e-14, rtol=0)
    assert int((scipy.linalg.svdvals(centered.flatten(0, 1).numpy()) > 1e-10).sum()) == 7


def test_readout_orientation_and_bad_inputs():
    torch.manual_seed(7)
    head = torch.nn.Linear(8, 8, bias=False)
    h = torch.randn(5, 7, 8)
    assert torch.equal(head(h), torch.nn.functional.linear(h, head.weight))
    torch.testing.assert_close(head(h).double(), h.double() @ head.weight.double().T, rtol=1e-5, atol=1e-6)
    with pytest.raises(ValueError):
        site_row_weight(5, 0)
    with pytest.raises(ValueError):
        WeightedReadoutQR(8, 8).solve(torch.eye(8), 1e-6)
