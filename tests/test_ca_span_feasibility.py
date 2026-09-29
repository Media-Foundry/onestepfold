import itertools
import numpy as np
import pytest

from fastglycan.ca_span_feasibility import (
    peptide_span_squared, ca_span_bounds, ca_motion_lower_bound)


def test_span_identity_against_constructed_cartesian_quadruplets():
    rng = np.random.default_rng(730)
    a, b, c = rng.uniform(1.2, 1.7, (3, 500))
    u, v, omega = rng.uniform(-.8, .5, 500), rng.uniform(-.9, .3, 500), rng.uniform(-np.pi, np.pi, 500)
    ca = np.stack([a*u, a*np.sqrt(1-u*u), np.zeros(500)], axis=-1)
    next_ca = np.stack([b-c*v, c*np.sqrt(1-v*v)*np.cos(omega), c*np.sqrt(1-v*v)*np.sin(omega)], axis=-1)
    np.testing.assert_allclose(peptide_span_squared(a, b, c, u, v, np.cos(omega)),
        ((next_ca-ca)**2).sum(-1), rtol=2e-14, atol=1e-14)


@pytest.mark.parametrize('sign', [-1, 1])
def test_certified_bounds_attained_at_corners_and_enclose_random_states(sign):
    widths = dict(cn=.03, angle_c=.04, angle_n=.04, omega=.1)
    bounds = ca_span_bounds(1.525, 1.458, 1.329, widths, sign)
    q = [1-.1**2/2, 1] if sign > 0 else [-1, -1+.1**2/2]
    corners = np.array(list(itertools.product([1.299, 1.359], [-.4873, -.4073], [-.5603, -.4803], q)))
    values = np.sqrt(peptide_span_squared(1.525, corners[:, 0], 1.458, *corners[:, 1:].T))
    np.testing.assert_allclose([values.min(), values.max()], [bounds['lower'], bounds['upper']], atol=1e-14)
    rng = np.random.default_rng(52)
    points = rng.uniform(corners.min(0), corners.max(0), (1000, 4))
    sampled = np.sqrt(peptide_span_squared(1.525, points[:, 0], 1.458, *points[:, 1:].T))
    assert (sampled >= bounds['lower']).all() and (sampled <= bounds['upper']).all()
    assert bounds['db_lower'] > 0 and bounds['du_upper'] < 0 and bounds['dv_upper'] < 0


def test_branch_counterfactual_and_disjoint_motion_bound():
    widths = dict(cn=.03, angle_c=.04, angle_n=.04, omega=.1)
    cis = ca_span_bounds(1.525, 1.458, 1.329, widths, 1)
    trans = ca_span_bounds(1.525, 1.458, 1.329, widths, -1)
    distance = np.sqrt(peptide_span_squared(1.525, 1.329, 1.458, -.4473, -.5203, -1))
    assert distance > cis['upper'] and trans['lower'] <= distance <= trans['upper']
    assert ca_motion_lower_bound([1., 1.]) == pytest.approx(np.sqrt(.5/3))
    assert ca_motion_lower_bound([1., 0., 1.]) == pytest.approx(.5)
    assert ca_motion_lower_bound([0., 0.]) == 0


def test_invalid_domain_is_not_reported_as_feasible():
    w = dict(cn=.03, angle_c=.04, angle_n=.04, omega=.1)
    with pytest.raises(ValueError): ca_span_bounds(0, 1.45, 1.329, w, -1)
    with pytest.raises(ValueError): ca_span_bounds(1.52, 1.45, 1.329, dict(w, omega=2), -1)
    with pytest.raises(ValueError): ca_span_bounds(1.52, 1.45, 1.329, dict(w, angle_n=.9), -1)
    with pytest.raises(ValueError): ca_span_bounds(1.52, 1.45, 1.329, w, 0)
    with pytest.raises(ValueError): ca_motion_lower_bound([-1])
