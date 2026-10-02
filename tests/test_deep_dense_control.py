import torch
from fastglycan.deep_dense_control import GlobalDenseControl


def test_full_field_readout_can_fit_all_seen_queries_and_wt_is_zero():
    torch.manual_seed(91);m=GlobalDenseControl(length=7,single_channels=12,pair_channels=4,rank=3)
    s=torch.randn(7,12);z=torch.randn(7,7,4);ids=list(range(1,20));target=torch.randn(19,7,7,4)
    with torch.no_grad():
        h,_=m.query_features(s,z,2,0,ids);design=torch.cat([h.double(),torch.ones(19,1)],1);assert torch.linalg.matrix_rank(design)==19
        c=torch.linalg.pinv(design)@target.double().flatten(1);m.dense.weight.copy_(c[:-1].T);m.dense.bias.copy_(c[-1])
    torch.testing.assert_close(m(s,z,2,0,ids),target,atol=2e-5,rtol=2e-5)
    assert torch.count_nonzero(m(s,z,2,0,[0]))==0
