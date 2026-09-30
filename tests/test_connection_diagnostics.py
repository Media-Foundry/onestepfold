import copy
import numpy as np
import pytest

from fastglycan.connection_audit import TOLERANCES
from fastglycan.connection_diagnostics import describe_connection_distribution


@pytest.mark.parametrize('invalid', [None, 'branch', 'nonfinite'])
def test_connection_distribution(invalid):
    # Following residues P, A, P: trans-Pro, trans-other, unsupported cis-Pro.
    branch=np.array([-1, -1, 1])
    measurement=dict(nearest_omega_sign=branch, omega_sign=branch.copy(),
        residuals={k:np.array([.02, .2, .8]) for k in TOLERANCES})
    calibration=dict(not_acceptance_thresholds=True, calibration_proteins=32,
        windows={kind:dict(supported=True,edges=100,windows={k:{q:dict(equal_protein=v)
            for q,v in [('q95',.05),('q99',.1)]} for k in TOLERANCES}) for kind in ['Pro','other']})
    if invalid:
        if invalid=='branch':measurement['omega_sign'][0]=1
        else:measurement['residuals']['cn'][0]=np.nan
        with pytest.raises(ValueError):describe_connection_distribution(measurement,'APAP',calibration)
        return
    original=copy.deepcopy(measurement)
    result=describe_connection_distribution(measurement,'APAP',calibration)
    pro=result['groups']['Pro_trans'];other=result['groups']['other_trans'];cis=result['groups']['Pro_cis']
    assert pro['terms']['cn']['reference_bands']['q99']['count']==0
    assert other['terms']['cn']['reference_bands']['q99']['left_residue_positions']==[2]
    assert other['terms']['cn']['reference_bands']['q99']['fraction']==1
    assert cis['left_residue_positions']==[3] and not cis['calibration_supported']
    assert 'reference_bands' not in cis['terms']['omega']
    assert result['groups']['other_cis']['edges']==0
    assert result['not_acceptance_thresholds'] and 'pass' not in result
    for k in TOLERANCES:np.testing.assert_array_equal(measurement['residuals'][k],original['residuals'][k])
