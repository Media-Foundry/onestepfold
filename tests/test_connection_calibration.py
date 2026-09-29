import numpy as np
import pytest

from fastglycan.connection_calibration import equal_protein_quantile, fit_connection_windows, coverage_by_protein
from fastglycan.connection_audit import TOLERANCES


def test_protein_weighting_does_not_count_long_chains_as_more_proteins():
    assert equal_protein_quantile([0.] * 100 + [10.], ['long'] * 100 + ['short'], .75) == 10.
    assert np.quantile([0.] * 100 + [10.], .75) == 0.
    with pytest.raises(ValueError):
        equal_protein_quantile([float('nan')], ['a'], .95)


def test_holdout_and_rare_class_cannot_define_windows():
    rows = [dict(role='calibration', branch='trans', next_class='other', group_id=str(i % 8),
                 **{term + '_residual': i / 100 for term in TOLERANCES}) for i in range(100)]
    windows = fit_connection_windows(rows)
    assert windows['other']['supported'] and not windows['Pro']['supported']
    assert windows['other']['windows']['cn']['q95']['pooled'] == pytest.approx(.9405)
    with pytest.raises(ValueError):
        fit_connection_windows(rows + [rows[0] | {'role': 'held_out'}])
    assert not fit_connection_windows([r | {'branch': 'cis'} for r in rows])['other']['supported']


def test_coverage_retains_protein_denominators_and_reproducible_intervals():
    rows = [dict(group_id='a', cn_residual=0.) for _ in range(10)] + [dict(group_id='b', cn_residual=2.)]
    report = coverage_by_protein(rows, 'cn', 1.)
    assert report['pooled'] == pytest.approx(10 / 11)
    assert report['equal_protein'] == .5 and report['proteins'] == 2
    assert report == coverage_by_protein(rows, 'cn', 1.)
    assert report['pooled_ci95'] == [0., 1.]
