import numpy as np
import pytest

from fastglycan.backbone_reference_calibration import measure_backbone_local_geometry, fit_backbone_reference, BACKBONE_METRICS


def test_backbone_geometry_known_angles_and_rigid_motion():
    x = np.array([[0.,1.,0.],[0.,0.,0.],[2.,0.,0.],[2.,0.,3.]])
    values = measure_backbone_local_geometry(x)
    np.testing.assert_allclose([values[k] for k in BACKBONE_METRICS], [1,2,3,90,90])
    rotation = np.array([[0.,1.,0.],[0.,0.,1.],[1.,0.,0.]])
    other = measure_backbone_local_geometry(x @ rotation + [5,-3,8])
    for k in BACKBONE_METRICS: np.testing.assert_allclose(values[k],other[k])
    with pytest.raises(ValueError): measure_backbone_local_geometry(np.zeros((4,3)))


def test_reference_split_support_and_terminal_exclusion():
    rows = [dict(role='calibration', amino_acid='A', terminal=False, group_id=str(i%8),
        **{name:float(i) for name in BACKBONE_METRICS}) for i in range(32)]
    rows.append(dict(rows[0], terminal=True, n_ca=1e9))
    fit = fit_backbone_reference(rows)
    assert fit['A']['supported'] and fit['A']['residues'] == 32
    assert fit['A']['metrics']['n_ca']['median'] == 15.5
    assert not fit['C']['supported'] and fit['C']['metrics']['ca_c'] is None
    with pytest.raises(ValueError): fit_backbone_reference(rows+[dict(rows[0],role='held_out')])
    assert not fit_backbone_reference([dict(r,group_id='single') for r in rows])['A']['supported']
