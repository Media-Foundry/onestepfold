import copy
import numpy as np
import pytest
from fastglycan.global_parameter_training import (parameter_matched_coefficient,make_parameter_weight_lock,
    verify_parameter_weight_lock,PARAMETER_MATCHED_WEIGHT,GLOBAL_DISTANCE_WEIGHT,BASE_LOCK_SHA256,CALIBRATION_REPORT_SHA256)


def test_initial_only_calibration_and_wrong_sources():
    points=[]
    for stage in ['retained512','global_distance2048']:
        for i in range(8):points.append(dict(stage=stage,group_id=str(i),seed=600001,statistics=dict(components=['old_coordinate','global_distance','rest'],gram=np.diag([float((i+1)**2),1.,4.]).tolist())))
    report=dict(complete=True,points=points);assert parameter_matched_coefficient(report)==pytest.approx(4.5*GLOBAL_DISTANCE_WEIGHT)
    for p in points[8:]:p['statistics']['gram']=np.full((3,3),999).tolist()
    assert parameter_matched_coefficient(report)==pytest.approx(4.5*GLOBAL_DISTANCE_WEIGHT)
    bad=copy.deepcopy(report);bad['points'][0]['seed']=2
    with pytest.raises(ValueError):parameter_matched_coefficient(bad)
    bad=copy.deepcopy(report);bad['points'][0]['statistics']['gram'][1][1]=0
    with pytest.raises(ValueError):parameter_matched_coefficient(bad)


def test_exact_single_intervention_and_baseline_immutable():
    base=dict(protocol='mini_folding_global_distance_training_v1',protocol_sha256='a',script_sha256='b',hashes={},weights={'coordinate':0.,'global_distance':GLOBAL_DISTANCE_WEIGHT,'teacher':.2},orders={'expanded':[{'group_id':'a','seed':1}]},global_distance={'labels':{'a':'old'}},updates=2048)
    before=copy.deepcopy(base);meta=dict(baseline_lock_sha256=BASE_LOCK_SHA256,calibration_report_sha256=CALIBRATION_REPORT_SHA256,coefficient=PARAMETER_MATCHED_WEIGHT)
    out=make_parameter_weight_lock(base,protocol_sha256='c',script_sha256='d',hashes={},provenance=meta);assert base==before
    for field,value in [('updates',1024),('orders',{'expanded':[]}),('global_distance',{'labels':{}}),('extra',1)]:
        bad=copy.deepcopy(out);bad[field]=value
        with pytest.raises(ValueError):verify_parameter_weight_lock(bad,base)
    for key,value in [('teacher',.1),('coordinate',.01),('global_distance',1.)]:
        bad=copy.deepcopy(out);bad['weights'][key]=value
        with pytest.raises(ValueError):verify_parameter_weight_lock(bad,base)
