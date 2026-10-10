"""The reporting boundary must not turn rejected trials into model improvements."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest

from fastglycan.fullbatch_results import verify_fullbatch_history


def _ledger_fixture():
    def gradient(n, value, digest):
        return dict(kind='gradient', gradient_pass=n, raw=value, common=value / 2,
                    centered=value / 2, gradient_norm=1., parameter_sha256=digest,
                    sites=[dict(site='train', raw=value, common=value / 2, centered=value / 2)])

    history = [gradient(1, .9, 'start'), gradient(2, .2, 'unaccepted_trial'),
               gradient(3, .8, 'accepted'),
               dict(kind='update', gradient_passes=3, calls=3, status='accepted',
                    changed=True, before=.9, after=.8),
               gradient(4, .8, 'accepted'),
               dict(kind='update', gradient_passes=4, calls=1, status='budget_rollback',
                    changed=False, before=.8, after=.8)]
    lock = dict(gradient_budget=4, train_sites=['train'], initial_objective=.9)
    report = dict(arm='lbfgs', optimizer_calls=2, changed_updates=1, rollbacks=1)
    objectives = [dict(step=0, objective=.9, parameter_sha256='start'),
                  dict(step=4, objective=.8, parameter_sha256='accepted')]
    return history, lock, report, objectives


def test_fullbatch_ledger_uses_returned_state_and_counts_discarded_trials():
    args = _ledger_fixture()
    result = verify_fullbatch_history(*args)
    assert result['evaluations'] == 4 and result['changed_updates'] == 1
    assert min(r['raw'] for r in result['gradient_trials']) == .2
    assert [r['after'] for r in result['accepted_states']] == [.8, .8]
    assert result['status_counts'] == {'accepted': 1, 'budget_rollback': 1}
    altered = copy.deepcopy(args)
    altered[3][-1].update(objective=.2, parameter_sha256='unaccepted_trial')
    with pytest.raises(AssertionError):
        verify_fullbatch_history(*altered)


def test_fullbatch_ledger_rejects_missing_charged_evaluation():
    history, lock, report, objectives = _ledger_fixture()
    history.pop(1)
    with pytest.raises(AssertionError):
        verify_fullbatch_history(history, lock, report, objectives)


def test_export_refuses_unfinished_controller_before_creating_directory(tmp_path):
    path = Path(__file__).resolve().parents[1] / 'scripts/export_stage_fullbatch.py'
    spec = importlib.util.spec_from_file_location('fullbatch_export_gate', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    (tmp_path / 'training_lock.json').write_text('{}')
    (tmp_path / 'controller.json').write_text(json.dumps(dict(complete=False, phase='training')))
    with pytest.raises(ValueError, match='incomplete'):
        module.export_stage_fullbatch(tmp_path)
    assert not (tmp_path / 'export').exists() and not (tmp_path / 'export.partial').exists()
