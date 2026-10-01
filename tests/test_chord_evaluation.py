import numpy as np
import pytest
from fastglycan.chord_evaluation import edit_backbone_metrics,fit_ca_frame


def test_source_copy_and_exact_target_use_same_nonlocal_frame():
    rng=np.random.default_rng(9);s=rng.normal(size=(12,3))*4;t=s.copy();t[:3,0]+=2
    local=np.arange(12)<3
    copy=edit_backbone_metrics(s,s,t,local);exact=edit_backbone_metrics(t,s,t,local)
    assert copy['local_target_rmsd']==pytest.approx(2)
    assert copy['local_response_cosine'] is None
    assert exact['local_target_rmsd']<1e-12 and exact['local_response_cosine']==pytest.approx(1)
    assert exact['nonlocal_motion']<1e-12
    r=np.linalg.qr(rng.normal(size=(3,3)))[0];r[:,0]*=np.linalg.det(r)
    moved=edit_backbone_metrics(t@r+10,s,t,local)
    for k in ['local_target_rmsd','nonlocal_target_rmsd','local_motion','ca_lddt']:
        assert moved[k]==pytest.approx(exact[k],abs=1e-12)


def test_frame_rejects_insufficient_support():
    with pytest.raises(ValueError):fit_ca_frame(np.zeros((2,3)),np.zeros((2,3)),np.ones(2,bool))
