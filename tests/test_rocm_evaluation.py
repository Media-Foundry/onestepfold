import copy
import gzip
import json
import runpy
from pathlib import Path
import pytest
from fastglycan.rocm_evaluation import make_rocm_evaluation_lock
from fastglycan.evaluation_reuse import expected_evaluation_calls

ROOT = Path(__file__).parents[1]


def test_matched_pair_uses_real_panel_and_no_historical_predictions():
    with gzip.open(ROOT/'reports/mini_folding_global_distance_evaluation_2026-09-30/final/lock.json.gz','rt') as f:
        prior=json.load(f)
    before=copy.deepcopy(prior)
    kwargs=dict(train='/train',checkpoints={a:dict(path='/'+a,sha256=a) for a in ['weak','strong']},
        training_locks={'weak':'w','strong':'s'},selected_names=['diffusion.weight'],hashes={},input_hashes={},protocol_sha256='p')
    lock=make_rocm_evaluation_lock(prior,**kwargs)
    assert prior==before
    assert lock['models']==['weak','strong'] and lock['contrasts']==[['strong','weak']]
    assert lock['reuse_models']=={} and lock['planned_outputs']==1820 and lock['planned_probe_nfe']==56
    assert expected_evaluation_calls(lock,lock['rows'])==dict(native=0,weak=910,strong=910)
    assert all(lock[k]==prior[k] for k in ['rows','assignments','cohorts','train_seeds','validation_seeds','bootstrap','cache','source'])
    kwargs['checkpoints'].pop('weak')
    with pytest.raises(ValueError):make_rocm_evaluation_lock(prior,**kwargs)


def test_failed_or_duplicate_inference_jobs_do_not_release_scoring(tmp_path):
    from fastglycan.paired_teacher_protocol import sha256
    api=runpy.run_path(str(ROOT/'scripts/evaluate_rocm_pair.py'))
    (tmp_path/'lock.json').write_text('{}')
    jobs=[dict(index=i,pid=i,exit_code=0) for i in range(8)]
    doc=dict(complete=True,jobs=jobs,lock_sha256=sha256(tmp_path/'lock.json'))
    jobs[0]['index']=1
    (tmp_path/'inference_execution.json').write_text(json.dumps(doc))
    with pytest.raises(AssertionError):api['collect_rocm_evaluation'](tmp_path)
    assert not (tmp_path/'execution.json').exists()
    jobs[0]['index']=0;jobs[0]['exit_code']=1
    (tmp_path/'inference_execution.json').write_text(json.dumps(doc))
    with pytest.raises(AssertionError):api['collect_rocm_evaluation'](tmp_path)
    assert not (tmp_path/'terminal_replay.json').exists()


def test_both_terminal_replays_are_required_before_scoring(tmp_path,monkeypatch):
    import sys
    import types
    from fastglycan.paired_teacher_protocol import sha256
    api=runpy.run_path(str(ROOT/'scripts/evaluate_rocm_pair.py'));calls=[]
    monkeypatch.setitem(sys.modules,'score_diffusion_learning',types.SimpleNamespace(summarize_diffusion_evaluation=lambda *a:calls.append(a)))
    monkeypatch.setitem(sys.modules,'analyze_folding_structure_extent',types.SimpleNamespace(summarize_structure_extent=lambda *a:None))
    (tmp_path/'lock.json').write_text('{}')
    (tmp_path/'terminal_replay.json').write_text(json.dumps(dict(complete=True,lock_sha256=sha256(tmp_path/'lock.json'),arms={'weak':dict(exact_coordinates=64)})))
    with pytest.raises(AssertionError):api['finish_rocm_evaluation'](tmp_path,1)
    assert not calls
