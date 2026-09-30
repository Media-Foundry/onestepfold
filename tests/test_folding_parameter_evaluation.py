import copy
import gzip
import json
from pathlib import Path

import pytest

from fastglycan.evaluation_reuse import expected_evaluation_calls, evaluation_prediction_source
from fastglycan.folding_parameter_evaluation import (
    CANDIDATE, REFERENCES, make_parameter_evaluation_lock, render_parameter_extent,
)


def prior_lock():
    p = Path(__file__).parents[1]/'reports/mini_folding_global_distance_evaluation_2026-09-30/final/lock.json.gz'
    with gzip.open(p, 'rt') as f:
        return json.load(f)


def candidate_lock(prior):
    return make_parameter_evaluation_lock(prior, train='/newtrain', reference_evaluation='/reference',
        checkpoint={'path': '/terminal.pt', 'sha256': 'checkpoint'}, training_lock_sha256='training-lock',
        selected_names=['diffusion.weight'], hashes={}, input_hashes={}, protocol_sha256='protocol')


def test_real_frozen_panel_reuses_all_six_models_with_only_910_new_calls():
    prior = prior_lock(); before = copy.deepcopy(prior); lock = candidate_lock(prior)
    assert prior == before
    assert lock['models'] == REFERENCES+[CANDIDATE]
    assert lock['planned_outputs'] == 6370 and lock['planned_probe_nfe'] == 32
    assert expected_evaluation_calls(lock, lock['rows']) == {'native': 0, CANDIDATE: 910}
    assert sum(expected_evaluation_calls(lock, s)[CANDIDATE] for s in lock['assignments']) == 910
    for row in lock['rows']:
        seeds = lock['train_seeds'] if row['role'] == 'train' else lock['validation_seeds']
        for seed in seeds:
            for model in REFERENCES:
                assert evaluation_prediction_source(lock, row, model, seed) == Path(f'/reference/examples/{row["group_id"]}/{model}_seed{seed}.npy')
            assert evaluation_prediction_source(lock, row, CANDIDATE, seed) is None
    assert lock['contrasts'][:2] == [[CANDIDATE, 'global_distance'], [CANDIDATE, 'expanded']]
    assert lock['checkpoint_arms'] == {CANDIDATE: 'expanded'}
    assert lock['checkpoints'] == {CANDIDATE: {'path': '/terminal.pt', 'sha256': 'checkpoint'}}
    assert all(lock[k] == prior[k] for k in ['rows', 'assignments', 'cohorts', 'cohort_order', 'train_seeds', 'validation_seeds', 'bootstrap', 'source', 'cache'])


@pytest.mark.parametrize('corruption', ['models', 'cohort', 'role', 'assignment', 'noise', 'row'])
def test_denominator_and_protocol_drift_rejected(corruption):
    p = prior_lock()
    if corruption == 'models': p['models'].pop()
    elif corruption == 'cohort': p['cohorts']['added_train295'][0] = p['cohorts']['original_train128'][0]
    elif corruption == 'role': p['rows'][0]['role'] = 'unknown'
    elif corruption == 'assignment': p['assignments'][0][0] = p['assignments'][0][1]
    elif corruption == 'noise': p['validation_seeds'] = [810013, 810031]
    elif corruption == 'row': p['rows'][0] = copy.deepcopy(p['rows'][1])
    with pytest.raises(ValueError): candidate_lock(p)


def test_extent_reports_both_primary_comparisons_and_null_support():
    lock = candidate_lock(prior_lock())
    keys = ['seq24_gt_ge30.mae', 'seq24_gt_ge30.signed_mean', 'fragment32_rmsd', 'remainder95_rmsd_fixed_alignment', 'rg_ratio']
    stats = {k: {'mean': None, 'proteins': 0, 'ci95': None} for k in keys}
    extent = dict(complete=True, outputs=6370, proteins=455, diagnostic_candidate=CANDIDATE, diagnostic_reference='global_distance', summary={})
    for cohort in lock['cohort_order']:
        extent['summary'][cohort] = dict(models={m: copy.deepcopy(stats) for m in lock['models']},
            contrasts=[dict(candidate=a, reference=b, metrics=copy.deepcopy(stats)) for a, b in lock['contrasts']])
    text = render_parameter_extent(extent, lock)
    assert CANDIDATE+' − global_distance' in text and CANDIDATE+' − expanded' in text
    assert '|0|NA|NA|' in text
    extent['outputs'] -= 1
    with pytest.raises(ValueError): render_parameter_extent(extent, lock)


def test_seventh_model_statistics_and_rendering_with_explicit_identity_fixture():
    """Synthetic candidate copies old scores solely to test seven-model plumbing."""
    from fastglycan.folding_evaluation import summarize_folding_cohorts
    from fastglycan.folding_global_metrics import summarize_global_structure
    from fastglycan.folding_report import render_folding_scale_report
    folder = Path(__file__).parents[1]/'reports/mini_folding_global_distance_evaluation_2026-09-30/final'
    with gzip.open(folder/'scored_instances.json.gz', 'rt') as f:
        data = json.load(f)
    records = data['records'] if isinstance(data, dict) else data
    records = copy.deepcopy(records)
    for r in list(records):
        if r['model'] == 'global_distance':
            new = copy.deepcopy(r); new['model'] = CANDIDATE; records.append(new)
    assert len(records) == 6370
    lock = candidate_lock(prior_lock()); lock['bootstrap']['replicates'] = 20
    cohorts = summarize_folding_cohorts(records, lock)
    global_result = summarize_global_structure(records, lock)
    for name in lock['cohorts']:
        pair = cohorts['summary'][name]['contrasts'][0]
        assert pair['candidate'] == CANDIDATE and pair['reference'] == 'global_distance'
        assert pair['quality']['all_atom_lddt']['mean'] == 0
        assert pair['quality']['all_atom_lddt']['ci95'] == [0, 0]
        assert global_result['summary'][name]['contrasts'][0]['mean'] == 0
    training = json.loads((folder/'training_comparison.json').read_text())
    training['summary'][CANDIDATE] = copy.deepcopy(training['summary']['global_distance'])
    evaluation = dict(complete=True, outputs=6370, proteins=455, counts={'native': 0, CANDIDATE: 910}, probe_nfe=32, metric_max_abs=0.)
    report = render_folding_scale_report(lock, training, evaluation, {'complete': True, **cohorts})
    assert '**6370**' in report and CANDIDATE+' − global_distance' in report and CANDIDATE+' − expanded' in report
    with pytest.raises(ValueError): summarize_folding_cohorts(records[:-1], lock)


def test_terminal_replay_required_before_scoring(tmp_path, monkeypatch):
    import runpy
    import sys
    import types
    from fastglycan.paired_teacher_protocol import sha256
    path = Path(__file__).parents[1]/'scripts/evaluate_folding_global_parameter.py'
    api = runpy.run_path(str(path)); called = []
    monkeypatch.setitem(sys.modules, 'score_diffusion_learning', types.SimpleNamespace(summarize_diffusion_evaluation=lambda *a: called.append(a)))
    train = tmp_path/'train'; probe = train/'expanded/probe_2048/report.json'; probe.parent.mkdir(parents=True)
    probe.write_text('{}')
    lock = tmp_path/'lock.json'; lock.write_text(json.dumps({'train': str(train)}))
    replay = dict(complete=True, exact_coordinates=63, lock_sha256=sha256(lock), training_probe_sha256=sha256(probe))
    (tmp_path/'terminal_replay.json').write_text(json.dumps(replay))
    with pytest.raises(AssertionError): api['score_parameter_evaluation'](tmp_path, 1)
    assert not called
    replay['exact_coordinates'] = 64; replay['training_probe_sha256'] = 'wrong'
    (tmp_path/'terminal_replay.json').write_text(json.dumps(replay))
    with pytest.raises(AssertionError): api['score_parameter_evaluation'](tmp_path, 1)
    assert not called


def test_collect_checks_actual_terminal_coordinate_bytes(tmp_path, monkeypatch):
    import runpy
    import sys
    import types
    from fastglycan.paired_teacher_protocol import sha256
    api = runpy.run_path(str(Path(__file__).parents[1]/'scripts/evaluate_folding_global_parameter.py'))
    monkeypatch.setitem(sys.modules, 'evaluate_folding_scale', types.SimpleNamespace(collect_folding_evaluation=lambda *a: None))
    train = tmp_path/'train'; probe = train/'expanded/probe_2048/report.json'; probe.parent.mkdir(parents=True)
    records = []
    for i in range(32):
        target = tmp_path/'examples'/str(i); target.mkdir(parents=True)
        for seed in [600001, 600011]:
            data = f'coordinate fixture {i} {seed}'.encode()
            original = probe.parent/f'{i}_{seed}.npy'; original.write_bytes(data)
            (target/f'{CANDIDATE}_seed{seed}.npy').write_bytes(data)
            records.append({'group_id': str(i), 'seed': seed, 'sha256': sha256(original)})
    probe.write_text(json.dumps({'records': records}))
    (tmp_path/'lock.json').write_text(json.dumps({'train': str(train)}))
    api['collect_parameter_evaluation'](tmp_path)
    output = tmp_path/'terminal_replay.json'
    assert json.loads(output.read_text())['exact_coordinates'] == 64
    output.unlink()
    (tmp_path/'examples/31'/f'{CANDIDATE}_seed600011.npy').write_bytes(b'changed')
    with pytest.raises(AssertionError): api['collect_parameter_evaluation'](tmp_path)
    assert not output.exists()
