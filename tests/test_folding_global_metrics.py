import copy
import pytest
from fastglycan.folding_global_metrics import summarize_global_structure


def test_global_structure_keeps_noise_pairing_and_upper_error_tail():
    lock=dict(rows=[dict(group_id=g,role='validation') for g in 'abc'],
        cohorts={'observed_validation32':list('abc')},models=['reference','candidate'],
        train_seeds=[1,2],validation_seeds=[3,4],contrasts=[['candidate','reference']],
        bootstrap=dict(seed=11,replicates=100))
    values={'a':([2,4],[1,7]),'b':([4,4],[2,2]),'c':([1,1],[1,1])}
    records=[dict(group_id=g,seed=s,model=m,ca_aligned_rmsd=value)
        for g,pair in values.items() for m,noise_values in zip(lock['models'],pair)
        for s,value in zip(lock['validation_seeds'],noise_values)]
    result=summarize_global_structure(records,lock);c=result['summary']['observed_validation32']
    assert c['models']['candidate']['mean']==pytest.approx(7/3)
    assert c['models']['candidate']['worst5_mean']==4
    p,=c['contrasts'];assert p['mean']==pytest.approx(-1/3)
    assert p['worst5_mean']==1 and p['increased_proteins']==1
    a=result['paired'][0];assert a['delta_rmsd']==1
    assert [v['delta_rmsd'] for v in a['per_noise']]==[-1,3]
    assert 'Positive candidate − reference differences mean deterioration' in result['markdown']
    assert '|1/3|' in result['markdown']
    for malformed in [records[:-1],records+[records[0]]]:
        with pytest.raises(ValueError,match='denominator'):summarize_global_structure(malformed,lock)
    bad=copy.deepcopy(records);bad[0]['ca_aligned_rmsd']=float('nan')
    with pytest.raises(ValueError,match='finite'):summarize_global_structure(bad,lock)
    badlock=copy.deepcopy(lock);badlock['cohorts']['observed_validation32'].append('a')
    with pytest.raises(ValueError,match='partition'):summarize_global_structure(records,badlock)
