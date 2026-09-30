import copy
import pytest
from fastglycan.folding_ablation import (
    CONTROL_LOCK_SHA256, make_coordinate_ablation_lock, verify_coordinate_ablation_lock,
)


def test_ablation_rejects_hidden_changes_and_does_not_mutate_control():
    control = dict(protocol='prior', protocol_sha256='old', script_sha256='old', hashes={},
        weights=dict(coordinate=.01, smooth_lddt=1., teacher=.025, clash=.001),
        arms=dict(train128=['a'], expanded=['a','b']),
        orders=dict(train128=[dict(group_id='a',seed=1)], expanded=[dict(group_id='a',seed=1),dict(group_id='b',seed=2)]),
        learning_rate=dict(peak=1e-5,terminal=1e-6), updates=2048, selected_names=['diffusion.weight'],
        rows=[dict(group_id='a',role='train'),dict(group_id='v',role='validation')])
    untouched = copy.deepcopy(control)
    good = make_coordinate_ablation_lock(control, protocol_sha256='new', script_sha256='new',
        hashes={'newroot/file':'same-content'}, provenance={'control_lock_sha256':CONTROL_LOCK_SHA256})
    assert control == untouched and good['weights']['coordinate']==0
    verify_coordinate_ablation_lock(good, control)
    variants=[]
    for key,value in [('updates',1024),('selected_names',['diffusion.weight','trunk.weight']),('unexpected',True)]:
        bad=copy.deepcopy(good);bad[key]=value;variants.append(bad)
    bad=copy.deepcopy(good);bad['weights']['teacher']=0;variants.append(bad)
    bad=copy.deepcopy(good);bad['orders']['expanded'][0]['seed']=3;variants.append(bad)
    bad=copy.deepcopy(good);bad['arms']['expanded'].append('v');variants.append(bad)
    bad=copy.deepcopy(good);bad['learning_rate']['peak']=2e-5;variants.append(bad)
    bad=copy.deepcopy(good);bad.pop('rows');variants.append(bad)
    for bad in variants:
        with pytest.raises(ValueError):verify_coordinate_ablation_lock(bad,control)
    good['orders']['expanded'][0]['seed']=9
    assert control==untouched
