import numpy as np
import pytest
import torch
from fastglycan.smooth_lddt_supervision import build_smooth_lddt_labels, smooth_lddt_loss


def test_width_against_closed_form_value_and_coordinate_derivative():
    target=torch.tensor([[0.,0.,0.],[2.,0.,0.],[float('nan')]*3],dtype=torch.float64)
    labels=build_smooth_lddt_labels(dict(coordinate=target,coordinate_mask=torch.tensor([True,True,False])),
        dict(atom_name=np.array(['CA']*3),residue_id=np.array([1,2,3])))
    x=target.clone();x[1,0]=4.2;x.requires_grad_()
    assert torch.equal(smooth_lddt_loss(x,labels),smooth_lddt_loss(x,labels,temperature=.1))
    for temperature in [.1,1.]:
        loss=smooth_lddt_loss(x,labels,temperature=temperature)
        p=1/(1+np.exp(-(np.array([.5,1.,2.,4.])-2.2)/temperature))
        assert float(loss.detach())==pytest.approx(1-p.mean(),abs=1e-14)
        gradient,=torch.autograd.grad(loss,x)
        slope=np.mean(p*(1-p))/temperature
        np.testing.assert_allclose(gradient.numpy(),[[-slope,0,0],[slope,0,0],[0,0,0]],atol=1e-14)


@pytest.mark.parametrize('temperature',[0.,-1.,float('inf'),float('nan')])
def test_invalid_width_rejected(temperature):
    with pytest.raises(ValueError,match='temperature'):
        smooth_lddt_loss(torch.ones(2,3),{},temperature=temperature)
