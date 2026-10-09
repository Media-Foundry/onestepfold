"""Independent accounting, historical controls and coordinate-score arithmetic."""
from collections import Counter
import gzip
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr


def verify_candidate_results(root):
    manifest = json.loads((root / 'manifest.json').read_text())
    for name, digest in manifest['files'].items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
    lock = json.loads((root / 'training_lock.json').read_text())
    old_root = root.parent / 'mini_pair_recovery_2026-10-09'
    old_lock = json.loads((old_root / 'training_lock.json').read_text())
    old_pre = json.loads((old_root / 'preflight.json').read_text())
    assert lock['train_sites'] == ['p3_s37'] and lock['checkpoints'] == [0,304,1216,4104,8208]
    assert lock['site_scale_squared'] == old_lock['site_scale_squared']
    assert lock['code']['src/fastglycan/models/pair_recovery.py'] == old_lock['code']['src/fastglycan/models/pair_recovery.py']
    tensor = json.loads((root / 'tensor_verification.json').read_text())
    assert tensor['complete'] and tensor['full_field'] and len(tensor['checked']) == 20
    checks = dict(runs=0, checkpoints=0, updates=0, correlations=0, regrets=0,
                  historical_controls=0, output_records=0, decompositions=0, s1=0)
    for arm in lock['arms']:
        for seed in lock['seeds']:
            folder = root / 'runs' / arm / str(seed)
            report = json.loads((folder / 'report.json').read_text())
            assert report['complete'] and report['parameters'] == 1331972
            assert report['initial_sha256'] == old_pre['models'][f'{arm}_{seed}']['initial_sha256']
            assert report['counts'] == dict(s1=228, updates=8208, recycle=0, c4=0, input_embedder=0)
            assert report['unchanged_inputs'] and report['unchanged_reference']
            assert report['training_forward_count'] == 16416 and report['evaluation_forward_count'] == 99
            assert report['feature_forwards'] == 16515
            assert hashlib.sha256((folder / 'history.jsonl').read_bytes()).hexdigest() == report['history_sha256']
            rows = [json.loads(line) for line in (folder / 'history.jsonl').read_text().splitlines()]
            assert len(rows) == 8208
            choices = list(report['exposure'])
            assert len(choices) == 19 and set(choices) == set('ACDEFGHIKLMNPQRSTVWY') - {'T'}
            # JSON key sorting is not the schedule: obtain fixed order from the saved AA rows.
            ev0 = json.loads((folder / 'evaluation_0.json').read_text())
            choices = [r['aa'] for r in ev0['candidate_stats']]
            counts = Counter({aa: 0 for aa in choices})
            for index, row in enumerate(rows):
                assert row['step'] == index + 1 and row['site'] == 'p3_s37'
                assert row['aa'] == [choices[(2 * index + j) % 19] for j in (0, 1)]
                assert all(math.isfinite(v) for v in row['loss'])
                assert row['clipped'] == (row['gradient_norm'] > 1)
                counts.update(row['aa'])
                if index + 1 in lock['checkpoints']:
                    ev = json.loads((folder / f'evaluation_{index+1}.json').read_text())
                    assert ev['exposure'] == dict(counts)
            assert dict(counts) == report['exposure'] == dict.fromkeys(choices, 864)
            assert not any(a['missing'] for a in report['gradient_audits'])
            for audit in report['gradient_audits']:
                assert all(math.isfinite(v) for v in audit['norms'].values())
            with gzip.open(old_root / 'runs' / arm / str(seed) / 'scores_8208.json.gz', 'rt') as handle:
                old_scores = json.load(handle)
            historical = {r['arm']: r for r in old_scores['sites'] if r['site_key'] == 'p3_s37'}
            historical_latent = next(r['moments'] for r in json.loads(
                (old_root / 'runs' / arm / str(seed) / 'evaluation_8208.json').read_text())['latent'] if r['site'] == 'p3_s37')
            for step in lock['checkpoints']:
                ev = json.loads((folder / f'evaluation_{step}.json').read_text())
                assert ev['complete'] and ev['site'] == 'p3_s37' and len(ev['latent']) == 1
                m = ev['latent'][0]['moments']
                for field in ('target_energy', 'predicted_energy', 'error_energy'):
                    assert math.isclose(m['raw'][field], m['common'][field] + m['centered'][field], rel_tol=2e-8, abs_tol=1e-7)
                for mode in ('raw', 'common', 'centered'):
                    assert math.isclose(m[mode]['target_energy'], historical_latent[mode]['target_energy'], rel_tol=1e-12)
                assert math.isclose(m['raw']['error_energy'], np.mean([r['moments']['raw']['error_energy'] for r in ev['candidate_stats']]), rel_tol=1e-10)
                if step == 0:
                    assert m['raw']['nmse'] == m['centered']['nmse'] == 1.
                    assert all(v == 0 for v in ev['parameter_movement_squared'].values())
                else:
                    assert all(v > 0 for v in ev['parameter_movement_squared'].values())
                checks['decompositions'] += 1
                with gzip.open(folder / f'scores_{step}.json.gz', 'rt') as handle:
                    score = json.load(handle)
                assert score['complete'] and score['contrasts'] == {'train': {}}
                lookup = {r['arm']: r for r in score['sites']}
                assert len(lookup) == (5 if step == 8208 else 4)
                exact = np.asarray(lookup['exact']['tasks'])
                for method, row in lookup.items():
                    assert row['site_key'] == 'p3_s37' and row['role'] == 'train'
                    pred = np.asarray(row['tasks'])
                    for ni in range(3):
                        x, y = (exact[ni], pred[ni]) if ni < 2 else (exact.mean(0), pred.mean(0))
                        rho = float(spearmanr(x, y).statistic)
                        got = row['ranking'][ni]['spearman'] if ni < 2 else row['aggregate_ranking']['spearman']
                        assert math.isclose(rho, got, abs_tol=1e-12)
                        checks['correlations'] += 1
                    selected = int(np.argmin(pred[0]))
                    assert row['old_selected'] == choices[selected]
                    assert math.isclose(row['old_select_new_regret'], exact[1,selected]-exact[1].min(), abs_tol=1e-12)
                    checks['regrets'] += 1
                    if method in ('exact', 'disabled', 'oracle_pair'):
                        for key in ('tasks','ranking','aggregate_ranking','old_selected','old_select_new_regret','response','local_mean','local_max','aa_lddt','ca_lddt'):
                            assert row[key] == historical[method][key], (arm,seed,step,method,key)
                        checks['historical_controls'] += 1
                    if step == 0 and method == 'correct':
                        for key in ('tasks','ranking','aggregate_ranking','response','old_selected','old_select_new_regret'):
                            assert row[key] == lookup['disabled'][key]
                outputs = score['outputs']
                assert len(outputs) == len(lookup)*38
                assert len({(r['arm'],r['noise'],r['label']) for r in outputs}) == len(outputs)
                checks['output_records'] += len(outputs)
                for method, value in score['summary']['train'].items():
                    oo = [r for r in outputs if r['arm'] == method]
                    assert value['geometry_pass'] == sum(r['geometry']['zero_severe_strict_checked_chirality'] for r in oo)
                    assert value['severe_pairs'] == sum(r['geometry']['severe_pairs'] for r in oo)
                    assert value['wrong_centres'] == sum(r['geometry']['checked_chirality_wrong'] for r in oo)
                    for key in ('disabled_pass_to_fail','disabled_fail_to_pass','exact_pass_to_fail','exact_fail_to_pass'):
                        assert value[key] == sum(r[key] for r in oo)
                    local = np.array([r['fidelity']['local_ca_rmsd_global_frame'] for r in oo])
                    for key, expected in [('local_max',local.max()),('local_p95',np.quantile(local,.95)),('local_p99',np.quantile(local,.99)),('local_over1',int((local>1).sum()))]:
                        assert value[key] == expected
                checks['checkpoints'] += 1
            checks['runs'] += 1; checks['updates'] += len(rows); checks['s1'] += report['counts']['s1']
    assert checks['updates'] == 32832 and checks['s1'] == 912
    result = dict(complete=True, source_files_sha_verified=len(manifest['files']), checks=checks,
                  full_field_tensor_check=tensor['complete'], no_independent_confirmation=True)
    (root / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    verify_candidate_results(Path(__file__).resolve().parent)
