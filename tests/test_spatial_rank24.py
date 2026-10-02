import torch
from fastglycan.spatial_rank24 import ChannelRank24Basis


def test_rank24_matches_direct_matrix_svd_and_full():
    torch.manual_seed(824);wt=torch.randn(30,30,3);target=torch.randn_like(wt);b=ChannelRank24Basis(wt,target);d=target.double()-wt.double();x=b.reconstruct('channel',24)
    for c in range(3):
        u,s,v=torch.linalg.svd(d[:,:,c]);expected=(wt[:,:,c].double()+(u[:,:24]*s[:24])@v[:24]).float()
        torch.testing.assert_close(x[:,:,c],expected,rtol=0,atol=2e-6)
    torch.testing.assert_close(b.reconstruct('channel','full'),target,rtol=0,atol=1e-6)
    e=b.evidence()['rows'][0];assert e['factor_elements']==2*30*24*3
