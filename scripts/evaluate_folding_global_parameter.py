#!/usr/bin/env python3
"""Release and score one fixed candidate with six hash-audited reference models."""
import argparse
import copy
import csv
import json
import subprocess
from pathlib import Path

from fastglycan.folding_parameter_evaluation import (
    CANDIDATE, REFERENCES, REFERENCE_LOCK_SHA256, REFERENCE_EVALUATION_SHA256,
    make_parameter_evaluation_lock, render_parameter_extent,
)
from fastglycan.global_parameter_training import BASE_LOCK_SHA256, verify_parameter_weight_lock
from fastglycan.paired_teacher_protocol import sha256, write_json


def prepare_parameter_evaluation(root):
    assert not (root/'lock.json').exists(), 'preserve the frozen evaluation'
    train = root.parent/'folding_global_parameter_training_v1_20260930'
    old = root.parent/'folding_global_distance_evaluation_v1_20260930'
    baseline = root.parent/'folding_global_distance_training_v1_20260930'
    assert sha256(baseline/'lock.json') == BASE_LOCK_SHA256
    tl = json.loads((train/'lock.json').read_text())
    verify_parameter_weight_lock(tl, json.loads((baseline/'lock.json').read_text()))
    audit_path = train/'parameter_weight_training_audit.json'
    audit = json.loads(audit_path.read_text())
    assert all(audit[k] for k in ['complete', 'same_start', 'same_exposure_order', 'initial_probe_replay_exact'])
    assert audit['lock_sha256'] == sha256(train/'lock.json')
    assert sha256(Path(audit['checkpoint']['path'])) == audit['checkpoint']['sha256']
    assert sha256(old/'lock.json') == REFERENCE_LOCK_SHA256
    assert sha256(old/'evaluation.json') == REFERENCE_EVALUATION_SHA256
    prior = json.loads((old/'lock.json').read_text())
    execution = json.loads((old/'execution.json').read_text())
    assert execution['complete'] and execution['lock_sha256'] == REFERENCE_LOCK_SHA256
    assert prior['rows'] == tl['rows'] and prior['models'] == REFERENCES
    trusted = {}
    inputs = dict(prior['input_hashes'])
    for worker in execution['workers']:
        p = old/f'worker_{worker["index"]}/report.json'
        assert worker['exit_code'] == 0 and sha256(p) == worker['report_sha256']
        report = json.loads(p.read_text())
        assert report['complete'] and report['lock_sha256'] == REFERENCE_LOCK_SHA256
        for row in report['rows']:
            assert row['group_id'] not in trusted
            trusted[row['group_id']] = row
        inputs[str(p)] = sha256(p)
    assert set(trusted) == {r['group_id'] for r in prior['rows']}
    for row in prior['rows']:
        g = row['group_id']; p = old/'examples'/g/'report.json'
        report = json.loads(p.read_text()); assert report == trusted[g]
        seeds = prior['train_seeds'] if row['role'] == 'train' else prior['validation_seeds']
        assert len(report['entries']) == 12
        assert {(e['model'], e['seed']) for e in report['entries']} == {(m, s) for m in REFERENCES for s in seeds}
        for entry in report['entries']:
            assert entry['name'] == f'{entry["model"]}_seed{entry["seed"]}.npy'
            pcoord = p.parent/entry['name']; assert sha256(pcoord) == entry['sha256']
            inputs[str(pcoord)] = entry['sha256']
        inputs[str(p)] = sha256(p)
        for f in [Path(prior['source'])/'chemistry'/g/'mapping.npz',
                  Path(prior['source'])/'chemistry'/g/'native.pt',
                  Path(prior['source'])/'data/examples'/g/'gt.npz']:
            assert sha256(f) == inputs[str(f)]
    for p in [train/'lock.json', audit_path, baseline/'lock.json', baseline/'global_training_audit.json',
              old/'lock.json', old/'execution.json', old/'evaluation.json', old/'final/training_comparison.json']:
        inputs[str(p)] = sha256(p)
    # The runner, checkpoint loaders and scorer are the already-executed versions.
    for f in ['models/differentiable_mini.py', 'models/diffusion_adapter.py', 'models/diffusion_scope.py',
              'models/soft_sequence_chart.py', 'folding_scale.py', 'diffusion_pilot_metrics.py']:
        assert sha256(root/'code/src/fastglycan'/f) == sha256(train/'code/src/fastglycan'/f), f
    for f in ['evaluate_diffusion_learning.py', 'score_diffusion_learning.py', 'evaluate_folding_scale.py',
              'analyze_folding_structure_extent.py']:
        assert sha256(root/'code/scripts'/f) == sha256(old/'code/scripts'/f), f
    hashes = {str(p): sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py', '.json', '.md']}
    lock = make_parameter_evaluation_lock(prior, train=train, reference_evaluation=old,
        checkpoint=audit['checkpoint'], training_lock_sha256=sha256(train/'lock.json'), selected_names=tl['selected_names'],
        hashes=hashes, input_hashes=inputs,
        protocol_sha256=sha256(root/'code/docs/mini_folding_global_parameter_evaluation_v1.md'))
    write_json(root/'lock.json', lock)
    write_json(root/'prepare.json', dict(complete=True, lock_sha256=sha256(root/'lock.json'), reused_coordinates=5460,
        new_prediction_nfe=910, engineering_nfe=32, planned_scored_outputs=6370))


def collect_parameter_evaluation(root):
    from evaluate_folding_scale import collect_folding_evaluation
    collect_folding_evaluation(root)
    lock = json.loads((root/'lock.json').read_text()); train = Path(lock['train'])
    probe = train/'expanded/probe_2048/report.json'
    records = json.loads(probe.read_text())['records']; assert len(records) == 64
    for record in records:
        g, seed = record['group_id'], record['seed']
        original = probe.parent/f'{g}_{seed}.npy'
        replay = root/'examples'/g/f'{CANDIDATE}_seed{seed}.npy'
        assert sha256(original) == record['sha256'] == sha256(replay), (g, seed)
    write_json(root/'terminal_replay.json', dict(complete=True, exact_coordinates=64,
        lock_sha256=sha256(root/'lock.json'), training_probe_sha256=sha256(probe)))



def score_parameter_evaluation(root, workers):
    from score_diffusion_learning import summarize_diffusion_evaluation
    from fastglycan.folding_evaluation import summarize_folding_cohorts
    lock = json.loads((root/'lock.json').read_text())
    replay = json.loads((root/'terminal_replay.json').read_text())
    assert replay['complete'] and replay['exact_coordinates'] == 64
    assert replay['lock_sha256'] == sha256(root/'lock.json')
    assert replay['training_probe_sha256'] == sha256(Path(lock['train'])/'expanded/probe_2048/report.json')
    summarize_diffusion_evaluation(root, workers)
    evaluation = json.loads((root/'evaluation.json').read_text())
    assert evaluation['complete'] and evaluation['outputs'] == 6370
    assert evaluation['lock_sha256'] == sha256(root/'lock.json')
    result = summarize_folding_cohorts(evaluation['records'], lock)
    write_json(root/'cohorts.json', dict(complete=True, evaluation_sha256=sha256(root/'evaluation.json'), **result))


def parameter_evaluation_extent(root, workers):
    from analyze_folding_structure_extent import summarize_structure_extent
    lock = json.loads((root/'lock.json').read_text())
    execution = json.loads((root/'execution.json').read_text())
    evaluation = json.loads((root/'evaluation.json').read_text())
    assert execution['complete'] and evaluation['complete'] and evaluation['outputs'] == 6370
    assert execution['lock_sha256'] == evaluation['lock_sha256'] == sha256(root/'lock.json')
    destination = root/'extent'; destination.mkdir(exist_ok=False)
    hashes = {str(p): sha256(p) for p in [root/'lock.json', root/'execution.json', root/'evaluation.json']}
    hashes.update(lock['hashes']); trusted = {}
    for worker in execution['workers']:
        p = root/f'worker_{worker["index"]}/report.json'
        assert sha256(p) == worker['report_sha256']; hashes[str(p)] = sha256(p)
        for row in json.loads(p.read_text())['rows']:
            assert row['group_id'] not in trusted
            trusted[row['group_id']] = row
    examples, rmsd = {}, {}
    for row in lock['rows']:
        g = row['group_id']; p = root/'examples'/g/'report.json'
        assert json.loads(p.read_text()) == trusted[g]; examples[g] = sha256(p)
    for x in evaluation['records']:
        rmsd.setdefault(x['group_id'], {}).setdefault(x['model'], {})[str(x['seed'])] = x['ca_aligned_rmsd']
    write_json(destination/'manifest.json', dict(evaluation_root=str(root), evaluation_lock_sha256=sha256(root/'lock.json'),
        hashes=hashes, example_reports=examples, rmsd=rmsd, diagnostic_candidate=CANDIDATE, diagnostic_reference='global_distance'))
    del evaluation
    summarize_structure_extent(destination, workers)


def report_parameter_evaluation(root):
    from fastglycan.folding_report import render_folding_scale_report
    from fastglycan.folding_global_metrics import summarize_global_structure
    lock = json.loads((root/'lock.json').read_text()); train = Path(lock['train']); old = Path(lock['reference_evaluation'])
    bound = [train/'lock.json', train/'parameter_weight_training_audit.json', old/'final/training_comparison.json']
    for p in bound:
        assert sha256(p) == lock['input_hashes'][str(p)]
    audit = json.loads(bound[1].read_text()); assert audit['complete']
    training = copy.deepcopy(json.loads(bound[2].read_text())); assert training['complete']
    tr_path = train/'expanded/report.json'; history = train/'expanded/history.jsonl'
    tr = json.loads(tr_path.read_text())
    assert tr['complete'] and tr['lock_sha256'] == sha256(train/'lock.json')
    assert sha256(history) == tr['history_sha256']
    clipped = sum(x.get('unclipped_accumulated_grad_norm', 0) > 1 for x in map(json.loads, history.read_text().splitlines()))
    training['summary'][CANDIDATE] = {**audit, 'clipped_updates': clipped}
    evaluation = json.loads((root/'evaluation.json').read_text())
    cohorts = json.loads((root/'cohorts.json').read_text())
    replay = json.loads((root/'terminal_replay.json').read_text())
    assert replay['complete'] and replay['exact_coordinates'] == 64 and replay['lock_sha256'] == sha256(root/'lock.json')
    assert evaluation['complete'] and evaluation['lock_sha256'] == sha256(root/'lock.json')
    assert cohorts['evaluation_sha256'] == sha256(root/'evaluation.json')
    assert evaluation['counts'] == {'native': 0, CANDIDATE: 910} and evaluation['probe_nfe'] == 32
    submission = json.loads((root/'submission.json').read_text()); jobs = [submission['score_job'], submission['extent_job']]
    raw = subprocess.check_output(['sacct', '-j', ','.join(jobs), '-n', '-X', '-P', '--format=JobIDRaw,State,ExitCode'], text=True)
    states = {p[0]: p[1:3] for line in raw.splitlines() if len(p := line.split('|')) >= 3}
    assert all(states.get(j) == ['COMPLETED', '0:0'] for j in jobs)
    extent = json.loads((root/'extent/report.json').read_text())
    em = json.loads((root/'extent/manifest.json').read_text())
    assert extent['manifest_sha256'] == sha256(root/'extent/manifest.json')
    assert em['hashes'][str(root/'evaluation.json')] == sha256(root/'evaluation.json') and extent['rmsd_replay_max'] < 1e-8
    global_structure = summarize_global_structure(evaluation['records'], lock)
    text = render_folding_scale_report(lock, training, evaluation, cohorts)+'\n'+global_structure.pop('markdown')+'\n'+render_parameter_extent(extent, lock)
    output = root/'final'; output.mkdir(exist_ok=False); (output/'report.md').write_text(text)
    write_json(output/'global_structure.json', dict(evaluation_sha256=sha256(root/'evaluation.json'), **global_structure))
    with (output/'paired.csv').open('w', newline='') as f:
        fields = ['cohort', 'group_id', 'pdb_id', 'length', 'candidate', 'reference', 'delta_aa', 'delta_ca', 'per_noise']
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator='\n'); writer.writeheader()
        lookup = {r['group_id']: r for r in lock['rows']}
        for row in cohorts['paired']:
            writer.writerow(dict(row, pdb_id=lookup[row['group_id']]['pdb_id'], per_noise=json.dumps(row['per_noise'], sort_keys=True)))
    write_json(output/'training_comparison.json', training)
    paths = bound+[tr_path, history, root/'lock.json', root/'execution.json', root/'evaluation.json', root/'cohorts.json',
        root/'terminal_replay.json', root/'extent/report.json', root/'extent/manifest.json']
    write_json(output/'provenance.json', dict(complete=True, jobs=jobs, scheduler=raw,
        inputs={str(p): sha256(p) for p in paths}, outputs={p.name: sha256(p) for p in output.iterdir() if p.is_file()},
        script_sha256=sha256(Path(__file__)), scope='fixed terminal; no automatic model promotion'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--mode', choices=['prepare', 'collect', 'score', 'extent', 'report'], required=True)
    parser.add_argument('--workers', type=int, default=8); args = parser.parse_args(); root = args.root.resolve()
    if args.mode == 'prepare': prepare_parameter_evaluation(root)
    elif args.mode == 'collect': collect_parameter_evaluation(root)
    elif args.mode == 'score': score_parameter_evaluation(root, args.workers)
    elif args.mode == 'extent': parameter_evaluation_extent(root, args.workers)
    else: report_parameter_evaluation(root)
