import numpy as np
import pytest
import torch

from fastglycan.articulated_output import ArticulatedOutput
from fastglycan.articulated_reference import geometry_invariants
from fastglycan.local_projection_fit import fit_local_projection


def chemistry():
    names = ['N', 'CA', 'C', 'O', 'CB', 'OG1', 'CG2']
    reference = np.array([[-.525, 1.363, 0], [0, 0, 0], [1.526, 0, 0],
                          [2.153, 1.062, 0], [-.529, -.774, -1.205],
                          [-1.7, -1., -1.9], [.5, -1.7, -1.6]])
    bonds = [(0, 1, 1), (1, 2, 1), (2, 3, 2), (1, 4, 1), (4, 5, 1), (4, 6, 1)]
    variants = {'THR:' + ','.join(names): dict(atom_names=names, bonds=bonds)}
    adapter = ArticulatedOutput(reference, names, np.ones(7, dtype=int), 'T', variants)
    return adapter, torch.tensor(reference), bonds


def test_known_feasible_input_stays_put_and_input_graph_is_not_claimed():
    adapter, raw, _ = chemistry()
    raw.requires_grad_(True)
    before = raw.detach().clone()
    result = fit_local_projection(adapter, raw)
    torch.testing.assert_close(result.coordinates, raw, atol=1e-10, rtol=0)
    assert result.final_mse < 1e-20
    assert not result.coordinates.requires_grad and raw.grad is None
    torch.testing.assert_close(raw.detach(), before)


def test_distorted_pose_anchor_can_be_fitted_without_changing_local_chemistry():
    adapter, reference, bonds = chemistry()
    raw = reference.clone()
    raw[0] += torch.tensor([.35, -.25, .30])
    result = fit_local_projection(adapter, raw)
    assert result.improved and result.final_mse < .7 * result.initial_mse
    lengths, cosines = geometry_invariants(reference.numpy(), bonds)
    after = geometry_invariants(result.coordinates.numpy(), bonds)
    np.testing.assert_allclose(after[0], lengths, atol=1e-10)
    np.testing.assert_allclose(after[1], cosines, atol=1e-10)
    for centre, a, b, c in [(1, 0, 2, 4), (4, 1, 5, 6)]:
        signs = [torch.dot(torch.linalg.cross(x[a] - x[centre], x[b] - x[centre]),
                           x[c] - x[centre]) for x in [reference, result.coordinates]]
        assert signs[0] * signs[1] > 0
    # Global proper pose changes do not change the nearest-coordinate problem.
    rotation = torch.tensor([[0., -1., 0.], [1., 0., 0.], [0., 0., 1.]], dtype=torch.float64)
    shifted = fit_local_projection(adapter, raw @ rotation + 7)
    torch.testing.assert_close(shifted.coordinates, result.coordinates @ rotation + 7, atol=1e-7, rtol=0)


def test_invalid_or_degenerate_inputs_are_not_silently_repaired():
    adapter, raw, _ = chemistry()
    with pytest.raises(ValueError, match='Nonfinite'):
        fit_local_projection(adapter, raw * float('nan'))
    with pytest.raises(ValueError, match='degenerate'):
        fit_local_projection(adapter, torch.zeros_like(raw))
    with pytest.raises(ValueError, match='budget'):
        fit_local_projection(adapter, raw, max_iter=0)
