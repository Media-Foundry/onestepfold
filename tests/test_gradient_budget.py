import numpy as np
import pytest
from fastglycan.gradient_budget import coordinate_gradient_budget


def test_signed_cancellation_and_ca_restriction():
    a=np.array([[1.,0,0],[0,2,0]])
    b=np.array([[-1.,0,0],[0,0,0]])
    out=coordinate_gradient_budget({'a':a,'b':b},{'a':1.,'b':1.},np.array([True,False]))
    assert out['spaces']['all']['total_norm']==2
    assert out['spaces']['ca']['total_norm']==0
    assert out['spaces']['ca']['terms']['a']['ratio_to_total_norm'] is None
    assert out['spaces']['ca']['terms']['a']['cosine_with_rest']==-1
    assert sum(v['signed_projection_on_total'] for v in out['spaces']['all']['terms'].values())==2


def test_weights_and_direct_gradient_sum():
    rng=np.random.default_rng(8);g={k:rng.normal(size=(10,3)) for k in ['a','b','c']};w={'a':.01,'b':2.,'c':0.}
    mask=np.arange(10)%3==0;out=coordinate_gradient_budget(g,w,mask)
    total=sum(w[k]*g[k] for k in w)
    for name,sel in [('all',slice(None)),('ca',mask)]:
        s=out['spaces'][name];assert s['total_norm']==pytest.approx(np.linalg.norm(total[sel]))
        assert s['terms']['c']['raw_norm']>0 and s['terms']['c']['weighted_norm']==0
        assert s['terms']['c']['cosine_with_rest'] is None
        for i,k in enumerate(out['keys']):
            for j,l in enumerate(out['keys']):assert s['raw_gram'][i][j]==pytest.approx(np.sum(g[k][sel]*g[l][sel]))


def test_invalid_inputs_and_empty_ca():
    g={'a':np.ones((2,3))}
    assert coordinate_gradient_budget(g,{'a':1},np.zeros(2,dtype=bool))['spaces']['ca']['cancellation_ratio'] is None
    for w,m in [({'b':1},np.ones(2,dtype=bool)),({'a':-1},np.ones(2,dtype=bool)),({'a':1},np.ones(2))]:
        with pytest.raises(ValueError):coordinate_gradient_budget(g,w,m)
    with pytest.raises(ValueError):coordinate_gradient_budget({'a':np.full((2,3),np.nan)},{'a':1},np.ones(2,dtype=bool))
