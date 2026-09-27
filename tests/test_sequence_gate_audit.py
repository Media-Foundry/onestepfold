import json
from pathlib import Path
import numpy as np
import pytest
import torch
from fastglycan.models.soft_esm import sequence_probabilities
from fastglycan.sequence_gate_metrics import contact_objective
from fastglycan.sequence_gate_audit import validate_run


@pytest.fixture
def completed_run(tmp_path):
    sequence='A'*10
    x=torch.zeros(1,10,3);x[0,:,0]=torch.arange(10)*3.8
    loss=float(contact_objective(x,torch.arange(10))[0])
    observations=[]
    for seed in (103,107):
        for label in ('initial','optimized'):
            for s in (1,2):
                np.savez(tmp_path/f'{label}_seed{seed}_s{s}.npz',coordinates=x.numpy(),
                         atom_names=np.array(['CA']*10),residue_ids=np.arange(1,11),sequence=sequence)
                observations.append(dict(seed=seed,label=label,steps=s,loss=loss))
    directions=[dict(plateau_pass=True,rows=[dict(h=h,analytic=1.,finite_difference=1.)
                                           for h in (.3,.1,.03,.01,.003)]) for _ in range(3)]
    numerical=dict(directions=directions,finite=True,norm=1.,repeat_max_abs=0.,passed=True)
    report=dict(complete=True,stage='complete',length=10,sequence=sequence,final_sequence=sequence,
                trajectory=[dict(update=i,sequence=sequence,cross_losses={'1':loss,'2':loss}) for i in range(51)],
                gates={'2_s1_local_derivative':numerical,'2_s2_local_derivative':numerical,
                       '3_optimization':dict(updates=50),'4_independent_noise':observations})
    (tmp_path/'report.json').write_text(json.dumps(report))
    q=sequence_probabilities(sequence)*4
    torch.save(dict(initial_logits=q,final_logits=q),tmp_path/'logits.pt')
    return tmp_path


def test_complete_artifact_set_replays_objective(completed_run):
    result=validate_run(completed_run)
    assert result['artifacts_complete']
    assert len(result['artifact_sha256'])==10
    assert result['max_cpu_objective_replay_error']==0


def test_missing_coordinate_rejected(completed_run):
    (completed_run/'optimized_seed107_s2.npz').unlink()
    with pytest.raises(ValueError,match='coordinate artifacts'):validate_run(completed_run)


def test_incorrect_reported_loss_rejected(completed_run):
    path=completed_run/'report.json';report=json.loads(path.read_text())
    report['gates']['4_independent_noise'][0]['loss']+=.01
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError,match='reported objective'):validate_run(completed_run)


def test_finite_difference_pass_cannot_override_values(completed_run):
    path=completed_run/'report.json';report=json.loads(path.read_text())
    for row in report['gates']['2_s1_local_derivative']['directions'][0]['rows']:
        row['finite_difference']=0
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError,match='acceptance disagrees'):validate_run(completed_run)
