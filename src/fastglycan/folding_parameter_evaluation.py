"""Fixed seven-model comparison for the single parameter-matched candidate."""
import copy
from .evaluation_reuse import expected_evaluation_calls

CANDIDATE = 'global_parameter_matched'
REFERENCES = ['native_s1', 'native_s2', 'retained', 'expanded', 'coordinate_zero', 'global_distance']
REFERENCE_LOCK_SHA256 = 'f89f2649e957ac4158895c62a73eb560c81c91036468c6b5591771bdbc4c8a9d'
REFERENCE_EVALUATION_SHA256 = '6524194f416ef25c5a51abb5e00cf3dcc4a613f0ccd62a8816c6f36ce613acbd'


def make_parameter_evaluation_lock(prior, *, train, reference_evaluation, checkpoint,
                                  training_lock_sha256, selected_names, hashes, input_hashes,
                                  protocol_sha256):
    if prior['models'] != REFERENCES:
        raise ValueError('six audited reference models required')
    rows = prior['rows']
    ids = [r['group_id'] for r in rows]
    if len(ids) != 455 or len(set(ids)) != 455:
        raise ValueError('need 455 unique proteins')
    cohorts = prior['cohorts']
    expected = {'original_train128': 128, 'added_train295': 295, 'observed_validation32': 32}
    if {k: len(v) for k, v in cohorts.items()} != expected:
        raise ValueError('cohort denominator changed')
    members = [g for group in cohorts.values() for g in group]
    if len(set(members)) != 455 or set(members) != set(ids):
        raise ValueError('cohort overlap or missing protein')
    validation = set(cohorts['observed_validation32'])
    if any(r['role'] != ('validation' if r['group_id'] in validation else 'train') for r in rows):
        raise ValueError('cohort role mismatch')
    assigned = [r for shard in prior['assignments'] for r in shard]
    if len(prior['assignments']) != 8 or len(assigned) != 455 or {r['group_id']: r for r in assigned} != {r['group_id']: r for r in rows}:
        raise ValueError('worker assignments changed or duplicated')
    if prior['train_seeds'] != [600001, 600011] or prior['validation_seeds'] != [810013, 810029]:
        raise ValueError('locked noises changed')
    lock = copy.deepcopy(prior)
    lock.update(schema='folding_global_parameter_evaluation_v1', train=str(train),
        reference_evaluation=str(reference_evaluation),
        checkpoints={CANDIDATE: copy.deepcopy(checkpoint)},
        checkpoint_training_locks={CANDIDATE: training_lock_sha256},
        checkpoint_arms={CANDIDATE: 'expanded'}, selected_names={CANDIDATE: list(selected_names)},
        reuse_models={m: dict(root=str(reference_evaluation)+'/examples', model=m,
                             roles=['train', 'validation']) for m in REFERENCES},
        models=REFERENCES+[CANDIDATE], hashes=copy.deepcopy(hashes), input_hashes=copy.deepcopy(input_hashes),
        contrasts=[[CANDIDATE, m] for m in ['global_distance', 'expanded', 'coordinate_zero', 'retained', 'native_s1', 'native_s2']]
            + [['global_distance', 'expanded'], ['global_distance', 'coordinate_zero'], ['native_s2', 'native_s1']],
        primary='parameter-matched global weight versus global_distance AND expanded; observed DEV is development',
        planned_outputs=6370, planned_prediction_nfe=910, planned_probe_nfe=32, protocol_sha256=protocol_sha256,
        report_title='# C4/S1 parameter-matched global-distance weight: fixed terminal',
        report_intro='Same retained512 parent, TRAIN423 membership, 8192 ordered exposures and 2048 updates. '
            'Only global-distance weight changes from 0.0329065568 to 0.1810138829 relative to global_distance. '
            'The coefficient uses eight TRAIN initial-state parameter gradients, not terminal or DEV selection. '
            'Frozen ESM2/C4, native FP32, C4/S1/K1. Native S2 supervision is not experimental GT.',
        training_curve_note='Matched original-TRAIN32 probes; same exposure order and noises. No checkpoint selection.')
    if expected_evaluation_calls(lock, rows) != {'native': 0, CANDIDATE: 910}:
        raise ValueError('new inference budget mismatch')
    return lock


def render_parameter_extent(extent, lock):
    if not extent.get('complete') or extent['outputs'] != 6370 or extent['proteins'] != 455:
        raise ValueError('incomplete distance diagnostic')
    if extent['diagnostic_candidate'] != CANDIDATE or extent['diagnostic_reference'] != 'global_distance':
        raise ValueError('wrong primary distance comparison')
    lines = ['## Global shape and long-range distance diagnostics', '',
        'Existing coordinates only. Far pairs: sequence separation ≥24, experimental distance ≥30 Å. '
        'Positive MAE/RMSD changes are worse; signed error indicates expansion/contraction, not quality. '
        'No universal better direction for predicted/GT radius of gyration. Empty bands remain NA. '
        'Intervals resample proteins after averaging the two locked noises.', '']
    keys = [('seq24_gt_ge30.mae', 'Far MAE'), ('seq24_gt_ge30.signed_mean', 'Far signed error'),
            ('fragment32_rmsd', 'Fragment32 RMSD'), ('remainder95_rmsd_fixed_alignment', 'Remaining95% RMSD'),
            ('rg_ratio', 'Predicted/GT Rg')]
    for cohort in lock['cohort_order']:
        data = extent['summary'][cohort]
        lines += [f'### {cohort}', '', '|Model|Metric|Proteins|Mean|', '|---|---|---:|---:|']
        for model in lock['models']:
            for key, label in keys:
                v = data['models'][model][key]
                mean = 'NA' if v['mean'] is None else f"{v['mean']:.6f}"
                lines.append(f"|{model}|{label}|{v['proteins']}|{mean}|")
        lines += ['', '|Candidate − reference|Metric|Proteins|Mean Δ|95% CI|', '|---|---|---:|---:|---|']
        for pair in data['contrasts']:
            if pair['candidate'] != CANDIDATE:
                continue
            for key, label in keys:
                v = pair['metrics'][key]
                mean = 'NA' if v['mean'] is None else f"{v['mean']:+.6f}"
                ci = 'NA' if v['ci95'] is None else f"[{v['ci95'][0]:+.6f}, {v['ci95'][1]:+.6f}]"
                lines.append(f"|{CANDIDATE} − {pair['reference']}|{label}|{v['proteins']}|{mean}|{ci}|")
        lines.append('')
    return '\n'.join(lines)
