import numpy as np
import pytest

from fastglycan.reference_editor_metrics import distance_response_summary, paired_parent_interval


def test_centered_response_does_not_reward_common_offset_copy():
    target = np.array([[1., 2.], [2., 4.], [3., 6.]])
    reference = np.array([.3, .4])
    exact = distance_response_summary(target, target, reference)
    assert exact['centered_response_nmse'] == 0
    shared = np.broadcast_to(target.mean(0), target.shape)
    result = distance_response_summary(target, shared, reference)
    assert result['mean_response_distance_rmse'] == pytest.approx(0)
    assert result['centered_response_nmse'] == pytest.approx(1)
    translated = distance_response_summary(target, target+10, reference)
    assert translated['centered_response_nmse'] == pytest.approx(0)
    assert translated['mean_response_distance_rmse'] == pytest.approx(10)


def test_bootstrap_pairs_parents_and_rejects_mismatched_membership():
    a = [dict(parent=i, rho=x) for i, x in enumerate([1., 0., .5])]
    b = [dict(parent=i, rho=x-.2) for i, x in enumerate([1., 0., .5])]
    result = paired_parent_interval(a, b, 'rho')
    assert result['parents'] == 3
    assert result['mean'] == pytest.approx(.2)
    assert result['interval'] == pytest.approx([.2, .2])
    with pytest.raises(ValueError, match='sets differ'):
        paired_parent_interval(a, b[:2], 'rho')
