"""One matched continuation contrast: two repeated noises versus one per exposure."""
import copy

DIVERSE_SEED_OFFSET=1800000


def diverse_exposure_order(base_order):
    if len(base_order)!=8192:raise ValueError('fixed 8192-exposure budget required')
    return [dict(row,seed=DIVERSE_SEED_OFFSET+i) for i,row in enumerate(base_order,1)]


def make_noise_diversity_lock(base, *, arm, cache, cache_files, cache_digests, hashes, protocol_sha256, script_sha256):
    if arm not in ['fixed','diverse']:raise ValueError('unapproved arm')
    if base['weights']['global_distance']!=0.03290655679814053 or base['training_seeds']!=[600001,600011]:
        raise ValueError('weak objective and original probe noises required')
    out=copy.deepcopy(base)
    out.update(protocol='mini_noise_diversity_v1',cache=str(cache),cache_files=copy.deepcopy(cache_files),
        cache_lock_sha256=cache_digests['lock.json'],cache_manifest_sha256=cache_digests['artifact_manifest.json'],
        cache_audit_sha256=cache_digests['audit.json'],hashes=copy.deepcopy(hashes),
        protocol_sha256=protocol_sha256,script_sha256=script_sha256,
        noise_diversity=dict(arm=arm,source='native public S2, regenerated on ROCm for BOTH arms',
            held_noises=[920003,920009,920021,920033],no_gt_or_weight_changes=True))
    if arm=='diverse':out['orders']={'expanded':diverse_exposure_order(base['orders']['expanded'])}
    if set(out['arms'])!={'expanded'}:raise ValueError('unexpected training arm')
    for x,y in zip(out['orders']['expanded'],base['orders']['expanded']):
        if {k:v for k,v in x.items() if k!='seed'}!={k:v for k,v in y.items() if k!='seed'}:
            raise ValueError('sequence exposure order changed')
    return out
