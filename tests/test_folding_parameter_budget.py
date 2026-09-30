import pytest
import torch
from fastglycan.folding_parameter_budget import parameter_gradient_grams


def test_streamed_gram_matches_linear_model_vjps_and_signed_sums():
    x=torch.tensor([2.,-1.,3.],requires_grad=True);y=torch.tensor([.5,-.7],requires_grad=True)
    a=x[0]+2*x[1]-y[0];b=-2*a+y[1];c=(x*x).sum()+y.sum()
    vectors={k:torch.autograd.grad(v,(x,y),retain_graph=True) for k,v in [('old',a),('global',b),('rest',c)]}
    r=parameter_gradient_grams(vectors,['x','y'],chunk=2)
    m=torch.stack([torch.cat(g).double() for g in vectors.values()]);assert torch.equal(torch.tensor(r['gram']), (m@m.T).float())
    assert r['gram'][0][1]<0 and r['elements']==5
    direct=torch.cat(torch.autograd.grad(b+c,(x,y))).double();w=torch.tensor([0.,1.,1.],dtype=torch.float64)
    assert float(w@torch.tensor(r['gram'],dtype=torch.float64)@w)==pytest.approx(float(direct@direct))


def test_zero_gradient_and_validation():
    z=torch.zeros(7);r=parameter_gradient_grams({'a':[z],'b':[z]},['p'],chunk=3);assert r['gram']==[[0.,0.],[0.,0.]]
    with pytest.raises(ValueError):parameter_gradient_grams({'a':[z],'b':[]},['p'])
    with pytest.raises(ValueError):parameter_gradient_grams({'a':[torch.tensor([float('nan')])]},['p'])
    with pytest.raises(ValueError):parameter_gradient_grams({'a':[z,z]},['p','p'])
