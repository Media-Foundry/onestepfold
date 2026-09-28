import torch
from fastglycan.near_hard_diagnostics import original_logit_directions,fd_measurement,summarize_directions


def test_small_signal_cannot_be_reported_as_informative_pass():
    rows=[fd_measurement(1e-8,1.+2*h*1e-8,1.,h,probability_delta_norm=1e-9,coordinate_delta_norm=1e-8) for h in [.3,.1]]
    result=summarize_directions([rows],finite=True,gradient_norm=1e-8,repeat_max_abs=0)
    assert result['original_passed'] and not result['informative_passed']
    assert result['label']=='pass_low_signal_or_absolute_tolerance_assisted'


def test_nonzero_well_resolved_derivative_and_original_failure():
    good=[fd_measurement(.01,1.+2*h*.01001,1.,h,probability_delta_norm=.01,coordinate_delta_norm=.1) for h in [.3,.1]]
    assert summarize_directions([good],finite=True,gradient_norm=.1,repeat_max_abs=0)['informative_passed']
    bad=[fd_measurement(.01,1.+2*h*.02,1.,h,probability_delta_norm=.01,coordinate_delta_norm=.1) for h in [.3,.1]]
    assert not summarize_directions([bad],finite=True,gradient_norm=.1,repeat_max_abs=0)['original_passed']
    assert not summarize_directions([good],finite=True,gradient_norm=.1,repeat_max_abs=1e-8)['original_passed']


def test_logit_directions_retain_original_gauge_and_scale():
    q=torch.zeros(12,20)
    first=list(original_logit_directions(q));repeat=list(original_logit_directions(q))
    for a,b in zip(first,repeat):
        assert torch.equal(a,b)
        torch.testing.assert_close(a.norm(),torch.tensor(1.))
        torch.testing.assert_close(a.sum(-1),torch.zeros(12),atol=1e-7,rtol=0)
