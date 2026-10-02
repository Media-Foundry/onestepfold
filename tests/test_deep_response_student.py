import torch
from fastglycan.factor_student import FactorStudent,expand_pair_factors
from fastglycan.deep_response_student import DeepResponseStudent,fit_gate,transfer_gate


def model_inputs():
    torch.manual_seed(51)
    return torch.randn(7,12),torch.randn(7,7,4),2,0,[0,1,2]


def test_small_bias_matches_old_network_and_wt_is_zero():
    args=model_inputs();torch.manual_seed(1);old=FactorStudent(12,4,3,128)
    torch.manual_seed(1);new=DeepResponseStudent(single_channels=12,pair_channels=4,rank=3)
    torch.testing.assert_close(new(*args),expand_pair_factors(*old(*args)),rtol=0,atol=0)
    new.v.weight.data.normal_();assert torch.count_nonzero(new(*args)[0])==0


def test_edge_content_gradient_and_matched_parameter_count():
    args=model_inputs();bias=DeepResponseStudent(single_channels=12,pair_channels=4,rank=3)
    content=DeepResponseStudent(content=True,single_channels=12,pair_channels=4,rank=3)
    assert abs(sum(p.numel() for p in bias.parameters())-sum(p.numel() for p in content.parameters()))<1024
    content.v.weight.data.normal_();content(*args).square().mean().backward()
    assert all(block.edge[1].weight.grad.abs().sum()>0 for block in content.blocks)


def test_oracle_site_only_does_not_read_other_target_rows():
    args=model_inputs();model=DeepResponseStudent(input_mode='site',input_channels=9,single_channels=12,pair_channels=4,rank=3)
    model.v.weight.data.normal_();wt=torch.randn(7,9);target=torch.randn(3,7,9)
    first=model(*args,wt,target);changed=target.clone();changed[:,:2]+=10;changed[:,3:]-=20
    torch.testing.assert_close(first,model(*args,wt,changed),rtol=0,atol=0)


def test_dense_is_unfactorized_and_zero_wt():
    args=model_inputs();model=DeepResponseStudent(output='dense',length=7,single_channels=12,pair_channels=4,rank=3)
    model.dense.weight.data.normal_();out=model(*args)
    assert out.shape==(3,7,7,4) and torch.count_nonzero(out[0])==0
    assert torch.linalg.matrix_rank(out[1,:,:,0])==7


def test_two_seed_gates_do_not_accept_one_seed_or_low_signal_centering():
    a=dict(mean_nmse=.09,centered_nmse=.9);b=dict(mean_nmse=.08,centered_nmse=.7)
    assert fit_gate([a,b]) and not fit_gate([a])
    assert not transfer_gate([a,b])
