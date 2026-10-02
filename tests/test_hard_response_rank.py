import numpy as np
import pytest
from fastglycan.hard_response_rank import hard_response_spectrum,analyze_hard_response_site


def test_known_singular_values_and_gram_match_direct_svd():
    rng=np.random.default_rng(14);a=rng.normal(size=(19,3));b=rng.normal(size=(3,71));x=a@b
    r=hard_response_spectrum(x);sv=np.linalg.svd(x,compute_uv=False)
    np.testing.assert_allclose(r['singular_values'][:3],sv[:3],rtol=1e-12)
    assert r['cumulative_energy'][2]==pytest.approx(1) and r['rank99']<=3


def test_shared_shift_does_not_prove_low_rank_mutant_contrasts():
    x=np.ones((19,50))*100;x[:,:19]+=np.eye(19)
    assert hard_response_spectrum(x)['rank95']==1
    assert hard_response_spectrum(x,centered=True)['rank95']==18
    assert hard_response_spectrum(np.zeros((19,4)))['zero_signal']


def test_block_scale_sensitivity_and_diagonal_deduplication():
    rng=np.random.default_rng(7);e=dict(s_site=rng.normal(size=(20,4)),z_row=rng.normal(size=(20,6,3)),z_col=rng.normal(size=(20,6,3)))
    e['z_col'][:,2]=e['z_row'][:,2]
    result=analyze_hard_response_site(e,3,2)
    assert result['dimensions']==dict(s_site=4,z_row=18,z_col=18)
    assert result['spectra']['equal_block_energy']['wt_anchored']['energy']==pytest.approx(3)
    delta=e['z_row'][np.arange(20)!=3,2]-e['z_row'][3,2]
    difference=result['spectra']['raw_concat']['wt_anchored']['energy']-result['spectra']['deduplicated_diagonal']['wt_anchored']['energy']
    assert difference==pytest.approx((delta*delta).sum())
