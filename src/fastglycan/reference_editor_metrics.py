"""Post-hoc structure/response summaries with parent-level experimental units."""
import numpy as np


def distance_response_summary(exact, approximate, reference):
    """Inputs: candidate-by-common-CA-distance arrays and same-noise WT distances.

    Centre over candidates, never over pairs or channels. No teacher statistic
    is used by the predictor; these are evaluation diagnostics only.
    """
    exact, approximate, reference = map(lambda x: np.asarray(x, dtype=np.float64),
                                         (exact, approximate, reference))
    if exact.shape != approximate.shape or exact.ndim != 2 or reference.shape != exact.shape[1:]:
        raise ValueError('common CA distance shapes differ')
    if not all(np.isfinite(x).all() for x in (exact, approximate, reference)):
        raise ValueError('nonfinite distance response')
    teacher, predicted = exact-reference, approximate-reference
    tm, pm = teacher.mean(0), predicted.mean(0)
    tc, pc = teacher-tm, predicted-pm
    energy = float(np.mean(tc**2))
    error = float(np.mean((pc-tc)**2))
    return dict(mean_response_distance_rmse=float(np.sqrt(np.mean((pm-tm)**2))),
                centered_response_distance_rmse=float(np.sqrt(error)),
                centered_response_nmse=error/energy if energy > 1e-12 else None,
                teacher_mean_response_energy=float(np.mean(tm**2)),
                predicted_mean_response_energy=float(np.mean(pm**2)),
                teacher_centered_response_energy=energy,
                predicted_centered_response_energy=float(np.mean(pc**2)))


def summarize_editor_sites(sites, outputs):
    """Ranking/regret/means are equal-weight parent averages; tails are pooled.

    Counts retain their actual mutant/noise denominators, not an independence
    claim. Missing Spearman from tied predictions is counted explicitly.
    """
    if not sites:
        raise ValueError('empty evaluation stratum')
    fields = dict(spearman=lambda r: r['aggregate_ranking']['spearman'],
                  old_spearman=lambda r: r['ranking'][0]['spearman'],
                  new_spearman=lambda r: r['ranking'][1]['spearman'],
                  regret=lambda r: r['old_select_new_regret'],
                  score_mae=lambda r: np.mean([x['task_mae'] for x in r['ranking']]),
                  top3_recall=lambda r: r['aggregate_ranking']['top3_recall'],
                  top5_recall=lambda r: r['aggregate_ranking']['top5_recall'],
                  local_mean=lambda r: r['local_mean'], aa_lddt=lambda r: r['aa_lddt'],
                  ca_lddt=lambda r: r['ca_lddt'],
                  centered_response_rmse=lambda r: np.mean([x['centered_response_distance_rmse'] for x in r['response']]))
    parents = sorted({r['parent'] for r in sites})
    rows = []
    for parent in parents:
        group = [r for r in sites if r['parent'] == parent]
        row = dict(parent=parent, sites=len(group))
        for name, getter in fields.items():
            values = [getter(r) for r in group]
            valid = [v for v in values if v is not None]
            row[name] = float(np.mean(valid)) if valid else None
        rows.append(row)
    result = dict(parents=len(parents), sites=len(sites), parent_summaries=rows,
                  undefined_spearman_sites=sum(r['aggregate_ranking']['spearman'] is None for r in sites))
    for name in fields:
        values = [r[name] for r in rows if r[name] is not None]
        result[name] = float(np.mean(values)) if values else None
    regrets = [r['regret'] for r in rows]
    result.update(regret_parent_median=float(np.median(regrets)), regret_parent_max=float(max(regrets)),
                  top1=sum(r['aggregate_ranking']['top1_match'] for r in sites))
    local = np.array([r['fidelity']['local_ca_rmsd_global_frame'] for r in outputs])
    result.update(outputs=len(outputs), local_p95=float(np.quantile(local, .95)),
                  local_p99=float(np.quantile(local, .99)), local_max=float(local.max()),
                  local_over1=int((local > 1).sum()),
                  geometry_pass=sum(r['geometry']['zero_severe_strict_checked_chirality'] for r in outputs),
                  exact_pass_to_fail=sum(r['exact_pass_to_fail'] for r in outputs),
                  exact_fail_to_pass=sum(r['exact_fail_to_pass'] for r in outputs),
                  reference_pass_to_fail=sum(r['reference_pass_to_fail'] for r in outputs),
                  reference_fail_to_pass=sum(r['reference_fail_to_pass'] for r in outputs))
    return result


def paired_parent_interval(first, second, field, seed=275001, draws=10000):
    """Descriptive paired bootstrap, never treating AA/noise as new proteins."""
    a = {r['parent']: r[field] for r in first}
    b = {r['parent']: r[field] for r in second}
    if set(a) != set(b):
        raise ValueError('paired parent sets differ')
    differences = np.array([a[k]-b[k] for k in sorted(a) if a[k] is not None and b[k] is not None])
    if not len(differences):
        return dict(parents=0, mean=None, interval=None)
    rng = np.random.default_rng(seed)
    samples = differences[rng.integers(len(differences), size=(draws, len(differences)))].mean(1)
    return dict(parents=len(differences), mean=float(differences.mean()),
                interval=np.quantile(samples, [.025, .975]).tolist(), descriptive=True)
