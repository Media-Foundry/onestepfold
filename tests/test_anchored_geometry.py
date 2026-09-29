import numpy as np
import torch
from fastglycan.articulated_output import ArticulatedOutput
from fastglycan.articulated_reference import geometry_invariants
from fastglycan.anchored_geometry import PoseVariables,JointObjective,solve


def chemistry():
    names=['N','CA','C','O','CB','OG1','CG2']
    reference=np.array([[-.525,1.363,0],[0,0,0],[1.526,0,0],[2.153,1.062,0],[-.529,-.774,-1.205],[-1.7,-1.,-1.9],[.5,-1.7,-1.6]])
    bonds=[(0,1,1),(1,2,1),(2,3,2),(1,4,1),(4,5,1),(4,6,1)]
    variant={'THR:'+','.join(names):dict(atom_names=names,bonds=bonds)}
    adapter=ArticulatedOutput(reference,names,np.ones(7,dtype=int),'T',variant)
    return adapter,torch.tensor(reference),bonds


def test_pose_zero_equivariance_and_local_chemical_invariants():
    adapter,raw,bonds=chemistry();v=PoseVariables(adapter,raw)
    torch.testing.assert_close(v(),adapter(raw)['coordinate'])
    q=tuple(torch.linspace(-.3,.4,p.numel(),dtype=torch.float64).reshape_as(p) for p in v.variables)
    x=v.coordinates(q)
    before=geometry_invariants(raw.numpy(),bonds);after=geometry_invariants(x.detach().numpy(),bonds)
    np.testing.assert_allclose(before[0],after[0],atol=1e-12);np.testing.assert_allclose(before[1],after[1],atol=1e-12)
    for center,a,b,c in [(1,0,2,4),(4,1,5,6)]:
        def volume(z):return torch.dot(torch.linalg.cross(z[a]-z[center],z[b]-z[center]),z[c]-z[center])
        assert volume(raw)*volume(x)>0
    rotation,_=torch.linalg.qr(torch.tensor(np.random.default_rng(9).normal(size=(3,3))));rotation[:,-1]*=torch.det(rotation)
    shifted=PoseVariables(adapter,raw@rotation+4)
    torch.testing.assert_close(shifted.coordinates(q),x@rotation+4,atol=1e-10,rtol=1e-10)
    assert torch.autograd.gradcheck(lambda *q:v.coordinates(q),tuple(p.detach().requires_grad_(True) for p in v.variables),atol=1e-5,rtol=1e-4)


def test_feasible_input_remains_stationary_and_solver_does_not_claim_raw_gradient():
    adapter,raw,_=chemistry();v=PoseVariables(adapter,raw.clone().requires_grad_(True))
    objective=JointObjective(raw,[[0,1,2,3]],'T',torch.empty((0,2),dtype=torch.long),torch.ones(len(raw)))
    result,history=solve(v,objective)
    torch.testing.assert_close(result,raw,atol=1e-10,rtol=1e-10)
    assert all(row['loss']<1e-20 for row in history)
    assert not v.initial.requires_grad and not objective.raw.requires_grad


def test_joint_connection_objective_backpropagates_to_both_residues():
    adapter,reference,_=chemistry()
    names=['N','CA','C','O','CB','OG1','CG2']
    bonds=[(0,1,1),(1,2,1),(2,3,2),(1,4,1),(4,5,1),(4,6,1)]
    variants={'THR:'+','.join(names):dict(atom_names=names,bonds=bonds)}
    ref=np.tile(reference.numpy(),(2,1))
    raw=torch.tensor(ref);raw[7:]+=torch.tensor([3.7,.5,.4])
    adapter=ArticulatedOutput(ref,names*2,np.repeat([1,2],7),'TT',variants)
    variables=PoseVariables(adapter,raw)
    objective=JointObjective(raw,[[0,1,2,3],[7,8,9,10]],'TT',torch.tensor([[0,12],[4,13]]),torch.ones(14)*1.7)
    q=tuple((p.detach()+.01).requires_grad_(True) for p in variables.variables)
    def loss(*q):return objective(variables.coordinates(q),q,1.)[0]
    assert torch.autograd.gradcheck(loss,q,atol=1e-4,rtol=1e-4)
    grad=torch.autograd.grad(loss(*q),q)[0]
    assert bool((grad[:,:6].norm(dim=-1)>0).all())
