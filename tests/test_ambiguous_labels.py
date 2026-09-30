import numpy as np
from fastglycan.ambiguous_labels import align_ambiguous_gt


def fixture():
    names=np.array(['N','CA','C','O','CB','CG','OD1','OD2','N','CA','C','O','CB'])
    res=np.array([1]*8+[2]*5)
    y=np.random.default_rng(4).normal(size=(13,3))*2
    return dict(coordinates=y,atom_names=names,residue_ids=res,chain_ids=np.array(['A']*13),mask=np.ones(13,dtype=bool))


def test_exact_swapped_label_recovers_without_changing_backbone_or_mask():
    m=fixture();x=m['coordinates'].copy();x[[6,7]]=x[[7,6]]
    result=align_ambiguous_gt(x,m,'DA')
    assert result['records'][0]['swapped']
    assert np.array_equal(result['coordinates'],x)
    assert np.array_equal(m['coordinates'][:6],result['coordinates'][:6])


def test_partial_observation_is_not_permuted_and_rigid_rotation_is_irrelevant():
    m=fixture();x=m['coordinates'].copy();x[[6,7]]=x[[7,6]]
    rotation=np.array([[0.,-1.,0.],[1.,0.,0.],[0.,0.,1.]])
    a=align_ambiguous_gt(x@rotation+10,m,'DA')
    assert a['records'][0]['swapped']
    m['mask'][7]=False;m['coordinates'][7]=np.nan
    b=align_ambiguous_gt(x,m,'DA');assert not b['records'][0]['swapped']
    assert np.array_equal(b['permutation'],np.arange(13))


def test_aromatic_swaps_are_coupled():
    names=np.array(['N','CA','C','O','CB','CG','CD1','CD2','CE1','CE2','CZ','CA','N','C'])
    y=np.random.default_rng(7).normal(size=(14,3))
    m=dict(coordinates=y,atom_names=names,residue_ids=np.array([1]*11+[2]*3),chain_ids=np.array(['A']*14),mask=np.ones(14,dtype=bool))
    x=y.copy();x[[6,7,8,9]]=x[[7,6,9,8]]
    a=align_ambiguous_gt(x,m,'FA')
    assert a['records'][0]['swapped'] and np.array_equal(a['coordinates'],x)
