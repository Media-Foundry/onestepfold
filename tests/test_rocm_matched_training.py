import copy
import pytest
from fastglycan.rocm_matched_training import make_rocm_matched_lock,verify_rocm_matched_lock,WEIGHTS,BASE_LOCK_SHA256


def test_same_platform_pair_preserves_every_scientific_field_except_weight():
    base=dict(protocol='mini_folding_global_distance_training_v1',protocol_sha256='old',script_sha256='old',hashes={},
              weights={'global_distance':WEIGHTS['weak'],'coordinate':0.,'teacher':.025},engineering_groups=['short','long'],
              orders={'expanded':[{'group_id':'a','seed':600001}]},arms={'expanded':['a']},updates=2048,coordinate_replay_bound=.001)
    original=copy.deepcopy(base);backend=dict(source_lock_sha256=BASE_LOCK_SHA256,engineering_references={'short':{},'long':{}},training_updates=0,platform='DiamondHill/ROCm')
    locks={a:make_rocm_matched_lock(base,arm=a,hashes={},backend=backend,protocol_sha256='p',script_sha256='s') for a in WEIGHTS}
    assert base==original and 'arm' not in backend
    for a,lock in locks.items():
        assert lock['weights']['global_distance']==WEIGHTS[a]
        for k in ['orders','arms','updates','coordinate_replay_bound']:assert lock[k]==base[k]
        for k,v in [('updates',4096),('orders',{}),('coordinate_replay_bound',.01)]:
            bad=copy.deepcopy(lock);bad[k]=v
            with pytest.raises(ValueError):verify_rocm_matched_lock(bad,base)
        bad=copy.deepcopy(lock);bad['weights']['coordinate']=.01
        with pytest.raises(ValueError):verify_rocm_matched_lock(bad,base)
        bad=copy.deepcopy(lock);bad['backend']['training_updates']=1
        with pytest.raises(ValueError):verify_rocm_matched_lock(bad,base)


def test_pair_release_rejects_unmatched_preflights():
    from fastglycan.rocm_matched_training import validate_rocm_pair
    locks={a:dict(protocol='x',hashes={a:'file'},weights={'teacher':.2,'global_distance':w},
                  backend={'arm':a,'platform':'same'},engineering_groups=['s','l'],updates=2048) for a,w in WEIGHTS.items()}
    report=dict(complete=True,parameter_updates=0,selected_tensors=288,selected_elements=69777841,initial_sha256='same',
        cases=[dict(group_id=g,replay_exact=True,parameters_unchanged=True,selected_nonzero_gradients=288,coordinate_sha256=g,parts={'global_distance':1.}) for g in ['s','l']])
    reports={a:copy.deepcopy(report) for a in locks}
    assert validate_rocm_pair(locks,reports)['complete']
    reports['strong']['cases'][0]['coordinate_sha256']='changed'
    with pytest.raises(ValueError):validate_rocm_pair(locks,reports)
    reports['strong']=copy.deepcopy(report);reports['strong']['cases'][0]['parts']['global_distance']=2.
    with pytest.raises(ValueError):validate_rocm_pair(locks,reports)
    reports['strong']=copy.deepcopy(report);reports['strong']['parameter_updates']=1
    with pytest.raises(ValueError):validate_rocm_pair(locks,reports)
