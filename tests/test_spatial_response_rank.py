import pytest
import torch
from fastglycan.spatial_response_rank import SpatialResponseBasis


def test_full_reconstruction_and_zero_wt():
    torch.manual_seed(751)
    wt=torch.randn(9,9,3);target=torch.randn_like(wt);before=wt.clone()
    b=SpatialResponseBasis(wt,target)
    for v in ('channel','shared'):
        torch.testing.assert_close(b.reconstruct(v,'full'),target,rtol=0,atol=1e-6)
        assert torch.equal(b.reconstruct(v,0),wt)
    assert torch.equal(wt,before)


def test_shared_low_spatial_rank_asymmetric():
    torch.manual_seed(752)
    u=torch.randn(10,3,dtype=torch.double);v=torch.randn(10,3,dtype=torch.double)
    d=torch.einsum('ir,rsc,js->ijc',u,torch.randn(3,3,2,dtype=torch.double),v)
    assert not torch.allclose(d,d.transpose(0,1))
    b=SpatialResponseBasis(torch.zeros_like(d),d)
    for variant in ('channel','shared'):
        torch.testing.assert_close(b.reconstruct(variant,4),d,atol=1e-12,rtol=1e-12)


def test_channel_matches_independent_svd_and_energy():
    torch.manual_seed(753);d=torch.randn(12,12,3,dtype=torch.double)
    b=SpatialResponseBasis(torch.zeros_like(d),d);out=b.reconstruct('channel',4)
    for c in range(3):
        u,s,v=torch.linalg.svd(d[:,:,c])
        torch.testing.assert_close(out[:,:,c],(u[:,:4]*s[:4])@v[:4],rtol=1e-12,atol=1e-12)
    for row in b.evidence()['rows']:
        x=b.reconstruct(row['variant'],row['rank'])
        torch.testing.assert_close(torch.tensor(row['energy_retained']),1-(x-d).square().sum().float()/d.square().sum().float())
        r=row['effective_rank'];expected=2*12*r*3 if row['variant']=='channel' else 24*r+r*r*3
        assert row['factor_elements']==expected


def test_zero_response_and_invalid():
    x=torch.zeros(8,8,2);b=SpatialResponseBasis(x,x)
    assert all(r['energy_retained'] is None for r in b.evidence()['rows'])
    assert torch.equal(b.reconstruct('shared',8),x)
    with pytest.raises(ValueError):SpatialResponseBasis(x,x[:7])
    with pytest.raises(ValueError):b.reconstruct('channel',3)
