import pytest
import torch
from fastglycan.conditioning_swaps import swap_conditioning, ARMS, DecoderFeatureTrace


def test_all_routes_and_partition_no_mutation():
    torch.manual_seed(3);wt=(torch.randn(5,4),torch.randn(5,6),torch.randn(5,5,3));target=tuple(x+10 for x in wt)
    before=[x.clone() for x in (*wt,*target)];p=2
    arms={a:swap_conditioning(wt,target,p,a) for a in ARMS}
    for name,src in [('exact',target),('chem_only',wt)]:
        assert all(torch.equal(a,b) for a,b in zip(arms[name],src))
    assert torch.equal(arms['wt_trunk'][0],target[0]) and torch.equal(arms['wt_trunk'][2],wt[2])
    assert torch.equal(arms['target_trunk_only'][0],wt[0]) and torch.equal(arms['target_trunk_only'][2],target[2])
    m=torch.zeros(5,5,dtype=torch.bool);m[p]=True;m[:,p]=True
    for name,local,other in [('local_only',target,wt),('global_only',wt,target)]:
        c=arms[name];assert torch.equal(c[0],target[0]);assert torch.equal(c[1][p],local[1][p])
        assert torch.equal(c[1][torch.arange(5)!=p],other[1][torch.arange(5)!=p])
        assert torch.equal(c[2][m],local[2][m]) and torch.equal(c[2][~m],other[2][~m])
    assert all(torch.equal(a,b) for a,b in zip(before,(*wt,*target)))
    for name in ARMS:assert all(torch.equal(a,b) for a,b in zip(swap_conditioning(wt,wt,p,name),wt))


def test_contract_and_trace():
    wt=(torch.zeros(3,1),torch.zeros(3,2),torch.zeros(3,3,1))
    with pytest.raises(ValueError):swap_conditioning(wt,wt,-1,'exact')
    with pytest.raises(ValueError):swap_conditioning(wt,wt,1,'other')
    with pytest.raises(ValueError):swap_conditioning(wt,tuple(x[:2] for x in wt),1,'exact')
    f=DecoderFeatureTrace({'x':wt[0]});assert f['x'] is wt[0];assert f.get('absent') is None;assert f.reads=={'x','absent'}
