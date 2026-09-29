import numpy as np
import pytest
import torch
from fastglycan.connected_output import ConnectedOutput, phase


def fixture():
    names=['N','CA','C','O','CB']
    ref=np.array([[-.525,1.363,0],[0,0,0],[1.526,0,0],[2.153,1.062,0],[-.529,-.774,-1.205]])
    variants={'ALA:'+','.join(names):dict(atom_names=names,bonds=[(0,1,1),(1,2,1),(2,3,2),(1,4,1)])}
    model=ConnectedOutput(np.tile(ref,(3,1)),names*3,np.repeat([1,2,3],5),'AAA',variants)
    raw=torch.tensor(np.random.default_rng(41).normal(size=(15,3)),requires_grad=True)
    return model,raw


def test_connected_chemistry_idempotence_and_proper_equivariance():
    model,raw=fixture();y=model(raw)
    torch.testing.assert_close(model(y),y,atol=1e-10,rtol=1e-10)
    q,_=torch.linalg.qr(torch.randn(3,3,dtype=torch.float64));q[:,-1]*=torch.linalg.det(q)
    torch.testing.assert_close(model(raw@q+4),y@q+4,atol=1e-10,rtol=1e-10)
    for i in range(3):
        n,ca,c,o,cb=y[5*i:5*i+5]
        assert torch.dot(torch.linalg.cross(n-ca,c-ca),cb-ca)>0
        for a,b,expected in [(n,ca,model.geometry[i,0]),(ca,c,model.geometry[i,1]),(c,o,model.geometry[i,3])]:
            torch.testing.assert_close((a-b).norm(),expected)
        if i<2:
            nn,nca=y[5*i+5:5*i+7]
            assert float((c-nn).norm().detach())==pytest.approx(1.329)
            co,si=phase(ca,c,nn,nca)
            assert float(co.detach())==pytest.approx(-1.)
            assert abs(float(si.detach()))<1e-10
            co,si=phase(nn,ca,c,o)
            assert float(co.detach())==pytest.approx(-1.)
            assert abs(float(si.detach()))<1e-10
    assert torch.equal(model(raw),model(raw))


def test_composed_output_derivative_and_degenerate_rejection():
    model,raw=fixture()
    assert torch.autograd.gradcheck(model,(raw,),atol=1e-5,rtol=1e-4)
    with pytest.raises(ValueError,match='degenerate'):
        model(torch.zeros_like(raw))


def test_terminal_oxt_preserves_inventory_and_internal_oxt_rejects():
    names=['N','CA','C','O','CB','OXT']
    reference=np.array([[-.525,1.363,0],[0,0,0],[1.526,0,0],[2.153,1.062,0],[-.529,-.774,-1.205],[2.1,-1.1,0]])
    variant={'ALA:'+','.join(names):dict(atom_names=names,bonds=[(0,1,1),(1,2,1),(2,3,2),(1,4,1),(2,5,1)])}
    model=ConnectedOutput(reference,names,np.ones(6,dtype=int),'A',variant)
    raw=torch.tensor(reference)
    torch.testing.assert_close(model(raw),raw,atol=1e-10,rtol=1e-10)
    with pytest.raises(ValueError,match='terminal'):
        ConnectedOutput(reference,names,np.ones(6,dtype=int),'AA',variant)
