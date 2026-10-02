import torch
from fastglycan.deep_response_student import DeepResponseStudent
from fastglycan.response_readouts import FreeNodeReadout,NonlinearResponseReadout,oracle_matrix_target


def test_free_hidden_starts_at_same_response_and_updates_hidden_and_heads():
    torch.manual_seed(79);s=torch.randn(6,9);z=torch.randn(6,6,4);base=DeepResponseStudent(size='large',single_channels=9,pair_channels=4,rank=2)
    base.v.weight.data.normal_(std=.02);model=FreeNodeReadout(base,s,z,1,0);args=(s,z,1,0,list(range(20)))
    torch.testing.assert_close(model(*args),base(*args),atol=0,rtol=0)
    model(*args).square().sum().backward();assert model.hidden.grad.abs().sum()>0 and model.u.weight.grad.abs().sum()>0 and model.v.weight.grad.abs().sum()>0
    assert model.hidden.grad[0].abs().sum()==0


def test_shared_readouts_support_lengths_zero_wt_and_nonlinear_content():
    for kind in ['pair','channel']:
        model=NonlinearResponseReadout(kind,single_channels=9,pair_channels=4,rank=2,readout_width=16)
        model.readout[-1].weight.data.normal_(std=.1)
        for length in [5,7]:
            s=torch.randn(length,9);z=torch.randn(length,length,4,requires_grad=True);x=model(s,z,1,0,[0,1,2]);assert x.shape==(3,length,length,4)
            assert x[0].count_nonzero()==0;x[1:].square().mean().backward();assert z.grad.abs().sum()>0
            if kind=='channel':assert torch.linalg.matrix_rank(x[1,:,:,0],atol=1e-4,rtol=0)<=2
            else:assert torch.linalg.matrix_rank(x[1,:,:,0])==length


def test_oracle_matrix_target_has_expected_rank_and_residual():
    torch.manual_seed(3);x=torch.randn(3,8,8,4);y=oracle_matrix_target(x,3)
    assert (torch.linalg.matrix_rank(y.permute(0,3,1,2),atol=2e-6,rtol=0)<=3).all()
    sv=torch.linalg.svdvals(x.double().permute(0,3,1,2));torch.testing.assert_close((x.double()-y.double()).square().sum(),sv[...,3:].square().sum(),rtol=1e-6,atol=1e-6)
