import numpy as np
import pytest
from fastglycan.lddt_attribution import lddt_attribution
from fastglycan.scaling_metrics import lddt_observed


def test_unequal_neighbour_degrees_and_exact_cutoffs():
    y=np.array([[0,0,0],[1,0,0],[3,0,0],[14,0,0],[15,0,0],[50,0,0]],float)
    x=y.copy();x[2,0]+=.5;x[3,1]+=2;x[4,0]+=1
    residues=np.array([1,1,2,3,4,5]);r=lddt_attribution(x,y,residues)
    expected=[]
    for i in range(len(x)):
        terms=[]
        for j in range(len(x)):
            if residues[i]==residues[j] or np.linalg.norm(y[i]-y[j])>=15:continue
            err=abs(np.linalg.norm(x[i]-x[j])-np.linalg.norm(y[i]-y[j]))
            terms.append(sum(err<t for t in [.5,1,2,4])/4)
        expected.append(np.mean(terms) if terms else 0)
    np.testing.assert_allclose(r['per_atom'],expected,rtol=0,atol=1e-15)
    assert not r['valid'][-1]
    assert np.ptp(r['counts'][r['valid']])>0
    assert abs(r['score']-lddt_observed(x,y,residues)['score'])<1e-15
    for key in ['atom_contribution','pair_contribution','threshold_contribution']:
        assert abs(r[key].sum()-r['score'])<1e-15
    assert abs(r['pair_weights'].sum()-1)<1e-15
    a=r['pairs'][:,0]%2==0
    assert abs(r['pair_contribution'][a].sum()+r['pair_contribution'][~a].sum()-r['score'])<1e-15
    q,_=np.linalg.qr(np.random.default_rng(4).normal(size=(3,3)))
    # Avoid exact threshold boundaries in this separate rigid-invariance check.
    x[2,0]+=.03;x[4,0]+=.02
    transformed=lddt_attribution(x@q+7,y@q+7,residues)
    np.testing.assert_allclose(transformed['per_atom'],lddt_attribution(x,y,residues)['per_atom'],atol=1e-15)


def test_invalid_and_empty_neighbourhoods():
    with pytest.raises(ValueError,match='no evaluable'):lddt_attribution(np.zeros((1,3)),np.zeros((1,3)),[1])
    with pytest.raises(ValueError,match='invalid'):lddt_attribution(np.zeros((2,3)),np.zeros((1,3)),[1])
