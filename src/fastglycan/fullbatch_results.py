"""Read-only NumPy/SciPy verification of the locked full-batch experiment.

No model, optimizer, GPU, teacher generation, or checkpoint selection occurs here.
Line-search evaluations and accepted model states are deliberately kept separate.
"""
from collections import Counter
import gzip
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

from fastglycan.fullbatch_recovery import verify_fullbatch_completion


def _json(path):
    return json.loads(Path(path).read_text())


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _close(a, b, *, rtol=1e-10, atol=1e-12):
    if a is None or b is None:
        assert a is b, (a, b)
    else:
        assert math.isfinite(a) and math.isfinite(b)
        assert math.isclose(a, b, rel_tol=rtol, abs_tol=atol), (a, b)


def verify_fullbatch_history(history, lock, report, objectives):
    """Verify every charged evaluation and identify the actually returned states."""
    gradients, transactions, pending = [], [], []
    checkpoints = {r['step']: r for r in objectives}
    for row in history:
        if row['kind'] == 'gradient':
            gradients.append(row)
            pending.append(row)
            assert row['gradient_pass'] == len(gradients)
            assert [r['site'] for r in row['sites']] == lock['train_sites']
            assert math.isfinite(row['gradient_norm']) and row['gradient_norm'] >= 0
            for mode in ('raw', 'common', 'centered'):
                _close(row[mode], float(np.mean([s[mode] for s in row['sites']])))
            _close(row['raw'], row['common'] + row['centered'])
            for site in row['sites']:
                _close(site['raw'], site['common'] + site['centered'])
        else:
            assert row['kind'] == 'update'
            assert len(pending) == row['calls'] > 0
            assert row['gradient_passes'] == len(gradients)
            _close(row['before'], pending[0]['raw'])
            transactions.append((row, pending))
            pending = []
    assert not pending and len(gradients) == lock['gradient_budget']
    assert len(transactions) == report['optimizer_calls']
    assert sum(int(r['changed']) for r, _ in transactions) == report['changed_updates']
    assert sum(r['status'].endswith('rollback') for r, _ in transactions) == report['rollbacks']
    accepted = []
    for i, (update, trial) in enumerate(transactions):
        end = update['gradient_passes']
        next_state = transactions[i + 1][1][0] if i + 1 < len(transactions) else None
        fixed = checkpoints.get(end)
        assert next_state is not None or fixed is not None
        digest = fixed['parameter_sha256'] if fixed else next_state['parameter_sha256']
        measured_loss = fixed['objective'] if fixed else next_state['raw']
        if fixed and next_state:
            assert fixed['parameter_sha256'] == next_state['parameter_sha256']
            _close(fixed['objective'], next_state['raw'], rtol=2e-8, atol=1e-10)
        assert update['changed'] == (digest != trial[0]['parameter_sha256'])
        if report['arm'] == 'lbfgs':
            assert update['status'] in ('accepted', 'unchanged', 'budget_rollback', 'ascent_rollback')
            assert update['calls'] <= 16
            _close(update['after'], measured_loss, rtol=2e-8, atol=1e-10)
            assert update['after'] <= update['before'] + 1e-10
            if update['status'] != 'accepted':
                assert not update['changed'] and digest == trial[0]['parameter_sha256']
            matches = [r for r in trial if r['parameter_sha256'] == digest]
            assert matches, 'returned L-BFGS state was not evaluated in this transaction'
            _close(matches[-1]['raw'], update['after'])
        else:
            assert update['status'] == 'adamw_step' and update['calls'] == 1
            assert update['clipped'] == (update['gradient_norm'] > 1)
            matches = [next_state] if next_state else []
        accepted.append(dict(gradient_passes=end, calls=update['calls'], status=update['status'],
                             changed=update['changed'], before=update['before'], after=measured_loss,
                             after_common=matches[-1]['common'] if matches else None,
                             after_centered=matches[-1]['centered'] if matches else None,
                             parameter_sha256=digest))
    assert checkpoints[0]['parameter_sha256'] == gradients[0]['parameter_sha256']
    _close(checkpoints[0]['objective'], lock['initial_objective'], rtol=2e-8, atol=1e-10)
    return dict(evaluations=len(gradients), optimizer_calls=len(transactions),
                changed_updates=report['changed_updates'], rollbacks=report['rollbacks'],
                status_counts=dict(Counter(r['status'] for r, _ in transactions)),
                accepted_states=accepted,
                gradient_trials=[{k: r[k] for k in ('gradient_pass', 'raw', 'common', 'centered',
                                                    'gradient_norm', 'parameter_sha256')} for r in gradients])


def _parent_interval(first, second, field):
    a, b = ({r['parent']: r[field] for r in rows} for rows in (first, second))
    assert set(a) == set(b)
    delta = np.asarray([a[k] - b[k] for k in sorted(a) if a[k] is not None and b[k] is not None])
    if not len(delta):
        return dict(parents=0, mean=None, interval=None)
    rng = np.random.default_rng(275001)
    means = delta[rng.integers(len(delta), size=(10000, len(delta)))].mean(1)
    return dict(parents=len(delta), mean=float(delta.mean()),
                interval=np.quantile(means, [.025, .975]).tolist(), descriptive=True)


def _check_score(score, ev, historical):
    """Recompute selection, aggregation, transitions and bootstrap arithmetic."""
    lookup = {(r['site_key'], r['arm']): r for r in score['sites']}
    arms = ['exact', 'disabled', 'oracle_pair', 'correct'] + (['mismatched'] if ev['step'] == 128 else [])
    sites = {r['site']: r for r in ev['latent']}
    assert set(lookup) == {(k, arm) for k in sites for arm in arms}
    outputs = {(r['site_key'], r['arm'], r['noise'], r['aa']): r for r in score['outputs']}
    assert len(outputs) == len(score['outputs']) == 38 * len(lookup)
    noise_ids = sorted({r['noise'] for r in score['outputs']})
    assert noise_ids == [230201, 230211]
    for row in score['sites']:
        key, arm = row['site_key'], row['arm']
        assert row['parent'] == sites[key]['parent'] and row['role'] == sites[key]['role']
        exact, predicted = (np.asarray(r['tasks']) for r in (lookup[key, 'exact'], row))
        assert exact.shape == predicted.shape == (2, 19)
        assert np.isfinite(exact).all() and np.isfinite(predicted).all()
        choices = [r['aa'] for r in score['outputs']
                   if (r['site_key'], r['arm'], r['noise']) == (key, 'exact', noise_ids[0])]
        assert len(set(choices)) == 19 and row['original_aa'] not in choices
        for ni in range(3):
            x, y = (exact[ni], predicted[ni]) if ni < 2 else (exact.mean(0), predicted.mean(0))
            rank = row['ranking'][ni] if ni < 2 else row['aggregate_ranking']
            rho = float(spearmanr(x, y).statistic)
            _close(None if math.isnan(rho) else rho, rank['spearman'])
            _close(float(np.mean(np.abs(x - y))), rank['task_mae'])
            assert rank['top1_match'] == bool(np.argmin(x) == np.argmin(y))
            for n in (3, 5):
                _close(len(set(np.argsort(x, kind='stable')[:n]) & set(np.argsort(y, kind='stable')[:n])) / n, rank[f'top{n}_recall'])
        selected = int(np.argmin(predicted[0]))
        assert row['old_selected'] == choices[selected]
        _close(float(exact[1, selected] - exact[1].min()), row['old_select_new_regret'])
        if arm in ('exact', 'disabled', 'oracle_pair'):
            old = historical[key, arm]
            for field in ('tasks', 'ranking', 'aggregate_ranking', 'response', 'old_selected',
                          'old_select_new_regret', 'local_mean', 'local_max', 'aa_lddt', 'ca_lddt'):
                assert row[field] == old[field], (key, arm, field)
        if ev['step'] == 0 and arm == 'correct':
            assert row['tasks'] == lookup[key, 'disabled']['tasks']
        for ni, noise in enumerate(noise_ids):
            for ai, aa in enumerate(choices):
                out = outputs[key, arm, noise, aa]
                _close(out['task'], predicted[ni, ai])
                ok = out['geometry']['zero_severe_strict_checked_chirality']
                for ref in ('exact', 'disabled'):
                    base_ok = outputs[key, ref, noise, aa]['geometry']['zero_severe_strict_checked_chirality']
                    assert out[f'{ref}_pass_to_fail'] == bool(base_ok and not ok)
                    assert out[f'{ref}_fail_to_pass'] == bool(not base_ok and ok)
    getters = dict(
        spearman=lambda r: r['aggregate_ranking']['spearman'],
        old_spearman=lambda r: r['ranking'][0]['spearman'],
        new_spearman=lambda r: r['ranking'][1]['spearman'],
        regret=lambda r: r['old_select_new_regret'],
        score_mae=lambda r: np.mean([x['task_mae'] for x in r['ranking']]),
        top3_recall=lambda r: r['aggregate_ranking']['top3_recall'],
        top5_recall=lambda r: r['aggregate_ranking']['top5_recall'],
        local_mean=lambda r: r['local_mean'], aa_lddt=lambda r: r['aa_lddt'], ca_lddt=lambda r: r['ca_lddt'],
        centered_response_rmse=lambda r: np.mean([x['centered_response_distance_rmse'] for x in r['response']]))
    for role, methods in score['summary'].items():
        assert set(methods) == set(arms)
        for method, summary in methods.items():
            rows = [r for r in score['sites'] if r['role'] == role and r['arm'] == method]
            outs = [r for r in score['outputs'] if r['role'] == role and r['arm'] == method]
            parents = sorted({r['parent'] for r in rows})
            assert (summary['parents'], summary['sites'], summary['outputs']) == (len(parents), len(rows), len(outs))
            stored = {r['parent']: r for r in summary['parent_summaries']}
            assert set(stored) == set(parents)
            for field, get in getters.items():
                means = []
                for parent in parents:
                    values = [get(r) for r in rows if r['parent'] == parent and get(r) is not None]
                    mean = float(np.mean(values)) if values else None
                    _close(mean, stored[parent][field])
                    if mean is not None:
                        means.append(mean)
                _close(float(np.mean(means)) if means else None, summary[field])
            regrets = [stored[p]['regret'] for p in parents]
            _close(float(np.median(regrets)), summary['regret_parent_median'])
            _close(max(regrets), summary['regret_parent_max'])
            assert summary['top1'] == sum(r['aggregate_ranking']['top1_match'] for r in rows)
            assert summary['undefined_spearman_sites'] == sum(r['aggregate_ranking']['spearman'] is None for r in rows)
            counts = dict(geometry_pass='zero_severe_strict_checked_chirality',
                          severe_pairs='severe_pairs', wrong_centres='checked_chirality_wrong')
            for field, raw in counts.items():
                assert summary[field] == sum(r['geometry'][raw] for r in outs)
            for ref in ('disabled', 'exact', 'reference'):
                for change in ('pass_to_fail', 'fail_to_pass'):
                    field = f'{ref}_{change}'
                    assert summary[field] == sum(r[field] for r in outs)
            local = np.asarray([r['fidelity']['local_ca_rmsd_global_frame'] for r in outs])
            _close(float(local.max()), summary['local_max'])
            _close(float(np.quantile(local, .95)), summary['local_p95'])
            _close(float(np.quantile(local, .99)), summary['local_p99'])
            assert summary['local_over1'] == int((local > 1).sum())
        for ref in ['disabled', 'oracle_pair'] + (['mismatched'] if ev['step'] == 128 else []):
            for field in ('spearman', 'regret', 'centered_response_rmse'):
                expected = _parent_interval(methods['correct']['parent_summaries'], methods[ref]['parent_summaries'], field)
                assert expected == score['contrasts'][role]['correct-' + ref][field]
    return dict(correlations=3 * len(lookup), regrets=len(lookup), outputs=len(outputs))


def verify_fullbatch_results(root):
    root = Path(root)
    manifest, lock = _json(root / 'manifest.json'), _json(root / 'training_lock.json')
    assert manifest['scientific_experiment_complete']
    for name, digest in manifest['files'].items():
        assert _sha(root / name) == digest, name
    assert _sha(root / 'protocol.md') == lock['protocol_sha256']
    assert lock['arms'] == ['adamw', 'lbfgs'] and lock['seeds'] == [272001, 272003]
    controller = _json(root / 'controller.json')
    recovered = verify_fullbatch_completion(root)
    assert manifest['operational_recovery'] is recovered
    assert controller['lock_sha256'] == _sha(root / 'training_lock.json')
    assert set(controller['jobs']) == {f'{kind}_{arm}_{seed}' for kind in ('train', 'score', 'verify')
                                      for arm in lock['arms'] for seed in lock['seeds']}
    assert _sha(root / 'source_stage_manifest.json') == lock['stage_manifest_sha256']
    old = _json(root / 'source_training_lock.json')
    assert _sha(root / 'source_training_lock.json') == lock['source_training_lock_sha256']
    for field in ('train_sites', 'eval_sites', 'site_scale_squared'):
        assert lock[field] == old[field]
    assert lock['checkpoints'] == [0, 32, 128] and lock['gradient_budget'] == 128
    with gzip.open(root / 'controls/scores_8208.json.gz', 'rt') as f:
        past = json.load(f)
    historical = {(r['site_key'], r['arm']): r for r in past['sites']}
    checks = Counter()
    ledger = {}
    for arm in lock['arms']:
        for seed in lock['seeds']:
            folder = root / 'runs' / arm / str(seed)
            report, tensor = _json(folder / 'report.json'), _json(folder / 'tensor_verification.json')
            assert report['complete'] and tensor['complete']
            assert report['gradient_passes'] == 128 and report['checkpoints'] == [0, 32, 128]
            assert report['arm'] == arm and report['seed'] == seed
            assert report['initial_sha256'] == lock['initial_hashes'][str(seed)]
            assert report['training_lock_sha256'] == _sha(root / 'training_lock.json')
            assert report['training_counts'] == dict(forwards=65664, backwards=65664, gradient_passes=128)
            assert report['native_counts'] == dict(c4=0, input_embedder=0, recycle=0, s1=7296, updates=0)
            assert report['isolation_forwards'] == 6 and report['evaluation_forwards'] == 2736
            assert report['initial_gradient_relative_error'] <= 5e-6
            assert report['cache_bytes'] <= lock['resident_tensor_byte_cap']
            assert _sha(folder / 'history.jsonl') == report['history_sha256']
            assert tensor['counts'] == dict(c4=0, input_embedder=0, recycle=0, s1=0, updates=0)
            assert tensor['verifier_sha256'] == lock['code']['scripts/verify_stage_fullbatch.py']
            assert tensor['feature_forwards'] == 2736
            assert {(r['step'], r['site']) for r in tensor['checks']} == {
                (step, site) for step in lock['checkpoints'] for site in lock['eval_sites']}
            history = [json.loads(s) for s in (folder / 'history.jsonl').read_text().splitlines()]
            ledger[f'{arm}_{seed}'] = verify_fullbatch_history(history, lock, report, tensor['objectives'])
            for step in lock['checkpoints']:
                ev = _json(folder / f'evaluation_{step}.json')
                assert ev['complete'] and ev['step'] == ev['gradient_passes'] == step
                assert {r['site'] for r in ev['latent']} == set(lock['eval_sites'])
                assert len(ev['predictions']) == (1824 if step == 128 else 912)
                for row in ev['latent']:
                    assert (row['role'] == 'train') == (row['site'] in lock['train_sites'])
                    assert (row['mismatch'] is not None) == (step == 128)
                    for moments in (row['moments'], row['mismatch']):
                        if moments is None:
                            continue
                        for field in ('error_energy', 'target_energy', 'predicted_energy'):
                            _close(moments['raw'][field], moments['common'][field] + moments['centered'][field], rtol=1e-7, atol=1e-7)
                    if step == 0:
                        assert row['moments']['raw']['nmse'] == row['moments']['centered']['nmse'] == 1.
                with gzip.open(folder / f'scores_{step}.json.gz', 'rt') as f:
                    score = json.load(f)
                assert score['complete'] and score['step'] == step and score['seed'] == seed
                assert score['scorer_sha256'] == lock['code']['scripts/score_pair_recovery.py']
                assert score['evaluation_sha256'] == _sha(folder / f'evaluation_{step}.json')
                assert _json(folder / f'summary_{step}.json') == {k: v for k, v in score.items() if k not in ('sites', 'outputs')}
                checks.update(_check_score(score, ev, historical))
                checks['nodes'] += 1
            checks.update(runs=1, training_forwards=65664, training_backwards=65664,
                          s1=7296, fixed_prediction_forwards=2736, isolation_forwards=6,
                          verification_forwards=2736, latent_replays=144)
    assert checks['runs'] == 4 and checks['nodes'] == 12
    result = dict(complete=True, scientific_experiment_complete=True, checks=dict(checks),
                  operational_recovery=recovered, original_controller_phase=controller['phase'],
                  files_sha_verified=len(manifest['files']), all_panels_development=True,
                  coordinate_scoring_recomputed=False, score_arithmetic_recomputed=True,
                  tensor_replay_verified=True, promoted=False, verifier_sha256=_sha(Path(__file__)),
                  lock_sha256=_sha(root / 'training_lock.json'))
    (root / 'optimization_ledger.json').write_text(json.dumps(ledger, indent=2, allow_nan=False) + '\n')
    (root / 'verification.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    return result


def analyze_fullbatch_results(root):
    root = Path(root)
    verified = _json(root / 'verification.json')
    assert verified['complete'] and verified['lock_sha256'] == _sha(root / 'training_lock.json')
    lock, ledger = _json(root / 'training_lock.json'), _json(root / 'optimization_ledger.json')
    runs, comparisons = {}, {}
    for arm in lock['arms']:
        for seed in lock['seeds']:
            folder = root / 'runs' / arm / str(seed)
            report, nodes = _json(folder / 'report.json'), []
            for step in lock['checkpoints']:
                ev = _json(folder / f'evaluation_{step}.json')
                with gzip.open(folder / f'scores_{step}.json.gz', 'rt') as f:
                    score = json.load(f)
                pooled = {}
                for role in sorted({r['role'] for r in ev['latent']}):
                    rr = [r for r in ev['latent'] if r['role'] == role]
                    parents = []
                    for parent in sorted({r['parent'] for r in rr}):
                        pp = [r for r in rr if r['parent'] == parent]
                        row = dict(parent=parent, sites=len(pp))
                        for mode in ('raw', 'common', 'centered'):
                            for field in ('nmse', 'energy_ratio', 'cosine'):
                                vv = [r['moments'][mode][field] for r in pp if r['moments'][mode][field] is not None]
                                row[f'{mode}_{field}'] = float(np.mean(vv)) if vv else None
                        fractions = [r['moments']['common']['predicted_energy'] / r['moments']['raw']['predicted_energy']
                                     for r in pp if r['moments']['raw']['predicted_energy'] > 0]
                        row['common_fraction'] = float(np.mean(fractions)) if fractions else None
                        if step == 128:
                            row['mismatch_centered_nmse'] = float(np.mean([r['mismatch']['centered']['nmse'] for r in pp]))
                        parents.append(row)
                    summary = dict(parents=len(parents), sites=len(rr), parent_summaries=parents)
                    for field in parents[0]:
                        if field in ('parent', 'sites'):
                            continue
                        vv = [r[field] for r in parents if r[field] is not None]
                        summary[field] = float(np.mean(vv)) if vv else None
                    pooled[role] = summary
                lookup = {(r['site_key'], r['arm']): r for r in score['sites']}
                choices = []
                for row in score['sites']:
                    if row['arm'] != 'correct':
                        continue
                    base, oracle = (lookup[row['site_key'], name] for name in ('disabled', 'oracle_pair'))
                    choice = dict(site=row['site_key'], parent=row['parent'], pdb=row['pdb'], role=row['role'],
                                  aa=row['old_selected'], baseline_aa=base['old_selected'], oracle_aa=oracle['old_selected'],
                                  regret=row['old_select_new_regret'], baseline_regret=base['old_select_new_regret'],
                                  regret_change=row['old_select_new_regret'] - base['old_select_new_regret'])
                    if step == 128:
                        wrong = lookup[row['site_key'], 'mismatched']
                        choice.update(mismatch_aa=wrong['old_selected'], mismatch_regret=wrong['old_select_new_regret'])
                    choices.append(choice)
                nodes.append(dict(step=step, latent=pooled, summary=score['summary'], contrasts=score['contrasts'], choices=choices))
            runs[f'{arm}_{seed}'] = dict(nodes=nodes, optimization=ledger[f'{arm}_{seed}'],
                seconds=report['seconds'], cache_bytes=report['cache_bytes'], cache_seconds=report['cache_seconds'],
                peak_allocated_bytes=report['peak_allocated_bytes'])
    for seed in lock['seeds']:
        for step_index, step in enumerate(lock['checkpoints']):
            a, b = (runs[f'{arm}_{seed}']['nodes'][step_index] for arm in ('lbfgs', 'adamw'))
            for role in a['summary']:
                comparisons[f'{seed}_{step}_{role}'] = {
                    field: _parent_interval(a['summary'][role]['correct']['parent_summaries'],
                                            b['summary'][role]['correct']['parent_summaries'], field)
                    for field in ('spearman', 'regret', 'centered_response_rmse')}
    result = dict(complete=True, runs=runs, lbfgs_minus_adamw=comparisons,
                  promoted=False, all_panels_development=True, recipe_comparison=True,
                  equal_walltime=False, equal_accepted_updates=False,
                  note='Every trial is charged; accepted_states, not last gradient_trials, define the model trajectory.')
    (root / 'analysis.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    return result
