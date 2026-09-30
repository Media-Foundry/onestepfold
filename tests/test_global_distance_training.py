import copy
from types import SimpleNamespace
import numpy as np
import pytest
import torch
from fastglycan.global_distance_training import (make_global_distance_lock,verify_global_distance_lock,
    global_distance_training_hooks,GLOBAL_DISTANCE_WEIGHT,CALIBRATION_MANIFEST_SHA256,CONTROL_LOCK_SHA256)
from fastglycan.global_distance_supervision import build_global_ca_distance_labels
from fastglycan.paired_teacher_protocol import sha256


def test_locked_single_change_and_no_control_mutation():
    old=dict(protocol='old',protocol_sha256='x',script_sha256='x',hashes={},weights=dict(coordinate=.01,teacher=.2),
             arms=dict(expanded=['a']),orders=dict(expanded=[dict(group_id='a',seed=1)]),updates=2048,selected_names=['w'])
    snapshot=copy.deepcopy(old);meta=dict(control_lock_sha256=CONTROL_LOCK_SHA256,calibration_manifest_sha256=CALIBRATION_MANIFEST_SHA256,labels={'a':{}})
    new=make_global_distance_lock(old,protocol_sha256='new',script_sha256='new',hashes={},provenance=meta)
    assert old==snapshot and new['weights']['global_distance']==GLOBAL_DISTANCE_WEIGHT
    for field,value in [('updates',1024),('selected_names',['w','pf']),('unexpected',1)]:
        bad=copy.deepcopy(new);bad[field]=value
        with pytest.raises(ValueError):verify_global_distance_lock(bad,old)
    for key,value in [('teacher',0),('global_distance',.1),('coordinate',.01)]:
        bad=copy.deepcopy(new);bad['weights'][key]=value
        with pytest.raises(ValueError):verify_global_distance_lock(bad,old)
    bad=copy.deepcopy(new);bad['orders']['expanded'][0]['seed']=2
    with pytest.raises(ValueError):verify_global_distance_lock(bad,old)


def test_wrapper_identity_added_gradient_and_restoration(tmp_path):
    xyz=np.arange(90,dtype=float).reshape(30,3);names=np.array(['CA']*30);ids=np.arange(1,31);chains=np.array(['A']*30)
    mapping=dict(coordinates=xyz,mask=np.ones(30,dtype=bool),atom_names=names,residue_ids=ids,chain_ids=chains)
    labels=build_global_ca_distance_labels(mapping);file=tmp_path/'a.pt'
    torch.save(dict(group_id='a',labels=labels,atom_names=names,residue_ids=ids,chain_ids=chains),file)
    original_labels={'sentinel':object()};atoms=SimpleNamespace(atom_name=names,res_id=ids,chain_id=chains)
    values=(object(),object(),object(),original_labels,object(),atoms)
    trainer=SimpleNamespace(folding_training_input=lambda *args:values)
    old_parts=lambda x,labels,teacher,**kw:dict(old=x.square().mean())
    supervision=SimpleNamespace(adapter_loss_parts=old_parts);original_input=trainer.folding_training_input
    lock=dict(arms={'expanded':['a']},global_distance={'labels':{'a':dict(path=str(file),sha256=sha256(file))}})
    with pytest.raises(RuntimeError,match='intentional'):
        with global_distance_training_hooks(trainer,supervision,lock):
            out=trainer.folding_training_input(lock,'a',1,set());assert out[:3]==values[:3] and out[4:]==values[4:]
            assert out[3]['sentinel'] is original_labels['sentinel'] and '_global_distance' not in original_labels
            x=torch.tensor(xyz*.8,requires_grad=True);parts=supervision.adapter_loss_parts(x,out[3],None)
            assert torch.equal(parts['old'],old_parts(x,original_labels,None)['old'])
            g,=torch.autograd.grad(parts['global_distance'],x);assert torch.isfinite(g).all() and g.abs().max()>0
            raise RuntimeError('intentional')
    assert trainer.folding_training_input is original_input and supervision.adapter_loss_parts is old_parts
    atoms.res_id=ids[::-1]
    with pytest.raises(ValueError,match='atom order'):
        with global_distance_training_hooks(trainer,supervision,lock):trainer.folding_training_input(lock,'a',1,set())
