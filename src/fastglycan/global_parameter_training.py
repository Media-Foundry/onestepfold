"""One parameter-budget-matched coefficient; old trial contracts stay immutable."""
import copy
import numpy as np
from .global_distance_training import GLOBAL_DISTANCE_WEIGHT

PROTOCOL='mini_folding_global_parameter_weight_v1'
PARAMETER_MATCHED_WEIGHT=0.1810138829332775
BASE_LOCK_SHA256='d266895a7c33f2a6ea4b7f6f492dd7f79bcbb1ec14cd5f2e3cb3088be12d5d27'
CALIBRATION_REPORT_SHA256='ce7157462408ab78a627bbc281424e694204b3c8ed673ae5b7b49e03d9e2c1a0'


def parameter_matched_coefficient(report):
    if not report.get('complete') or len(report['points'])!=16:
        raise ValueError('incomplete parameter diagnostic')
    initial=[p for p in report['points'] if p['stage']=='retained512']
    if len(initial)!=8 or len({p['group_id'] for p in initial})!=8:
        raise ValueError('need eight unique initial TRAIN points')
    ratios=[]
    for p in initial:
        if p['seed']!=600001 or p['statistics']['components']!=['old_coordinate','global_distance','rest']:
            raise ValueError('wrong noise or component order')
        g=np.asarray(p['statistics']['gram'],dtype=float)
        if g.shape!=(3,3) or not np.isfinite(g).all() or min(g[0,0],g[1,1])<=0:
            raise ValueError('invalid parameter gradient norms')
        ratios.append(float(np.sqrt(g[0,0]/g[1,1])))
    return GLOBAL_DISTANCE_WEIGHT*float(np.median(ratios))


def make_parameter_weight_lock(base, *, protocol_sha256, script_sha256, hashes, provenance):
    out=copy.deepcopy(base)
    out.update(protocol=PROTOCOL,protocol_sha256=protocol_sha256,script_sha256=script_sha256,
               hashes=copy.deepcopy(hashes),parameter_budget=copy.deepcopy(provenance))
    out['weights']=dict(base['weights'],global_distance=PARAMETER_MATCHED_WEIGHT)
    verify_parameter_weight_lock(out,base)
    return out


def verify_parameter_weight_lock(candidate,base):
    if base.get('protocol')!='mini_folding_global_distance_training_v1' or base['weights']['global_distance']!=GLOBAL_DISTANCE_WEIGHT:
        raise ValueError('wrong completed baseline')
    if candidate.get('protocol')!=PROTOCOL or set(candidate)!=set(base)|{'parameter_budget'}:
        raise ValueError('wrong experiment or fields')
    for key in base:
        if key not in {'protocol','protocol_sha256','script_sha256','hashes','weights'} and candidate[key]!=base[key]:
            raise ValueError('unapproved change: '+key)
    if candidate['weights']!=dict(base['weights'],global_distance=PARAMETER_MATCHED_WEIGHT):
        raise ValueError('only the fixed global coefficient may change')
    p=candidate['parameter_budget']
    if p['baseline_lock_sha256']!=BASE_LOCK_SHA256 or p['calibration_report_sha256']!=CALIBRATION_REPORT_SHA256 or p['coefficient']!=PARAMETER_MATCHED_WEIGHT:
        raise ValueError('wrong calibration/baseline provenance')
