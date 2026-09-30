"""Readable terminal comparison without selecting a checkpoint or hiding tails."""


def render_folding_scale_report(lock, training, evaluation, cohorts):
    if not all(x.get('complete') for x in [training,evaluation,cohorts]):
        raise ValueError('incomplete inputs are not a terminal result')
    if evaluation['outputs']!=lock['planned_outputs'] or evaluation['proteins']!=len(lock['rows']):
        raise ValueError('output denominator differs from the frozen plan')
    counts={k:len(v) for k,v in lock['cohorts'].items()}
    if set(cohorts['summary'])!=set(counts) or any(cohorts['summary'][k]['proteins']!=n for k,n in counts.items()):
        raise ValueError('cohort denominator differs from the frozen plan')
    lines=['# C4/S1 fixed-terminal folding comparison','',
        'Frozen ESM2 + C4 conditioning; only the native diffusion parameters were trained. '
        'Both arms start from the retained checkpoint, reset optimizer state and receive '
        '2048 new updates / 8192 new exposures. This is not training from zero.','',
        'Scores use observed experimental GT. Each protein contributes the mean of its two '
        'fixed noises; no best-of-noise or intermediate-checkpoint selection. Geometry '
        'counts describe the explicit severe-collision and checked-stereocentre criteria, '
        'not comprehensive chemical correctness or deployment approval.','']
    for cohort in ['new_validation32','original_train128','added_train295']:
        if cohort not in counts:continue
        c=cohorts['summary'][cohort];n=c['proteins']
        lines.extend([f'## {cohort}: {n} proteins','',
            '|Model|AA-lDDT|Cα-lDDT|Zero severe + strict stereo, instances|Both noises, proteins|Severe pairs total|',
            '|---|---:|---:|---:|---:|---:|'])
        for model in lock['models']:
            m=c['models'][model]
            lines.append(f"|{model}|{m['mean_aa']:.6f}|{m['mean_ca']:.6f}|"
                f"{m['zero_and_strict_instances']}/{m['instances']}|{m['zero_and_strict_both_noises']}/{n}|{m['severe_pairs']}|")
        lines.extend(['','Positive quality differences favor the candidate. Intervals resample proteins, '
            'conditional on the two locked noises; they do not establish independence from pretraining.','',
            '|Candidate − reference|Metric|Mean Δ|95% CI|P01 Δ|P05 Δ|Worst5% Δ mean|Δ < −0.05, proteins|',
            '|---|---|---:|---|---:|---:|---:|---:|'])
        for pair in c['contrasts']:
            for metric,short in [('all_atom_lddt','AA'),('ca_lddt','Cα')]:
                q=pair['quality'][metric];lo,hi=q['ci95']
                lines.append(f"|{pair['candidate']} − {pair['reference']}|{short}|{q['mean']:+.6f}|"
                    f"[{lo:+.6f}, {hi:+.6f}]|{q['p01']:+.6f}|{q['p05']:+.6f}|{q['worst5_mean']:+.6f}|{q['below_minus_005']}/{n}|")
        lines.extend(['','|Candidate − reference|New severe collision instances from zero|Lost strict stereo instances|',
            '|---|---:|---:|'])
        for p in c['contrasts']:
            lines.append(f"|{p['candidate']} − {p['reference']}|{p['introduced_severe_on_zero_instances']}|{p['lost_strict_chirality_instances']}|")
        if c.get('strata'):
            lines.extend(['','Descriptive length/assembly subsets; overlapping views, not additional independent tests.','',
                '|Subset|Proteins|Candidate − reference|Mean AA Δ|Mean Cα Δ|','|---|---:|---|---:|---:|'])
            for name,s in c['strata'].items():
                for p in s['paired']:
                    lines.append(f"|{name}|{s['proteins']}|{p['candidate']} − {p['reference']}|{p['mean_delta_aa']:+.6f}|{p['mean_delta_ca']:+.6f}|")
        lines.append('')
    lines.extend(['## Matched original-TRAIN32 learning curves','',
        'These are training probes, not validation learning curves. The expanded arm exposes '
        'each original protein less often at equal total updates.','',
        '|Arm|New update|AA-lDDT|Cα-lDDT|Zero severe + strict stereo / 64|Severe pairs|',
        '|---|---:|---:|---:|---:|---:|'])
    for arm,s in training['summary'].items():
        for c in s['curves']:
            lines.append(f"|{arm}|{c['update']}|{c['all_atom_lddt']:.6f}|{c['ca_lddt']:.6f}|{c['zero_and_strict']}/64|{c['severe_pairs']}|")
    lines.extend(['','## Cost and provenance','',
        '|Arm|Training seconds|Allocated peak GiB|Samples per protein, min–max|Clipped updates|',
        '|---|---:|---:|---|---:|'])
    for arm,s in training['summary'].items():
        lines.append(f"|{arm}|{s['seconds']:.1f}|{s['peak_gpu_bytes']/2**30:.3f}|{s['exposure_min']}–{s['exposure_max']}|{s['clipped_updates']}|")
    lines.extend(['',f"Complete outputs: **{evaluation['outputs']}** over **{evaluation['proteins']} proteins**. "
        f"New evaluation prediction NFEs: **{sum(evaluation['counts'].values())}**; engineering probes: **{evaluation['probe_nfe']}**. "
        f"Independent dense-distance metric maximum absolute discrepancy: **{evaluation['metric_max_abs']:.3g}**.",'',
        'Inference timings in evaluation.json cover diffusion with cached conditioning only. '
        'They omit live ESM2 and Pairformer, and are not end-to-end folding speed. Equal '
        'updates/exposures are not equal GPU time, FLOPs, or per-protein exposure.','',
        'Original128, added295 and new validation32 remain distinct cohorts. Most sources '
        'are complete single chains extracted from homooligomers. The scope is supported '
        'single-chain prediction; assembly context and pretraining exposure remain limitations.','',
        'No model is automatically promoted by this report. Review mean quality, paired tails '
        'and newly introduced chemical failures jointly. This experiment does not establish '
        'BindCraft utility, binding affinity or a gradient through a changed output function.',''])
    return '\n'.join(lines)
