import numpy as np
import pytest
from fastglycan.independent_geometry_eval import continuation_screen,experimental_quality


def complete_rows():
    groups=[str(i) for i in range(32)]
    rows=[dict(group_id=g,seed=s,raw_joint_pass=False,tail_joint_pass=True,quality={'raw':{'all_atom_lddt':.8},'tail':{'all_atom_lddt':.801}}) for g in groups for s in (300007,300017,300023)]
    return groups,rows


def test_missing_seed_cannot_be_dropped_from_quality_gate():
    groups,rows=complete_rows();ok=continuation_screen(rows,groups)
    assert ok['continuation_screen'] and ok['all3_tail_joint_pass']==32
    fail=continuation_screen(rows[:-1],groups)
    assert fail['instances']==96 and fail['tail_joint_pass']==95
    assert not fail['quality_screen'] and not fail['continuation_screen']
    assert len(fail['missing_quality'])==1


def test_raw_pass_regression_blocks_otherwise_good_mean():
    groups,rows=complete_rows();rows[0].update(raw_joint_pass=True,tail_joint_pass=False)
    result=continuation_screen(rows,groups)
    assert result['quality_screen'] and result['raw_pass_regressions']==1
    assert not result['geometry_screen']
    with pytest.raises(ValueError):continuation_screen(rows+[rows[0]],groups)


def test_experimental_mask_and_rigid_quality():
    pytest.importorskip('tmtools')
    xyz=np.array([[0,0,0],[3,1,0],[6,0,1],[8,2,3],[20,20,20]],float)
    mapping=dict(coordinates=xyz,mask=np.array([1,1,1,1,0],bool),residue_ids=np.array([1,2,3,4,4]),atom_names=np.array(['CA']*4+['CB']))
    predicted=xyz+10;predicted[-1]=10000
    result=experimental_quality(predicted,mapping,'AAAA')
    assert result['all_atom_lddt']==1 and result['ca_lddt']==1
    assert result['ca_rmsd']<1e-10 and result['observed_atoms']==4
