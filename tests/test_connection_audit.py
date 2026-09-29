import numpy as np
import pytest
import torch

from fastglycan.connection_audit import normal_dihedral,measure_connections,summarize_residuals
from fastglycan.anchored_geometry import JointObjective


def test_signed_phase_cis_trans_and_rigid_transform():
    angles=np.array([0.,.4,-.8,np.pi])
    points=np.array([[[1,0,0],[0,0,0],[0,0,1],[np.cos(t),np.sin(t),1]] for t in angles])
    np.testing.assert_allclose(normal_dihedral(points),angles,atol=1e-14)
    rotation=np.array([[0,-1,0],[1,0,0],[0,0,1.]])
    np.testing.assert_allclose(normal_dihedral(points@rotation+4),angles,atol=1e-14)
    with pytest.raises(ValueError,match='degenerate'):normal_dihedral(np.zeros((4,3)))


def test_independent_residuals_and_wrong_fixed_branch():
    x=np.array([[-1.,1.,0],[0,0,0],[1.5,0,0],[2.,-1.,.2],
                [2.,1.3,0],[3.4,1.7,.4],[4.,2.8,0],[3.4,3.8,.1]])
    anchors=np.arange(8).reshape(2,4)
    a=measure_connections(x,anchors,'AP')
    objective=JointObjective(torch.tensor(x),anchors,'AP',torch.empty((0,2),dtype=torch.long),torch.ones(8))
    for key,value in objective.residuals(torch.tensor(x)).items():
        np.testing.assert_allclose(a['residuals'][key],value.numpy(),atol=1e-14)
    other=measure_connections(x,anchors,'AP',-a['nearest_omega_sign'])
    np.testing.assert_allclose(a['residuals']['omega']**2+other['residuals']['omega']**2,4,atol=1e-14)
    # Proline-specific target is applied to the following residue, not the preceding one.
    plain=measure_connections(x,anchors,'PA')
    np.testing.assert_allclose(plain['residuals']['cn']-a['residuals']['cn'],.012,atol=1e-14)


def test_optimization_activity_is_distinct_from_hard_rejection():
    result=summarize_residuals({'angle_c':np.array([0.,.01,.03,.05])})['angle_c']
    assert result['active']==2 and result['rejected']==1
    assert result['mean_penalty']==pytest.approx((.5**2+1.5**2)/4)
