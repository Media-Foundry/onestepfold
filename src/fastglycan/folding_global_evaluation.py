"""Explicit six-model terminal contract and existing-coordinate diagnostics."""
import copy
from .evaluation_reuse import expected_evaluation_calls

REFERENCE_MODELS = ['native_s1','native_s2','retained','expanded','coordinate_zero']
CANDIDATE = 'global_distance'


def make_global_distance_evaluation_lock(prior, *, train, control, reference_evaluation, checkpoint,
        training_lock_sha256, selected_names, hashes, input_hashes, protocol_sha256):
    if prior['models']!=REFERENCE_MODELS:raise ValueError('unexpected reference models')
    lock=copy.deepcopy(prior)
    lock.update(schema='folding_global_distance_evaluation_v1',train=str(train),control=str(control),reference_evaluation=str(reference_evaluation),
        checkpoints={CANDIDATE:copy.deepcopy(checkpoint)},checkpoint_training_locks={CANDIDATE:training_lock_sha256},
        checkpoint_arms={CANDIDATE:'expanded'},selected_names={CANDIDATE:list(selected_names)},
        reuse_models={m:dict(root=str(reference_evaluation)+'/examples',model=m,roles=['train','validation']) for m in REFERENCE_MODELS},
        models=REFERENCE_MODELS+[CANDIDATE],hashes=copy.deepcopy(hashes),input_hashes=copy.deepcopy(input_hashes),
        contrasts=[[CANDIDATE,m] for m in ['coordinate_zero','expanded','retained','native_s1','native_s2']]
            +[['coordinate_zero','expanded'],['expanded','retained'],['native_s2','native_s1']],
        primary='global_distance versus coordinate_zero AND expanded; observed DEV32 is development evidence',
        planned_outputs=5460,planned_prediction_nfe=910,planned_probe_nfe=32,protocol_sha256=protocol_sha256,
        report_title='# C4/S1 experimental global-distance candidate: fixed terminal',
        report_intro='All three TRAIN423 continuations start at the same retained512 checkpoint and use the same '
            '8192 ordered exposures / 2048 updates. The new candidate adds experimental global CA distance '
            'supervision to the coordinate-zero recipe, at a fixed TRAIN-calibrated weight. Native S2 remains '
            'auxiliary synthetic supervision, not experimental GT. Frozen ESM2/C4, native FP32, C4/S1/K1.',
        training_curve_note='Matched original-TRAIN32 probes; same training membership, order, noises and per-protein exposure. No checkpoint selection.')
    if len(lock['rows'])!=455 or sum(map(len,lock['cohorts'].values()))!=455:raise ValueError('unexpected cohort size')
    if expected_evaluation_calls(lock,lock['rows'])!=dict(native=0,global_distance=910):raise ValueError('incorrect new call budget')
    if len(lock['assignments'])!=8 or 8*(1+3*len(lock['checkpoints']))!=32:raise ValueError('incorrect engineering budget')
    return lock


def render_global_distance_extent(extent, lock):
    if not extent.get('complete') or extent['outputs']!=lock['planned_outputs'] or extent['proteins']!=455:
        raise ValueError('incomplete global-distance diagnostic')
    if extent.get('diagnostic_candidate')!=CANDIDATE or extent.get('diagnostic_reference')!='coordinate_zero':
        raise ValueError('wrong primary extent comparison')
    lines=['## Existing-coordinate distance and error-extent diagnostics','',
        'No new inference. Observed CA identities/GT are unchanged; whole-chain RMSD is independently replayed. '
        'Far pairs have sequence separation ≥24 and experimental distance ≥30 Å. Positive MAE/fragment RMSD '
        'changes are worse. Negative signed distance error means underestimation, not improvement. '
        'Radius-of-gyration ratio has no universal better direction. Empty bands remain null, with valid-protein '
        'counts. These are descriptive diagnostics, not extra independent confirmations.','']
    keys=[('seq24_gt_ge30.mae','Far MAE (Å)'),('seq24_gt_ge30.signed_mean','Far signed error (Å)'),
          ('remainder95_rmsd_fixed_alignment','Remaining95% RMSD (Å)'),('fragment32_rmsd','Fragment32 RMSD (Å)'),('rg_ratio','Predicted/GT Rg')]
    for cohort in lock['cohort_order']:
        data=extent['summary'][cohort]
        lines.extend([f'### {cohort}','', '|Model|Metric|Proteins with support|Mean|','|---|---|---:|---:|'])
        for model in lock['models']:
            for key,label in keys:
                v=data['models'][model][key];value='NA' if v['mean'] is None else f"{v['mean']:.6f}"
                lines.append(f"|{model}|{label}|{v['proteins']}|{value}|")
        lines.extend(['','|Candidate − reference|Metric|Proteins|Mean Δ|95% CI|','|---|---|---:|---:|---|'])
        for pair in data['contrasts']:
            if pair['candidate']!=CANDIDATE:continue
            for key,label in keys:
                v=pair['metrics'][key]
                value='NA' if v['mean'] is None else f"{v['mean']:+.6f}"
                ci='NA' if v['ci95'] is None else f"[{v['ci95'][0]:+.6f}, {v['ci95'][1]:+.6f}]"
                lines.append(f"|{pair['candidate']} − {pair['reference']}|{label}|{v['proteins']}|{value}|{ci}|")
        lines.append('')
    return '\n'.join(lines)
