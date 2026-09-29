import numpy as np
import pytest
import torch

from fastglycan.articulated_output import ArticulatedOutput
from fastglycan.output_reference_lengths import calibrate_output_reference


def fixture():
    names=['N','CA','C','O','CB','CG','CD']
    bonds=[(0,1,1),(1,2,1),(2,3,2),(1,4,1),(4,5,1),(5,6,1),(6,0,1)]
    variant={'PRO:'+','.join(names):dict(atom_names=names,bonds=bonds)}
    x=np.random.default_rng(19).normal(size=(21,3))
    parameters={'P':dict(supported=True,metrics={'ca_c':dict(median=1.525),'c_o':dict(median=1.234)})}
    return x,np.tile(names,3),np.repeat([1,2,3],7),variant,parameters


def test_output_lengths_ring_chirality_and_equivariance():
    x,n,r,v,p=fixture();y,records=calibrate_output_reference(x,n,r,'PPP',v,p)
    change=(r==2)&np.isin(n,['C','O'])
    assert np.array_equal(x[~change],y[~change]) and len(records)==1
    assert np.isclose(np.linalg.norm(y[9]-y[8]),1.525)
    assert np.isclose(np.linalg.norm(y[10]-y[9]),1.234)
    old=np.dot(np.cross(x[7]-x[8],x[9]-x[8]),x[11]-x[8])
    new=np.dot(np.cross(y[7]-y[8],y[9]-y[8]),y[11]-y[8]);assert old*new>0
    q,_=np.linalg.qr(np.random.default_rng(6).normal(size=(3,3)));q[:,-1]*=np.linalg.det(q)
    transformed,_=calibrate_output_reference(x@q+3,n,r,'PPP',v,p)
    np.testing.assert_allclose(transformed,y@q+3,rtol=0,atol=1e-13)
    replay,_=calibrate_output_reference(y,n,r,'PPP',v,p)
    np.testing.assert_allclose(replay,y,rtol=0,atol=1e-14)
    old_adapter=ArticulatedOutput(x,n,r,'PPP',v)
    adapter=ArticulatedOutput(y,n,r,'PPP',v)
    raw=torch.tensor(x,requires_grad=True)
    projected=adapter(raw)['coordinate'];old_projected=old_adapter(raw)['coordinate']
    torch.testing.assert_close(projected[~change],old_projected[~change],rtol=0,atol=1e-12)
    assert torch.autograd.gradcheck(lambda z:adapter(z)['coordinate'],(raw,))


def test_output_lengths_reject_unsupported_graph():
    x,n,r,v,p=fixture()
    key=next(iter(v));v[key]['bonds']=v[key]['bonds']+[(3,4,1)]
    with pytest.raises(ValueError,match='isolate'):calibrate_output_reference(x,n,r,'PPP',v,p)
