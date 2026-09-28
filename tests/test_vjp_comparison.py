import torch
from fastglycan.vjp_comparison import compare_fields,vector_metrics


def test_identity_can_hide_disagreement_and_zero_signal_is_not_pass():
    identity={'x':torch.tensor([1e8,0.],dtype=torch.double)}
    a={'x':identity['x']+torch.tensor([0.,1.],dtype=torch.double)}
    b={'x':identity['x']+torch.tensor([0.,2.],dtype=torch.double)}
    r=compare_fields(a,b,identity)
    assert r['total']['relative_l2_error']<1e-7
    assert r['without_explicit_identity']['total']['relative_l2_error']==.5
    z=vector_metrics(torch.zeros(2),torch.zeros(2))
    assert z['low_reference_norm'] and z['relative_l2_error'] is None and z['cosine'] is None
