import pytest
import torch
from fastglycan.response_coverage import SETS, EXCLUDED, coverage_exposures, coverage_stratum, response_polar_errors


def test_matching_and_exclusions():
    a,b=SETS.values()
    assert len(a)==len(b)==10 and len(set(a))==len(set(b))==10
    assert sorted(p for p,_ in a)==sorted(p for p,_ in b)
    assert len({p for p,_ in a})==8
    assert not set(EXCLUDED)&(set(a)|set(b))
    assert 6 not in {p for p,_ in a+b}
    assert coverage_exposures(32760)==[3276]*10
    assert sum(coverage_exposures(10923))==10923
    with pytest.raises(ValueError): coverage_exposures(32761)


def test_polar_identity_floors_and_oracle():
    t=torch.tensor([[1.,0.],[1.,0.],[1.,0.],[1e-5,0.],[0.,0.]],dtype=torch.float64)
    p=torch.tensor([[2.,0.],[0.,1.],[-1.,0.],[0.,1e-5],[1.,0.]],dtype=torch.float64)
    out=response_polar_errors(p,t)
    for r in out: assert r['nmse']==pytest.approx(r['expanded_identity_nmse'],abs=1e-12)
    assert out[0]['amplitude_ratio']==2 and out[0]['cosine']==1
    assert out[0]['oracle_scalar']==.5 and out[0]['oracle_scaled_nmse']==0
    assert out[1]['cosine']==0 and out[1]['oracle_scaled_nmse']==1
    assert out[2]['cosine']==-1 and out[2]['oracle_scalar']==-1
    assert out[3]['denominator_floor_active'] and out[3]['nmse']!=2
    assert out[4]['teacher_zero'] and out[4]['cosine'] is None
    zero=response_polar_errors(torch.zeros_like(t[:1]),t[:1])[0]
    assert zero['prediction_zero'] and zero['cosine'] is None and zero['nmse']==1


def test_strata_depend_on_arm_source_coverage():
    rows={i:{'sequence':['T']*200} for i in range(24)}
    for p,i in SETS['restricted']: rows[p]['sequence'][i]='A'
    for p,i in SETS['expanded'][6:]: rows[p]['sequence'][i]='L'
    rows[6]['sequence'][9]='L'
    assert coverage_stratum(rows,'restricted',6,9)=='unseen_protein_uncovered_source'
    assert coverage_stratum(rows,'expanded',6,9)=='unseen_protein_covered_source'
    assert coverage_stratum(rows,'expanded',4,24)=='seen_protein_uncovered_source'
    assert coverage_stratum(rows,'restricted',3,36)=='train'
