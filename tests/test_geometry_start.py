import numpy as np
import pytest
import torch

from fastglycan.articulated_output import ArticulatedOutput
from fastglycan.anchored_geometry import PoseVariables, JointObjective
from fastglycan.geometry_start import pose_variables_at_start
from fastglycan.local_projection_fit import fit_local_projection


def two_residues():
    names = ['N','CA','C','O','CB','OG1','CG2']
    ref = np.array([[-.525,1.363,0],[0,0,0],[1.526,0,0],[2.153,1.062,0],
                    [-.529,-.774,-1.205],[-1.7,-1.,-1.9],[.5,-1.7,-1.6]])
    bonds = [(0,1,1),(1,2,1),(2,3,2),(1,4,1),(4,5,1),(4,6,1)]
    variant = {'THR:'+','.join(names):dict(atom_names=names,bonds=bonds)}
    reference = np.concatenate([ref,ref+[3.8,0.,0.]])
    adapter = ArticulatedOutput(reference,names*2,np.repeat([1,2],7),'TT',variant).double()
    raw = torch.tensor(reference)
    raw[0] += torch.tensor([.35,-.25,.30]);raw[9] += torch.tensor([-.2,.1,.15])
    return adapter, raw


def test_parameter_start_preserves_chart_objective_and_replays_saved_fit():
    adapter,raw=two_residues();saved=raw.clone()
    fit=fit_local_projection(adapter,raw)
    cold=pose_variables_at_start(adapter,raw)
    warm=pose_variables_at_start(adapter,raw,fit.values)
    for (name,a),(other,b) in zip(cold.named_buffers(),warm.named_buffers(),strict=True):
        assert name==other and torch.equal(a,b)
    torch.testing.assert_close(warm(),fit.coordinates,atol=1e-10,rtol=0)
    torch.testing.assert_close(cold(),cold.initial,atol=1e-10,rtol=0)
    objective=JointObjective(raw,[[0,1,2,3],[7,8,9,10]],'TT',torch.empty((0,2),dtype=torch.long),torch.ones(14))
    # Identical q gives identical objective in the original chart, irrespective of start.
    with torch.no_grad():
        for p,v in zip(cold.variables,fit.values,strict=True):p.copy_(v)
    a,_=objective(cold(),cold.variables,1.)
    b,_=objective(warm(),warm.variables,1.)
    torch.testing.assert_close(a,b,atol=0,rtol=0)
    # Rebuilding around fitted coordinates WOULD move the anchor/chart; not equivalent.
    recharted=PoseVariables(adapter,fit.coordinates)
    assert any(not torch.equal(x.origin,y.origin) for x,y in zip(warm.groups,recharted.groups))
    assert torch.equal(objective.raw,raw) and torch.equal(raw,saved)
    with torch.no_grad():warm.variables[0].add_(1)
    assert not torch.equal(warm.variables[0],fit.values[0])


def test_invalid_starts_fail_without_silent_conversion():
    adapter,raw=two_residues();v=pose_variables_at_start(adapter,raw)
    values=tuple(p.detach().clone() for p in v.variables)
    for bad,match in [((), 'group count'), (tuple(x.float() for x in values),'dtype'),
                      (tuple(x*float('nan') for x in values),'nonfinite')]:
        with pytest.raises(ValueError,match=match):pose_variables_at_start(adapter,raw,bad)
