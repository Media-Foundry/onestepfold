"""Independent CPU arithmetic checks of the fixed pair-recovery experiment."""
import gzip
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr


def verify_pair_recovery(root):
    manifest = json.loads((root / 'manifest.json').read_text())
    for name, digest in manifest['files'].items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
    lock = json.loads((root / 'training_lock.json').read_text())
    old = json.loads((root.parent / 'mini_oracle_pair_2026-10-09/summary.json').read_text())
    controls = {(r['site_key'], r['arm']): r for r in old['sites']}
    train = lock['train_residual_stats']
    assert len(train) == 27 and all(r['role'] == 'train' for r in train)
    floor = max(float(np.quantile([r['mean_squared_residual'] for r in train], .25)), 1e-12)
    assert floor == lock['scale_floor']
    assert lock['site_scale_squared'] == {r['site']: max(r['mean_squared_residual'], floor) for r in train}
    counts = dict(updates=0, recycle=0, c4=0, input_embedder=0, s1=0)
    checks = dict(correlations=0, regrets=0, historical_site_controls=0, output_records=0,
                  residual_decompositions=0, exposure_entries=0)
    for seed in lock['seeds']:
        for initialization in lock['arms']:
            folder = root / 'runs' / initialization / str(seed)
            run = json.loads((folder / 'report.json').read_text())
            assert run['complete'] and run['step'] == 8208
            assert run['runtime']['cuda_visible'] is None and run['runtime']['rocr_visible'] is None
            assert run['runtime']['hip_visible'] in ('0', '1', '2', '3')
            assert run['runtime']['physical_mapping_verified']
            assert run['counts'] == dict(updates=8208, recycle=0, c4=0, input_embedder=0, s1=5472)
            for name in counts:
                counts[name] += run['counts'][name]
            history = [json.loads(line) for line in (folder / 'history.jsonl').read_text().splitlines()]
            assert len(history) == 8208 and [r['step'] for r in history] == list(range(1, 8209))
            exposure = {k: {} for k in lock['train_sites']}
            for row in history:
                assert row['site'] in exposure and len(row['aa']) == 2
                assert np.isfinite(row['loss'] + [row['gradient_norm']]).all()
                for aa in row['aa']:
                    exposure[row['site']][aa] = exposure[row['site']].get(aa, 0) + 1
            assert exposure == run['exposure'] and all(len(r) == 19 for r in exposure.values())
            assert all(n == 32 for r in exposure.values() for n in r.values())
            for step in lock['checkpoints']:
                with gzip.open(folder / f'scores_{step}.json.gz', 'rt') as handle:
                    result = json.load(handle)
                assert result['complete'] and result['initialization'] == initialization
                assert result['seed'] == seed and result['step'] == step
                ev = json.loads((folder / f'evaluation_{step}.json').read_text())
                assert ev['complete'] and len(ev['predictions']) == (912 if step == 4104 else 1824)
                assert len({(r['label'], r['arm']) for r in ev['predictions']}) == len(ev['predictions'])
                scheduled = json.loads((folder / f'exposure_{step}.json').read_text())
                assert len(scheduled) == 27 and all(len(r) == 19 for r in scheduled.values())
                assert all(n == step // 256.5 for r in scheduled.values() for n in r.values())
                checks['exposure_entries'] += 513
                for row in ev['latent']:
                    moments = row['moments']
                    assert moments['candidates'] == 19
                    for key in ('target_energy', 'predicted_energy', 'error_energy'):
                        assert math.isclose(moments['raw'][key], moments['common'][key] + moments['centered'][key],
                                            rel_tol=1e-7, abs_tol=1e-7)
                    checks['residual_decompositions'] += 1
                sites = result['sites']
                lookup = {(r['site_key'], r['arm']): r for r in sites}
                assert len(sites) == len(lookup) == 48 * (4 if step == 4104 else 5)
                for row in sites:
                    predicted = np.asarray(row['tasks'])
                    exact = np.asarray(lookup[row['site_key'], 'exact']['tasks'])
                    for ni in range(3):
                        a, b = (exact[ni], predicted[ni]) if ni < 2 else (exact.mean(0), predicted.mean(0))
                        rho = float(spearmanr(a, b).statistic)
                        recorded = row['ranking'][ni]['spearman'] if ni < 2 else row['aggregate_ranking']['spearman']
                        assert (recorded is None and math.isnan(rho)) or math.isclose(recorded, rho, abs_tol=1e-12)
                        checks['correlations'] += 1
                    regret = float(exact[1, np.argmin(predicted[0])] - exact[1].min())
                    assert math.isclose(regret, row['old_select_new_regret'], abs_tol=1e-12)
                    checks['regrets'] += 1
                    if row['arm'] in ('exact', 'disabled', 'oracle_pair'):
                        reference = controls[row['site_key'], row['arm']]
                        for key in ('tasks', 'ranking', 'aggregate_ranking', 'old_selected', 'old_select_new_regret',
                                    'response', 'local_mean', 'local_max', 'aa_lddt', 'ca_lddt'):
                            assert row[key] == reference[key], (row['site_key'], row['arm'], key)
                        checks['historical_site_controls'] += 1
                outputs = result['outputs']
                assert len(outputs) == len({(r['arm'], r['label'], r['noise']) for r in outputs})
                assert len(outputs) == 1824 * (4 if step == 4104 else 5)
                checks['output_records'] += len(outputs)
                for role, arms in result['summary'].items():
                    for arm, values in arms.items():
                        rr = [r for r in sites if r['role'] == role and r['arm'] == arm]
                        oo = [r for r in outputs if r['role'] == role and r['arm'] == arm]
                        assert values['outputs'] == len(oo)
                        assert values['geometry_pass'] == sum(r['geometry']['zero_severe_strict_checked_chirality'] for r in oo)
                        assert values['severe_pairs'] == sum(r['geometry']['severe_pairs'] for r in oo)
                        assert values['wrong_centres'] == sum(r['geometry']['checked_chirality_wrong'] for r in oo)
                        for key in ('disabled_pass_to_fail', 'disabled_fail_to_pass', 'exact_pass_to_fail', 'exact_fail_to_pass'):
                            assert values[key] == sum(r[key] for r in oo)
                        local = np.array([r['fidelity']['local_ca_rmsd_global_frame'] for r in oo])
                        for key, value in (('local_p95', np.quantile(local, .95)), ('local_p99', np.quantile(local, .99)),
                                           ('local_max', local.max()), ('local_over1', (local > 1).sum())):
                            assert values[key] == value
                        parent_regrets = [np.mean([r['old_select_new_regret'] for r in rr if r['parent'] == p])
                                          for p in sorted({r['parent'] for r in rr})]
                        assert math.isclose(values['regret'], float(np.mean(parent_regrets)), abs_tol=1e-12)
                        assert math.isclose(values['regret_parent_max'], float(max(parent_regrets)), abs_tol=1e-12)
    assert counts == dict(updates=32832, recycle=0, c4=0, input_embedder=0, s1=21888)
    result = dict(complete=True, main_counts=counts, checks=checks,
                  source_files_sha_verified=len(manifest['files']), train_only_scales_verified=True,
                  geometry_and_tail_counts_verified=True, all_panels_development=True)
    (root / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    verify_pair_recovery(Path(__file__).resolve().parent)
