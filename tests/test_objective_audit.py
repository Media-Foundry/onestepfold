import numpy as np
import pytest
from fastglycan.objective_audit import score_decomposition,noise_audit,rank_correlation


def test_shift_and_candidate_error_are_separate():
    d=score_decomposition([100,101,102],[102,101,100])
    assert d['mean_error']==0
    assert d['centered_error']==pytest.approx(8/3)
    shifted=score_decomposition([0,1,2],[4,5,6])
    assert shifted['mean_error']==16 and shifted['centered_error']==0
    assert rank_correlation([0,1,2],[4,5,6])==1


def test_noise_shift_is_not_ranking_failure():
    d=noise_audit(np.array([[1,2,3],[1,2,3],[11,12,13],[11,12,13]]))
    assert d['old_new_rho']==1 and d['centered_noise_mse']==0
    assert d['old_select_new_regret']==0
    assert rank_correlation([1,1,1],[1,2,3]) is None
