import copy

import pytest
import torch

from fastglycan.anchored_tail import TailObjective
from fastglycan.calibrated_connection_objective import CalibratedConnectionObjective
from fastglycan.connection_audit import TOLERANCES


def fixture():
    raw = torch.tensor([[-1., 1., 0.], [0., 0., 0.], [1., 0., 0.], [1., -1., 0.],
        [1., 0., 1.], [2., 0., 1.], [3., 0., 1.], [3., -1., 1.],
        [3., 0., 2.], [2., 0., 2.], [1., 0., 2.], [1., 1., 2.],
        [1., 0., 3.], [0., 0., 3.], [-1., 0., 3.], [-1., -1., 3.]], dtype=torch.float64)
    args = (raw, torch.arange(16).reshape(4, 4), 'APAA',
            torch.empty((0, 2), dtype=torch.long), torch.ones(16, dtype=torch.float64))
    calibration = {'windows': {c: dict(supported=True, windows={
        k: {'q95': {'pooled': .5 * t}} for k, t in TOLERANCES.items()}) for c in ['Pro', 'other']}}
    return args, calibration


def test_old_onset_replays_original_value_gradient_and_shared_buffers():
    args, calibration = fixture()
    old = TailObjective(*args); new = CalibratedConnectionObjective(*args, calibration)
    for name, value in old.named_buffers():
        assert torch.equal(value, dict(new.named_buffers())[name])
    torch.manual_seed(12)
    x = (args[0] + .02 * torch.randn_like(args[0])).requires_grad_()
    values = [torch.zeros((4, 7), dtype=torch.float64, requires_grad=True)]
    a, ta = old(x, values, 10.); b, tb = new(x, values, 10.)
    assert torch.equal(a, b)
    ga = torch.autograd.grad(a, [x, *values], retain_graph=True)
    gb = torch.autograd.grad(b, [x, *values])
    for left, right in zip(ga, gb):
        torch.testing.assert_close(left, right, atol=1e-10, rtol=1e-12)
    for key in ta:
        assert torch.equal(ta[key], tb[key])


def test_only_trans_onsets_change_and_local_derivative_is_consistent():
    args, calibration = fixture()
    for category, factor in [('Pro', 3.), ('other', 2.)]:
        for term in TOLERANCES:
            calibration['windows'][category]['windows'][term]['q95']['pooled'] *= factor
    objective = CalibratedConnectionObjective(*args, calibration)
    assert objective.omega_target[:, 0].tolist() == [-1., 1., -1.]
    for i, t in enumerate(TOLERANCES.values()):
        torch.testing.assert_close(objective.connection_onsets[i], args[0].new_tensor([1.5*t, .5*t, t]))
    torch.manual_seed(15)
    x = (args[0] + .04 * torch.randn_like(args[0])).requires_grad_()
    direction = torch.randn_like(x); direction /= direction.norm()
    values = [torch.zeros((4, 7), dtype=torch.float64)]
    loss, terms = objective(x, values, 1.)
    ad = (torch.autograd.grad(loss, x)[0] * direction).sum()
    h = 1e-6
    fd = (objective(x.detach()+h*direction, values, 1.)[0] -
          objective(x.detach()-h*direction, values, 1.)[0])/(2*h)
    torch.testing.assert_close(ad, fd, atol=1e-4, rtol=1e-6)
    old_loss, old_terms = TailObjective(*args)(x.detach(), values, 1.)
    for key in ['anchor', 'repulsion', 'budget', 'tail']:
        assert torch.equal(terms[key], old_terms[key])
    assert loss <= old_loss
    bad = copy.deepcopy(calibration); bad['windows']['Pro']['windows']['omega']['q95']['pooled'] = float('nan')
    with pytest.raises(ValueError, match='invalid empirical'):
        CalibratedConnectionObjective(*args, bad)
