"""Original scorer plus per-noise geometry and paired arm summaries."""
import argparse
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path

from fastglycan.noise_lora import read_noise_lock, noise_index_for_exposure, noise_schedule_exposures
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.reference_editor_metrics import paired_parent_interval
from audit_recycle_lora import score_lora


def score_noise_lora(args):
    lock = read_noise_lock(args.root)
    folder = args.root/args.arm/'runs'/str(args.seed)
    history = [json.loads(s) for s in (folder/'history.jsonl').read_text().splitlines()]
    assert [r['step'] for r in history] == list(range(1,8209))
    exposure = Counter()
    for r in history:
        assert len(r['aa']) == len(r['noise_indices']) == 2
        for rank, (aa, ni) in enumerate(zip(r['aa'], r['noise_indices'])):
            assert ni == noise_index_for_exposure(args.arm, r['step']-1, rank)
            exposure[(r['site'], aa, ni)] += 1
    expected = noise_schedule_exposures(args.arm)
    assert len(exposure) == len(expected) and sorted(exposure.values()) == sorted(expected.values())
    train = json.loads((folder/'training_complete.json').read_text())
    assert train['complete'] and train['history_sha256'] == sha256(folder/'history.jsonl')
    assert train['noise_lock_sha256'] == sha256(args.root/'noise_lock.json')
    assert all(r['input_embedder'] == r['c4'] == 0 and r['recycle'] == r['s1'] == 8208 for r in train['rank_counts'])
    report = dict(complete=True, seed=args.seed, arm=args.arm,
        counts=dict(updates=8208, input_embedder=0, c4=0),
        evaluations=[{k:v for k,v in json.loads((folder/f'evaluation_{step}.json').read_text()).items()
                      if k != 'predictions'} for step in (0,4104,8208)],
        history_sha256=sha256(folder/'history.jsonl'), execution='paired_DDP_from_zero',
        noise_lock_sha256=sha256(args.root/'noise_lock.json'))
    write_json(folder/'report.json', report)
    score_lora(args.root/args.arm, args.seed)
    with gzip.open(folder/'scores.json.gz', 'rt') as stream:
        data = json.load(stream)
    by = {(r['label'],r['noise'],r['arm']):r for r in data['outputs']}
    names = {s['site_key']:s['pdb'] for s in data['sites']}
    groups = defaultdict(Counter)
    for row in data['outputs']:
        if row['arm'] not in ('disabled','4104_adapted','8208_adapted','exact'):
            continue
        g = row['geometry']
        for parent in ('ALL', names[row['site_key']]):
            c = groups[(row['role'],parent,row['noise'],row['arm'])]
            c.update(outputs=1, passed=int(g['zero_severe_strict_checked_chirality']),
                     severe_pairs=g['severe_pairs'], wrong_centres=g['checked_chirality_wrong'],
                     new_failures=int(row['disabled_pass_to_fail']), repairs=int(row['disabled_fail_to_pass']))
            old = by[row['label'],row['noise'],'disabled']['geometry']
            if not old['zero_severe_strict_checked_chirality']:
                c['already_failed_outputs'] += 1
                c['already_failed_severe_pairs'] += g['severe_pairs']
                c['already_failed_wrong_centres'] += g['checked_chirality_wrong']
    records = [dict(role=k[0],pdb=k[1],noise=k[2],checkpoint_arm=k[3],**v) for k,v in groups.items()]
    write_json(folder/'noise_audit.json', dict(complete=True, arm=args.arm, seed=args.seed,
        exposure_counts=[dict(site=k[0],aa=k[1],noise=lock['noises'][k[2]],count=v) for k,v in sorted(exposure.items())],
        geometry=records, second_noise_is_training_noise=args.arm=='dual',
        independent_confirmation=False, new_unseen_noise_test=False))
    # Each seed can be compared once both arms finish. No model selection.
    other = args.root/('dual' if args.arm=='single' else 'single')/'runs'/str(args.seed)
    if (other/'noise_audit.json').exists():
        values = {arm:json.loads((args.root/arm/'runs'/str(args.seed)/'summary.json').read_text()) for arm in lock['arms']}
        contrasts = {}
        for role in values['single']['summary']:
            contrasts[role] = {metric:paired_parent_interval(
                values['dual']['summary'][role]['8208_adapted']['parent_summaries'],
                values['single']['summary'][role]['8208_adapted']['parent_summaries'],metric)
                for metric in ('spearman','regret','centered_response_rmse')}
        write_json(args.root/f'paired_{args.seed}.json', dict(complete=True, contrasts=contrasts,
            promoted=False, independent_confirmation=False, primary_checkpoint=8208))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--arm',choices=['single','dual'],required=True)
    p.add_argument('--seed',type=int,required=True)
    score_noise_lora(p.parse_args())
