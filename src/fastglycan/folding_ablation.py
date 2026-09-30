"""Single-variable contract for the experimental-GT coordinate-loss ablation."""
import copy

PROTOCOL = 'mini_folding_coordinate_ablation_v1'
CONTROL_LOCK_SHA256 = '1ec3f1c13fec5ea12981f9efef37957fec264c1bc0e659c9fc4a98519384c357'
CONTROL_TERMINAL_SHA256 = '3e6c6e1b1a493215adba31df1106efa9e30218c5f92846f4ca4d2e3a6fd17b09'
ADMIN_FIELDS = {'protocol', 'protocol_sha256', 'script_sha256', 'hashes'}


def make_coordinate_ablation_lock(control, *, protocol_sha256, script_sha256, hashes, provenance):
    candidate = copy.deepcopy(control)
    candidate.update(protocol=PROTOCOL, protocol_sha256=protocol_sha256,
                     script_sha256=script_sha256, hashes=copy.deepcopy(hashes),
                     ablation=copy.deepcopy(provenance))
    candidate['arms'] = {'expanded': copy.deepcopy(control['arms']['expanded'])}
    candidate['orders'] = {'expanded': copy.deepcopy(control['orders']['expanded'])}
    candidate['weights']['coordinate'] = 0.0
    verify_coordinate_ablation_lock(candidate, control)
    return candidate


def verify_coordinate_ablation_lock(candidate, control):
    if control['weights']['coordinate'] != .01 or candidate.get('protocol') != PROTOCOL:
        raise ValueError('wrong control objective or experiment')
    if set(candidate) != set(control) | {'ablation'}:
        raise ValueError('missing or extra contract fields')
    for key in control:
        if key in ADMIN_FIELDS or key in {'weights', 'arms', 'orders'}:
            continue
        if candidate[key] != control[key]:
            raise ValueError('unapproved scientific change: '+key)
    expected_weights = dict(control['weights'], coordinate=0.0)
    if candidate['weights'] != expected_weights:
        raise ValueError('only coordinate weight may change')
    for key in ['arms', 'orders']:
        if candidate[key] != {'expanded': control[key]['expanded']}:
            raise ValueError('changed TRAIN423 membership/order/noise')
    if candidate['ablation'].get('control_lock_sha256') != CONTROL_LOCK_SHA256:
        raise ValueError('wrong control provenance')
