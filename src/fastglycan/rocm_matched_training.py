"""Same-platform replication of one global-distance weight contrast."""
import copy
from .global_parameter_training import BASE_LOCK_SHA256, PARAMETER_MATCHED_WEIGHT
from .global_distance_training import GLOBAL_DISTANCE_WEIGHT

PROTOCOL='mini_folding_rocm_matched_v1'
WEIGHTS={'weak':GLOBAL_DISTANCE_WEIGHT,'strong':PARAMETER_MATCHED_WEIGHT}


def make_rocm_matched_lock(base, *, arm, hashes, backend, protocol_sha256, script_sha256):
    if arm not in WEIGHTS:raise ValueError('only weak/strong matched comparison')
    out=copy.deepcopy(base)
    out.update(protocol=PROTOCOL,hashes=copy.deepcopy(hashes),backend=copy.deepcopy(backend),
               protocol_sha256=protocol_sha256,script_sha256=script_sha256)
    out['weights']=dict(base['weights'],global_distance=WEIGHTS[arm])
    out['backend']['arm']=arm
    verify_rocm_matched_lock(out,base)
    return out


def verify_rocm_matched_lock(candidate,base):
    if base.get('protocol')!='mini_folding_global_distance_training_v1' or base['weights']['global_distance']!=GLOBAL_DISTANCE_WEIGHT:
        raise ValueError('wrong source experiment')
    if candidate.get('protocol')!=PROTOCOL or set(candidate)!=set(base)|{'backend'}:
        raise ValueError('unapproved fields')
    for k in base:
        if k not in {'protocol','protocol_sha256','script_sha256','hashes','weights'} and candidate[k]!=base[k]:
            raise ValueError('scientific contract changed: '+k)
    meta=candidate['backend'];arm=meta['arm']
    if arm not in WEIGHTS or meta['source_lock_sha256']!=BASE_LOCK_SHA256:
        raise ValueError('wrong arm or provenance')
    if candidate['weights']!=dict(base['weights'],global_distance=WEIGHTS[arm]):
        raise ValueError('only predeclared global coefficient may change')
    if set(meta['engineering_references'])!=set(base['engineering_groups']):
        raise ValueError('need both original engineering cases')
    if meta['training_updates']!=0 or meta['platform']!='DiamondHill/ROCm':
        raise ValueError('references must be pre-training platform anchors')


def validate_rocm_pair(locks, reports):
    if set(locks)!={'weak','strong'} or set(reports)!=set(locks):raise ValueError('need both arms')
    a,b=locks['weak'],locks['strong']
    for key in set(a)|set(b):
        if key not in {'hashes','weights','backend'} and a.get(key)!=b.get(key):raise ValueError('unmatched field: '+key)
    if {k:v for k,v in a['backend'].items() if k!='arm'}!={k:v for k,v in b['backend'].items() if k!='arm'}:
        raise ValueError('unmatched platform/input references')
    if a['weights']!=dict(b['weights'],global_distance=WEIGHTS['weak']) or b['weights']['global_distance']!=WEIGHTS['strong']:
        raise ValueError('unmatched objectives')
    for arm,report in reports.items():
        if not report['complete'] or report['parameter_updates']!=0 or report['selected_tensors']!=288 or report['selected_elements']!=69777841:
            raise ValueError('incomplete preflight')
        if locks[arm]['backend']['arm']!=arm:raise ValueError('swapped arm')
        if [x['group_id'] for x in report['cases']]!=locks[arm]['engineering_groups']:raise ValueError('wrong engineering cases')
        for case in report['cases']:
            if not case['replay_exact'] or not case['parameters_unchanged'] or case['selected_nonzero_gradients']!=288:
                raise ValueError('preflight did not establish gradient/replay contract')
    if reports['weak']['initial_sha256']!=reports['strong']['initial_sha256']:raise ValueError('different initial parameters')
    for x,y in zip(reports['weak']['cases'],reports['strong']['cases']):
        if x['coordinate_sha256']!=y['coordinate_sha256'] or x['parts']!=y['parts']:
            raise ValueError('unmatched starting forward or objective components')
    return {'complete':True,'same_start':True,'same_engineering_coordinates':True,'same_unweighted_parts':True}
