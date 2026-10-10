"""Recompute this fixed interim comparison; run from the repository root."""
import gzip
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path('src').resolve()))
from fastglycan.reference_editor_metrics import summarize_editor_sites, paired_parent_interval

root = Path(__file__).resolve().parent
control = Path('reports/mini_stage_fullbatch_2026-10-10/runs/adamw/272001/scores_32.json.gz')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
provenance = json.loads((root/'provenance.json').read_text())
assert provenance['complete'] and not provenance['full_experiment_complete']
for name, digest in provenance['outputs'].items():
    assert sha(root/Path(name).name) == digest
with gzip.open(root/'scores_32.json.gz', 'rt') as stream:
    new = json.load(stream)
with gzip.open(control, 'rt') as stream:
    old = json.load(stream)
assert new['seed'] == old['seed'] == 272001 and new['step'] == old['step'] == 32
assert new['scorer_sha256'] == old['scorer_sha256']
assert new['evaluation_sha256'] == provenance['evaluation_sha256']
assert len(new['sites']) == 48*4 and len(new['outputs']) == 48*19*2*4

# Compare unchanged reference arms row for row, including all geometry details.
for key in ('sites', 'outputs'):
    for arm in ('exact', 'disabled', 'oracle_pair'):
        assert [r for r in new[key] if r['arm'] == arm] == [r for r in old[key] if r['arm'] == arm]

panels = {}
for role in new['summary']:
    sites = [r for r in new['sites'] if r['role'] == role and r['arm'] == 'correct']
    outputs = [r for r in new['outputs'] if r['role'] == role and r['arm'] == 'correct']
    rebuilt = summarize_editor_sites(sites, outputs)
    rebuilt.update({k: sum(r[k] for r in outputs) for k in ('disabled_pass_to_fail', 'disabled_fail_to_pass')})
    rebuilt['severe_pairs'] = sum(r['geometry']['severe_pairs'] for r in outputs)
    rebuilt['wrong_centres'] = sum(r['geometry']['checked_chirality_wrong'] for r in outputs)
    assert rebuilt == new['summary'][role]['correct']
    old_summary = old['summary'][role]['correct']
    matched = {f: paired_parent_interval(rebuilt['parent_summaries'], old_summary['parent_summaries'], f)
               for f in ('spearman', 'regret', 'centered_response_rmse')}
    previous = {r['site_key']: r for r in old['sites'] if r['role'] == role and r['arm'] == 'correct'}
    exact = {r['site_key']: r for r in new['sites'] if r['role'] == role and r['arm'] == 'exact'}
    parent_sites = {p: sum(s['parent'] == p for s in sites) for p in {s['parent'] for s in sites}}
    changes = []
    for site in sites:
        key = site['site_key']; before = previous[key]
        row_outputs = [r for r in outputs if r['site_key'] == key]
        noises = sorted({r['noise'] for r in row_outputs}); assert len(noises) == 2
        choices = [r['aa'] for r in row_outputs if r['noise'] == noises[0]]
        assert len(set(choices)) == 19
        tasks = np.asarray(site['tasks']); teacher = np.asarray(exact[key]['tasks'])
        for ni, noise in enumerate(noises):
            assert np.array_equal(tasks[ni], [r['task'] for r in row_outputs if r['noise'] == noise])
        selected = int(np.argmin(tasks[0]))
        assert choices[selected] == site['old_selected']
        assert float(teacher[1, selected] - teacher[1].min()) == site['old_select_new_regret']
        if site['old_selected'] != before['old_selected']:
            delta = site['old_select_new_regret'] - before['old_select_new_regret']
            changes.append(dict(site=key, pdb=site['pdb'], position=site['position']+1,
                original=site['original_aa'], before=before['old_selected'], after=site['old_selected'],
                old_regret=before['old_select_new_regret'], new_regret=site['old_select_new_regret'],
                mean_contribution=delta/len(parent_sites)/parent_sites[site['parent']]))
    assert np.isclose(sum(r['mean_contribution'] for r in changes), rebuilt['regret']-old_summary['regret'], atol=1e-14)
    old_outputs = {(r['label'], r['noise']): r for r in old['outputs'] if r['role'] == role and r['arm'] == 'correct'}
    good = lambda r: r['geometry']['zero_severe_strict_checked_chirality']
    transitions = dict(pass_to_fail=sum(good(old_outputs[r['label'], r['noise']]) and not good(r) for r in outputs),
                       fail_to_pass=sum(not good(old_outputs[r['label'], r['noise']]) and good(r) for r in outputs))
    assert old_summary['geometry_pass']-transitions['pass_to_fail']+transitions['fail_to_pass'] == rebuilt['geometry_pass']
    parent_comparison = []
    old_parents = {p['parent']: p for p in old_summary['parent_summaries']}
    for p in rebuilt['parent_summaries']:
        parent_comparison.append(dict(parent=p['parent'], pdb=next(s['pdb'] for s in sites if s['parent'] == p['parent']),
            differences={k: p[k]-old_parents[p['parent']][k] for k in ('spearman','regret','centered_response_rmse')}))
    panels[role] = dict(matched_control=old_summary, anchored=rebuilt, contrasts=matched,
        selection_changes=changes, geometry_transitions_from_control=transitions, parent_comparison=parent_comparison)
result = dict(seed=272001, step=32, interim=True, promoted=False, independent_confirmation=False,
    native_tensor_verification_pending=True, source_sha256=sha(root/'scores_32.json.gz'),
    historical_control_sha256=sha(control), aggregation_code_sha256=sha(Path('src/fastglycan/reference_editor_metrics.py')),
    analysis_code_sha256=sha(Path(__file__)), panels=panels)
(root/'functional_comparison.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
print(json.dumps({role: {k: v for k, v in row.items() if k not in ('matched_control','anchored','parent_comparison')}
                  for role, row in panels.items()}, indent=2))
