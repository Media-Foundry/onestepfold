"""Guard completion, paired identities, weighting and pre-update loss axes."""
import copy
import hashlib
import json

import pytest

from fastglycan.placement_results import (
    placement_geometry_transitions, placement_trajectory,
    require_placement_completion, selection_contributions)


def completion_case(tmp_path):
    train=tmp_path/'train';verify=tmp_path/'verify';train.mkdir();verify.mkdir()
    lock=dict(arms=['late','early'],seeds=[272001,272003],checkpoints=[0,32,128],gradient_budget=128,
              run_order=[['late',272001],['early',272001],['late',272003],['early',272003]])
    def write(path,value):path.write_text(json.dumps(value))
    write(train/'training_lock.json',lock)
    digest=hashlib.sha256((train/'training_lock.json').read_bytes()).hexdigest()
    good=dict(status='complete',exit_code=0)
    names=['tests','parallel_gate','gate_verification','ledger_verification']+[
        f'{kind}_{arm}_{seed}' for kind in ['train','score'] for arm,seed in lock['run_order']]
    state=dict(complete=True,phase='complete',lock_sha256=digest,jobs={n:dict(good) for n in names})
    write(train/'controller.json',state)
    verify_state=dict(complete=True,phase='complete',jobs={f'{a}_{s}':dict(good) for a,s in lock['run_order']})
    write(verify/'controller.json',verify_state);write(verify/'verification_lock.json',dict(training_lock_sha256=digest))
    for name in ['ledger_verification.json','parallel_gate_verification.json']:
        write(train/name,dict(complete=True,lock_sha256=digest,bitwise_steps=[1,2]))
    return train,verify,lock,state,verify_state


def test_training_completion_does_not_replace_independent_replay(tmp_path):
    train,verify,lock,state,verified=completion_case(tmp_path)
    assert require_placement_completion(train,verify)==lock
    verified.update(complete=False,phase='waiting_for_original_training')
    (verify/'controller.json').write_text(json.dumps(verified))
    with pytest.raises(ValueError,match='independent native'):
        require_placement_completion(train,verify)


def test_complete_flag_cannot_hide_missing_or_failed_run(tmp_path):
    train,verify,_,state,_=completion_case(tmp_path)
    state['jobs']['train_early_272003']['exit_code']=1
    (train/'controller.json').write_text(json.dumps(state))
    with pytest.raises(AssertionError):require_placement_completion(train,verify)
    del state['jobs']['train_early_272003']
    (train/'controller.json').write_text(json.dumps(state))
    with pytest.raises(AssertionError):require_placement_completion(train,verify)


def test_regret_contributions_respect_unequal_sites_per_protein():
    def row(site,parent,regret):
        return dict(site_key=site,parent=parent,role='dev',arm='correct',old_selected='A',old_select_new_regret=regret)
    early=[row('a',0,2),row('b',0,4),row('c',1,10)]
    late=[row('a',0,0),row('b',0,0),row('c',1,0)]
    result=selection_contributions(early,late)
    assert [r['protein_weighted_contribution'] for r in result]==[.5,1.,5.]
    assert sum(r['protein_weighted_contribution'] for r in result)==6.5
    assert all(not r['selection_changed'] for r in result)
    with pytest.raises(AssertionError):selection_contributions(early,late[:-1])
    with pytest.raises(AssertionError):selection_contributions(early+[early[0]],late)
    wrong=copy.deepcopy(late);wrong[0]['parent']=1
    with pytest.raises(AssertionError):selection_contributions(early,wrong)


def test_equal_pass_totals_do_not_hide_broken_and_repaired_outputs():
    def row(aa,passed,severe):
        return dict(site_key='x',noise=230201,aa=aa,arm='correct',role='dev',parent=0,
            geometry=dict(zero_severe_strict_checked_chirality=passed,severe_pairs=severe,checked_chirality_wrong=0))
    early=[row('A',False,2),row('D',True,0)]
    late=[row('A',True,0),row('D',False,7)]
    value=placement_geometry_transitions(early,late)['dev']['counts']
    assert value['early_pass']==value['late_pass']==1
    assert value['late_pass_to_early_fail']==value['late_fail_to_early_pass']==1
    assert value['severe_pair_delta']==-5
    with pytest.raises(AssertionError):placement_geometry_transitions(early,late[:-1])


def test_trajectory_places_gradient_loss_before_the_charged_update():
    keys=[f's{i}' for i in range(27)];history=[]
    for step in range(1,129):
        raw=1-(step-1)*.001
        row=dict(raw=raw,common=.4*raw,centered=.6*raw)
        history.append(dict(step=step,seconds=2.,gradient_norm=.5,clipped=False,
            summary=dict(**row,sites=[dict(site=k,**row) for k in keys],
                counts=dict(forwards=513,backwards=513,reference_forwards=27,reference_backwards=27,gradient_passes=1))))
    tensor=dict(objectives=[dict(step=i,raw=1-i*.001) for i in (0,32,128)])
    value=placement_trajectory(history,dict(train_sites=keys),tensor)
    assert value['states'][0]['state_step']==0 and value['states'][0]['raw']==1.
    assert value['states'][127]['state_step']==127 and value['states'][127]['raw']==pytest.approx(.873)
    assert value['states'][128]==dict(state_step=128,raw=.872,common=None,centered=None)
    assert value['update_seconds']['sum']==256 and not value['balanced_benchmark']
    with pytest.raises(AssertionError):placement_trajectory(history[:-1],dict(train_sites=keys),tensor)
