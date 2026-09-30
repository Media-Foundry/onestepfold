import copy
from pathlib import Path
import pytest
from fastglycan.evaluation_reuse import evaluation_prediction_source, expected_evaluation_calls


def test_explicit_reuse_supports_validation_without_changing_legacy_behavior():
    rows=[dict(group_id='a',role='train'),dict(group_id='b',role='validation')]
    lock=dict(cache='/cache',models=['native_s1','native_s2','candidate'],checkpoints={'candidate':{}},train_seeds=[1,2],validation_seeds=[3,4])
    assert expected_evaluation_calls(lock,rows)==dict(native=6,candidate=4)
    assert evaluation_prediction_source(lock,rows[0],'native_s2',1)==Path('/cache/examples/a/s2_seed1.npy')
    assert evaluation_prediction_source(lock,rows[1],'native_s2',3) is None
    reused=copy.deepcopy(lock)
    reused['reuse_models']={m:dict(root='/previous',model=m,roles=['train','validation']) for m in ['native_s1','native_s2','retained','expanded']}
    reused['models']=['native_s1','native_s2','retained','expanded','candidate']
    assert expected_evaluation_calls(reused,rows)==dict(native=0,candidate=4)
    assert evaluation_prediction_source(reused,rows[1],'native_s2',3)==Path('/previous/b/native_s2_seed3.npy')
    bad=copy.deepcopy(reused);bad['reuse_models']['retained'].pop('roles')
    with pytest.raises(ValueError,match='checkpoint'):expected_evaluation_calls(bad,rows)
    bad=copy.deepcopy(reused);bad['reuse_models']['expanded']['roles']=['test']
    with pytest.raises(ValueError,match='roles'):expected_evaluation_calls(bad,rows)
    bad=copy.deepcopy(reused);bad['models'].append('candidate')
    with pytest.raises(ValueError,match='duplicate'):expected_evaluation_calls(bad,rows)
    bad=copy.deepcopy(reused);bad['validation_seeds']=[3,3]
    with pytest.raises(ValueError,match='noises'):expected_evaluation_calls(bad,rows)
