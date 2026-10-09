"""Descriptive, equal-parent summaries of every fixed recovery endpoint."""
import gzip
import json
from pathlib import Path

import numpy as np


def analyze_pair_recovery_results(root):
    lock = json.loads((root / 'training_lock.json').read_text())
    analyses = {}
    for seed in lock['seeds']:
        for initialization in lock['arms']:
            folder = root / 'runs' / initialization / str(seed)
            history = [json.loads(line) for line in (folder / 'history.jsonl').read_text().splitlines()]
            cycles = []
            for end in range(513, 8209, 513):
                hh = history[end - 513:end]
                cycles.append(dict(step=end, exposures_per_candidate=end * 2 // 513,
                                   weighted_loss=float(np.mean([r['loss'] for r in hh])),
                                   clipped_fraction=float(np.mean([r['clipped'] for r in hh])),
                                   gradient_norm_mean=float(np.mean([r['gradient_norm'] for r in hh]))))
            for step in lock['checkpoints']:
                with gzip.open(folder / f'scores_{step}.json.gz', 'rt') as handle:
                    score = json.load(handle)
                latent = json.loads((folder / f'evaluation_{step}.json').read_text())['latent']
                result = dict(initialization=initialization, seed=seed, step=step,
                              summary=score['summary'], contrasts=score['contrasts'],
                              latent={}, selections={}, worst_outputs={}, learning_cycles=cycles)
                for role in sorted({r['role'] for r in latent}):
                    ll = [r for r in latent if r['role'] == role]
                    parents = []
                    for parent in sorted({r['parent'] for r in ll}):
                        rr = [r for r in ll if r['parent'] == parent]
                        entry = dict(parent=parent, pdb=rr[0]['pdb'], sites=len(rr))
                        for mode in ('raw', 'common', 'centered'):
                            for field in ('nmse', 'cosine', 'energy_ratio'):
                                values = [r['moments'][mode][field] for r in rr if r['moments'][mode][field] is not None]
                                entry[f'{mode}_{field}'] = float(np.mean(values)) if values else None
                        energy_fractions = [r['moments']['common']['predicted_energy'] / r['moments']['raw']['predicted_energy']
                                            for r in rr if r['moments']['raw']['predicted_energy'] > 0]
                        entry['predicted_common_energy_fraction'] = float(np.mean(energy_fractions)) if energy_fractions else None
                        target_fractions = [r['moments']['common']['target_energy'] / r['moments']['raw']['target_energy']
                                            for r in rr if r['moments']['raw']['target_energy'] > 0]
                        entry['target_common_energy_fraction'] = float(np.mean(target_fractions)) if target_fractions else None
                        parents.append(entry)
                    pooled = dict(parents=len(parents), sites=len(ll), parent_summaries=parents,
                                  centered_improved_sites=sum(r['moments']['centered']['nmse'] is not None and
                                                             r['moments']['centered']['nmse'] < 1 for r in ll))
                    for key in parents[0]:
                        if key in ('parent', 'pdb', 'sites'):
                            continue
                        values = [r[key] for r in parents if r[key] is not None]
                        pooled[key] = float(np.mean(values)) if values else None
                    result['latent'][role] = pooled
                    sites = [r for r in score['sites'] if r['role'] == role]
                    lookup = {(r['site_key'], r['arm']): r for r in sites}
                    choices = []
                    for r in sites:
                        if r['arm'] != 'correct':
                            continue
                        baseline = lookup[r['site_key'], 'disabled']
                        exact = lookup[r['site_key'], 'exact']
                        oracle = lookup[r['site_key'], 'oracle_pair']
                        row = dict(site=r['site_key'], pdb=r['pdb'], position=r['position'] + 1,
                                   source=r['original_aa'], chosen=r['old_selected'], baseline_chosen=baseline['old_selected'],
                                   exact_chosen=exact['old_selected'], oracle_chosen=oracle['old_selected'],
                                   regret=r['old_select_new_regret'], baseline_regret=baseline['old_select_new_regret'],
                                   regret_change=r['old_select_new_regret'] - baseline['old_select_new_regret'],
                                   spearman=r['aggregate_ranking']['spearman'])
                        if step == 8208:
                            mismatch = lookup[r['site_key'], 'mismatched']
                            row.update(mismatch_chosen=mismatch['old_selected'], mismatch_regret=mismatch['old_select_new_regret'])
                        choices.append(row)
                    result['selections'][role] = choices
                    oo = sorted([r for r in score['outputs'] if r['role'] == role and r['arm'] == 'correct'],
                                key=lambda r: r['fidelity']['local_ca_rmsd_global_frame'], reverse=True)[:5]
                    result['worst_outputs'][role] = [dict(label=r['label'], noise=r['noise'],
                        local_rmsd=r['fidelity']['local_ca_rmsd_global_frame'], geometry=r['geometry'],
                        disabled_pass_to_fail=r['disabled_pass_to_fail']) for r in oo]
                analyses[f'{initialization}_{seed}_{step}'] = result
    paired = {}
    for seed in lock['seeds']:
        for step in lock['checkpoints']:
            a = analyses[f'pretrained_{seed}_{step}']
            b = analyses[f'random_{seed}_{step}']
            for role in a['summary']:
                pa = {r['parent']: r for r in a['summary'][role]['correct']['parent_summaries']}
                pb = {r['parent']: r for r in b['summary'][role]['correct']['parent_summaries']}
                assert set(pa) == set(pb)
                fields = {}
                for field in ('spearman', 'regret', 'centered_response_rmse'):
                    delta = np.array([pa[p][field] - pb[p][field] for p in sorted(pa)
                                      if pa[p][field] is not None and pb[p][field] is not None])
                    if not len(delta):
                        fields[field] = dict(mean=None, interval=None, parents=0, descriptive=True)
                        continue
                    rng = np.random.default_rng(275001)
                    samples = delta[rng.integers(len(delta), size=(10000, len(delta)))].mean(1)
                    fields[field] = dict(mean=float(delta.mean()), interval=np.quantile(samples, [.025, .975]).tolist(),
                                         parents=len(delta), descriptive=True)
                paired[f'{seed}_{step}_{role}'] = fields
    result = dict(complete=True, endpoints=analyses, pretrained_minus_random=paired,
                  all_panels_development=True, promoted=False)
    (root / 'analysis.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print('ANALYZED', len(analyses), 'fixed endpoints')


if __name__ == '__main__':
    analyze_pair_recovery_results(Path(__file__).resolve().parent)
