import numpy as np
import pytest
from fastglycan.structure_extent import structure_extent_diagnostics


def test_rigid_motion_and_pair_band_partition():
    rng=np.random.default_rng(19); y=rng.normal(size=(96,3))*15
    q,_=np.linalg.qr(rng.normal(size=(3,3)))
    if np.linalg.det(q)<0:q[:,0]*=-1
    d=structure_extent_diagnostics(y@q+123,y,np.arange(1,97))
    assert d['ca_rmsd']<1e-12 and d['fragment32_rmsd']<1e-12
    assert d['top5_sse_fraction'] is None
    assert d['distance_bands']['all']['mae']<1e-12
    assert sum(d['distance_bands'][k]['pairs'] for k in ['seq24_gt_lt15','seq24_gt_15_30','seq24_gt_ge30'])==sum(96-gap for gap in range(24,96))


def test_piecewise_rigid_displacement_preserves_local_shape_but_not_global():
    rng=np.random.default_rng(7);y=rng.normal(size=(64,3))*2;y[32:]+=np.array([20,0,0])
    x=y.copy();x[32:]+=np.array([0,15,0])
    d=structure_extent_diagnostics(x,y,np.arange(1,65))
    assert d['fragment32_rmsd']<1e-12
    assert d['ca_rmsd']>1 and d['distance_bands']['all']['mae']>1
    assert d['top5_sse_fraction']<.5


def test_isolated_outlier_and_reflection_are_not_hidden():
    rng=np.random.default_rng(11);y=rng.normal(size=(100,3))*3;x=y.copy();x[-1]+=[80,0,0]
    d=structure_extent_diagnostics(x,y,np.arange(100))
    assert d['top5_sse_fraction']>.9
    assert d['remainder95_rmsd_fixed_alignment']<d['ca_rmsd']/3
    mirror=y.copy();mirror[:,0]*=-1
    assert structure_extent_diagnostics(mirror,y,np.arange(100))['ca_rmsd']>1
    with pytest.raises(ValueError):structure_extent_diagnostics(x,y,np.zeros(100,dtype=int))
    with pytest.raises(ValueError):structure_extent_diagnostics(x*np.nan,y,np.arange(100))
