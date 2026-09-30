"""Isolated integration contract for one global-distance folding continuation."""
import copy
from contextlib import contextmanager
from pathlib import Path
import numpy as np
import torch
from .folding_ablation import CONTROL_LOCK_SHA256
from .global_distance_supervision import global_ca_distance_loss
from .paired_teacher_protocol import sha256

GLOBAL_DISTANCE_WEIGHT = 0.03290655679814053
CALIBRATION_MANIFEST_SHA256 = 'c867845c2410e1001cae3c48573ed195e36c2ddad5adcb9564cc3ff3a38b21b5'
PROTOCOL = 'mini_folding_global_distance_training_v1'


def make_global_distance_lock(control, *, protocol_sha256, script_sha256, hashes, provenance):
    candidate=copy.deepcopy(control)
    candidate.update(protocol=PROTOCOL,protocol_sha256=protocol_sha256,script_sha256=script_sha256,
                     hashes=copy.deepcopy(hashes),global_distance=copy.deepcopy(provenance))
    candidate['arms']={'expanded':copy.deepcopy(control['arms']['expanded'])}
    candidate['orders']={'expanded':copy.deepcopy(control['orders']['expanded'])}
    candidate['weights']=dict(control['weights'],coordinate=0.,global_distance=GLOBAL_DISTANCE_WEIGHT)
    verify_global_distance_lock(candidate,control)
    return candidate


def verify_global_distance_lock(candidate,control):
    if candidate.get('protocol')!=PROTOCOL or control['weights']['coordinate']!=.01:
        raise ValueError('wrong experiment or control')
    if set(candidate)!=set(control)|{'global_distance'}:raise ValueError('contract fields changed')
    for key in control:
        if key not in {'protocol','protocol_sha256','script_sha256','hashes','arms','orders','weights'} and candidate[key]!=control[key]:
            raise ValueError('unapproved scientific change: '+key)
    if candidate['weights']!=dict(control['weights'],coordinate=0.,global_distance=GLOBAL_DISTANCE_WEIGHT):
        raise ValueError('unapproved weights')
    for key in ['arms','orders']:
        if candidate[key]!={'expanded':control[key]['expanded']}:raise ValueError('membership/order/noise changed')
    meta=candidate['global_distance']
    if meta['control_lock_sha256']!=CONTROL_LOCK_SHA256 or meta['calibration_manifest_sha256']!=CALIBRATION_MANIFEST_SHA256:
        raise ValueError('incorrect evidence binding')
    if set(meta['labels'])!=set(control['arms']['expanded']):raise ValueError('wrong label membership')


@contextmanager
def global_distance_training_hooks(trainer, supervision_module, lock, observer=None):
    """Patch only this process, restore even after failure; original inputs survive."""
    old_input=trainer.folding_training_input;old_parts=supervision_module.adapter_loss_parts
    cache={}
    def input_with_global(active_lock,group,seed,verified):
        values=old_input(active_lock,group,seed,verified)
        if group not in lock['arms']['expanded']:raise ValueError('non-TRAIN global labels')
        atoms=values[5]
        if group not in cache:
            entry=lock['global_distance']['labels'][group];path=Path(entry['path'])
            if sha256(path)!=entry['sha256']:raise ValueError('global label hash mismatch')
            bundle=torch.load(path,map_location='cpu',weights_only=False)
            if bundle['group_id']!=group:raise ValueError('global label group mismatch')
            for key,array in [('atom_names',atoms.atom_name),('residue_ids',atoms.res_id),('chain_ids',atoms.chain_id)]:
                if not np.array_equal(bundle[key],array):raise ValueError('global label atom order mismatch')
            cache[group]=bundle['labels']
        labels=dict(values[3],_global_distance=cache[group],_global_group=group)
        return (*values[:3],labels,*values[4:])
    def parts_with_global(x,labels,teacher=None,**kwargs):
        parts=old_parts(x,labels,teacher,**kwargs)
        parts['global_distance']=global_ca_distance_loss(x,labels['_global_distance'])
        if observer is not None:observer(x,labels,teacher,parts,old_parts,kwargs)
        return parts
    trainer.folding_training_input=input_with_global;supervision_module.adapter_loss_parts=parts_with_global
    try:yield
    finally:
        trainer.folding_training_input=old_input;supervision_module.adapter_loss_parts=old_parts
