#!/usr/bin/env python3
"""Fixed 455-protein terminal comparison, using the unchanged inference/scoring paths."""
import argparse
import json
import shutil
from pathlib import Path
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.rocm_evaluation import make_rocm_evaluation_lock
from fastglycan.folding_parameter_evaluation import REFERENCE_LOCK_SHA256
from fastglycan.evaluation_reuse import expected_evaluation_calls


def prepare_rocm_evaluation(root):
    assert not (root/'lock.json').exists()
    train = root.parent/'rocm_matched_training_v1_20261001'
    old = root.parent/'folding_global_distance_evaluation_v1_20260930'
    assert sha256(old/'lock.json') == REFERENCE_LOCK_SHA256
    prior = json.loads((old/'lock.json').read_text())
    audit = json.loads((train/'terminal_audit.json').read_text())
    assert audit['complete'] and audit['same_exposure_order'] and audit['initial_probe_exact_coordinates'] == 64
    inputs = {}
    for arm in ['weak','strong']:
        tl = json.loads((train/arm/'lock.json').read_text())
        assert audit['training_locks'][arm] == sha256(train/arm/'lock.json')
        assert prior['rows'] == tl['rows']
        assert sha256(Path(audit['checkpoints'][arm]['path'])) == audit['checkpoints'][arm]['sha256']
        for file in [train/arm/'lock.json', train/arm/'expanded/probe_2048/report.json']:
            inputs[str(file)] = sha256(file)
    # Match all actual coordinate/GT/chemistry/conditioning inputs; do not rescore old CUDA outputs.
    cache, source = Path(prior['cache']), Path(prior['source'])
    for row in prior['rows']:
        g = row['group_id']
        for p in [cache/'examples'/g/'conditioning.pt',source/'chemistry'/g/'native.pt',
                  source/'chemistry'/g/'mapping.npz',source/'data/examples'/g/'gt.npz']:
            digest = sha256(p); assert digest == prior['input_hashes'][str(p)], p
            inputs[str(p)] = digest
    # Explicit same-platform public anchor; never alter the historical CUDA cache.
    weak = json.loads((train/'weak/lock.json').read_text())
    g = weak['engineering_groups'][0]
    probe = next(r for r in prior['rows'] if r['group_id'] == g)
    assert probe['role'] == 'train'
    reference = weak['backend']['engineering_references'][g]
    assert sha256(Path(reference['report'])) == reference['sha256']
    for p in [Path(reference['public']),Path(reference['report'])]:
        assert sha256(p) == weak['hashes'][str(p)]; inputs[str(p)] = sha256(p)
    destination = root/'probe_cache/examples'/g; destination.mkdir(parents=True,exist_ok=False)
    for src,name in [(cache/'examples'/g/'conditioning.pt','conditioning.pt'),
                     (Path(reference['public']),'s1_seed600001.npy')]:
        shutil.copyfile(src,destination/name); assert sha256(src) == sha256(destination/name)
        inputs[str(destination/name)] = sha256(destination/name)
    for p in [old/'lock.json',train/'terminal_audit.json',train/'execution.json']:
        inputs[str(p)] = sha256(p)
    for f in ['evaluate_diffusion_learning.py','score_diffusion_learning.py','analyze_folding_structure_extent.py']:
        assert sha256(root/'code/scripts'/f) == sha256(old/'code/scripts'/f)
    for f in ['models/differentiable_mini.py','models/diffusion_scope.py','folding_scale.py','diffusion_pilot_metrics.py']:
        assert sha256(root/'code/src/fastglycan'/f) == sha256(train/'weak/code/src/fastglycan'/f)
    hashes = {str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.json','.md']}
    lock = make_rocm_evaluation_lock(prior,train=train,checkpoints=audit['checkpoints'],
        training_locks=audit['training_locks'],selected_names=weak['selected_names'],hashes=hashes,
        input_hashes=inputs,protocol_sha256=sha256(root/'code/docs/mini_folding_rocm_evaluation_v1.md'))
    lock.update(probe=probe,probe_cache=str(root/'probe_cache'),probe_source=str(source),
        backend=weak['backend'],anchor_note='Public Mini ROCm diagnostic; original CUDA cache remains unchanged')
    write_json(root/'lock.json',lock)
    write_json(root/'prepare.json',dict(complete=True,lock_sha256=sha256(root/'lock.json'),
        outputs=1820,prediction_nfe=1820,engineering_nfe=56,workers=8))


def collect_rocm_evaluation(root):
    lock = json.loads((root/'lock.json').read_text())
    controller = json.loads((root/'inference_execution.json').read_text())
    assert controller['complete'] and len(controller['jobs']) == 8
    assert controller['lock_sha256'] == sha256(root/'lock.json')
    assert sorted(j['index'] for j in controller['jobs']) == list(range(8))
    workers = []; seen = set()
    for job in controller['jobs']:
        i = job['index']; assert job['exit_code'] == 0
        p = root/f'worker_{i}/report.json'; report = json.loads(p.read_text())
        assert report['complete'] and report['lock_sha256'] == sha256(root/'lock.json')
        assert report['calls'] == expected_evaluation_calls(lock,lock['assignments'][i])
        assert report['probe_nfe'] == 7 and all(all(v.values()) for v in report['probe'].values())
        assert [r['group_id'] for r in report['rows']] == [r['group_id'] for r in lock['assignments'][i]]
        for row in report['rows']:
            g = row['group_id']; assert g not in seen; seen.add(g)
            assert json.loads((root/'examples'/g/'report.json').read_text()) == row
            for e in row['entries']:
                assert sha256(root/'examples'/g/e['name']) == e['sha256']
        workers.append(dict(index=i,pid=job['pid'],exit_code=0,report_sha256=sha256(p)))
    assert seen == {r['group_id'] for r in lock['rows']}
    # Replaying both training terminals protects checkpoint identity and inference parity.
    replay = {}
    for arm in ['weak','strong']:
        probe = Path(lock['train'])/arm/'expanded/probe_2048/report.json'
        assert sha256(probe) == lock['input_hashes'][str(probe)]
        records = json.loads(probe.read_text())['records']; assert len(records) == 64
        for r in records:
            original = probe.parent/f'{r["group_id"]}_{r["seed"]}.npy'
            new = root/'examples'/r['group_id']/f'{arm}_seed{r["seed"]}.npy'
            assert sha256(new) == sha256(original) == r['sha256'], (arm,r['group_id'],r['seed'])
        replay[arm] = dict(exact_coordinates=64,training_probe_sha256=sha256(probe))
    write_json(root/'terminal_replay.json',dict(complete=True,arms=replay,lock_sha256=sha256(root/'lock.json')))
    write_json(root/'execution.json',dict(complete=True,workers=workers,lock_sha256=sha256(root/'lock.json'),
        controller_sha256=sha256(root/'inference_execution.json')))


def finish_rocm_evaluation(root, workers):
    from score_diffusion_learning import summarize_diffusion_evaluation
    from analyze_folding_structure_extent import summarize_structure_extent
    from fastglycan.folding_evaluation import summarize_folding_cohorts
    from fastglycan.folding_global_metrics import summarize_global_structure
    from fastglycan.folding_report import render_folding_scale_report
    lock = json.loads((root/'lock.json').read_text())
    replay = json.loads((root/'terminal_replay.json').read_text())
    assert replay['complete'] and replay['lock_sha256'] == sha256(root/'lock.json')
    assert set(replay['arms']) == {'weak','strong'}
    for arm,r in replay['arms'].items():
        assert r['exact_coordinates'] == 64
        assert r['training_probe_sha256'] == sha256(Path(lock['train'])/arm/'expanded/probe_2048/report.json')
    summarize_diffusion_evaluation(root,workers)
    evaluation = json.loads((root/'evaluation.json').read_text())
    assert evaluation['complete'] and evaluation['outputs'] == 1820 and evaluation['probe_nfe'] == 56
    cohorts = dict(complete=True,evaluation_sha256=sha256(root/'evaluation.json'),
        **summarize_folding_cohorts(evaluation['records'],lock))
    write_json(root/'cohorts.json',cohorts)
    destination=root/'extent'; destination.mkdir(exist_ok=False)
    hashes={str(p):sha256(p) for p in [root/'lock.json',root/'execution.json',root/'evaluation.json']}
    hashes.update(lock['hashes']); examples={}; rmsd={}
    for row in lock['rows']:
        g=row['group_id'];examples[g]=sha256(root/'examples'/g/'report.json')
    for x in evaluation['records']:
        rmsd.setdefault(x['group_id'],{}).setdefault(x['model'],{})[str(x['seed'])]=x['ca_aligned_rmsd']
    write_json(destination/'manifest.json',dict(evaluation_root=str(root),evaluation_lock_sha256=sha256(root/'lock.json'),
        hashes=hashes,example_reports=examples,rmsd=rmsd,diagnostic_candidate='strong',diagnostic_reference='weak'))
    summarize_structure_extent(destination,workers)
    extent=json.loads((destination/'report.json').read_text())
    assert extent['complete'] and extent['outputs']==1820 and extent['rmsd_replay_max']<1e-8
    audit_path=Path(lock['train'])/'terminal_audit.json'
    assert sha256(audit_path)==lock['input_hashes'][str(audit_path)]
    audit=json.loads(audit_path.read_text()); global_result=summarize_global_structure(evaluation['records'],lock)
    text=render_folding_scale_report(lock,audit,evaluation,cohorts)+'\n'+global_result.pop('markdown')
    text+='\n## Far experimental distances (sequence gap ≥24, GT distance ≥30 Å)\n\n'
    text+='|Cohort|Weak MAE|Strong MAE|Mean Δ|95% CI|\n|---|---:|---:|---:|---|\n'
    for cohort in lock['cohort_order']:
        s=extent['summary'][cohort];key='seq24_gt_ge30.mae';d=s['contrasts'][0]['metrics'][key]
        text+=f"|{cohort}|{s['models']['weak'][key]['mean']}|{s['models']['strong'][key]['mean']}|{d['mean']}|{d['ci95']}|\n"
    text+='\nPositive distance/RMSD deltas are worse. All tails, per-protein values and empty-band support remain in JSON. '
    text+='Historical CUDA outcomes are separate context, not the matched causal contrast. No automatic model promotion.\n'
    (root/'report.md').write_text(text)
    write_json(root/'global_structure.json',global_result)
    files=['lock.json','execution.json','terminal_replay.json','evaluation.json','cohorts.json','extent/report.json','extent/manifest.json','report.md','global_structure.json']
    write_json(root/'acceptance.json',dict(complete=True,files={f:sha256(root/f) for f in files},
        audited_terminal_sha256=sha256(audit_path),scope='paired folding quality/geometry; no deployment/design claim'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--mode',choices=['prepare','collect','finish'],required=True);p.add_argument('--workers',type=int,default=8)
    a=p.parse_args()
    if a.mode=='prepare':prepare_rocm_evaluation(a.root)
    elif a.mode=='collect':collect_rocm_evaluation(a.root)
    else:finish_rocm_evaluation(a.root,a.workers)
