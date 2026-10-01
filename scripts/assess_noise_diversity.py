#!/usr/bin/env python3
"""Frozen terminal inference/score orchestration; no new training or model selection."""
import argparse
import copy
import json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.evaluation_reuse import expected_evaluation_calls


def prepare_noise_assessment(root):
    train=root.parent/'noise_diversity_training_v1_20261001_retry1'
    audit=json.loads((train/'terminal_audit.json').read_text());assert audit['complete']
    prior_path=root.parent/'rocm_matched_evaluation_v1_20261001/lock.json'
    prior=json.loads(prior_path.read_text());tl=json.loads((train/'fixed/lock.json').read_text())
    assert prior['rows']==tl['rows']
    for path,digest in prior['input_hashes'].items():assert sha256(Path(path))==digest,path
    for name in ['evaluate_diffusion_learning.py','score_diffusion_learning.py']:
        assert sha256(root/'code/scripts'/name)==sha256(prior_path.parent/'code/scripts'/name)
    assert sha256(root/'code/scripts/audit_rocm_flag_replay.py') == sha256(prior_path.parent/'replay_tools/audit_rocm_flag_replay.py')
    hashes={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.json','.md']}
    hashes[str(Path(__file__))]=sha256(Path(__file__))
    for panel in ['original','noise']:
        dest=root/panel;dest.mkdir(exist_ok=False);(dest/'code').symlink_to(root/'code',target_is_directory=True)
        (dest/'replay_tools').mkdir()
        ref=root/'code/docs/mini_folding_rocm_replay_addendum_v1.md'
        (dest/'replay_tools'/ref.name).symlink_to(ref)
        lock=copy.deepcopy(prior)
        lock.update(schema='noise_diversity_terminal_assessment_v1',train=str(train),models=['fixed','diverse'],
            checkpoints=audit['checkpoints'],checkpoint_training_locks=audit['training_locks'],
            checkpoint_arms={a:'expanded' for a in ['fixed','diverse']},
            selected_names={a:tl['selected_names'] for a in ['fixed','diverse']},reuse_models={},
            contrasts=[['diverse','fixed']],hashes=hashes,
            primary='Matched terminal diverse minus fixed; development evidence, no checkpoint selection',
            protocol_sha256=sha256(root/'code/docs/mini_noise_diversity_v1.md'))
        lock['input_hashes'].update({str(train/'terminal_audit.json'):sha256(train/'terminal_audit.json'),str(prior_path):sha256(prior_path)})
        if panel=='noise':
            groups=set(tl['probe_groups']);lock['rows']=[r for r in prior['rows'] if r['group_id'] in groups]
            assert len(lock['rows'])==32 and all(r['role']=='train' for r in lock['rows'])
            lock['train_seeds']=[600001,600011,920003,920009,920021,920033]
            lock['cohorts']={'train_probe32':[r['group_id'] for r in lock['rows']]};lock['cohort_order']=['train_probe32']
        assignments=[[] for _ in range(8)];loads=[0]*8
        for row in sorted(lock['rows'],key=lambda r:(-len(r['sequence']),r['group_id'])):
            i=min(range(8),key=lambda i:(loads[i],i));assignments[i].append(row);loads[i]+=len(row['sequence'])**2
        lock['assignments']=assignments
        lock['planned_outputs']=sum(expected_evaluation_calls(lock,lock['rows']).values())
        lock['planned_prediction_nfe']=lock['planned_outputs'];lock['planned_probe_nfe']=56
        write_json(dest/'lock.json',lock)
    write_json(root/'prepare.json',dict(complete=True,panels={p:sha256(root/p/'lock.json') for p in ['original','noise']},terminal_audit_sha256=sha256(train/'terminal_audit.json')))


def score_noise_assessment(root,panel):
    from score_diffusion_learning import score_diffusion_case
    from fastglycan.folding_evaluation import summarize_folding_cohorts
    from fastglycan.folding_global_metrics import summarize_global_structure
    dest=root/panel;lock=json.loads((dest/'lock.json').read_text())
    execution=json.loads((dest/'execution.json').read_text());assert execution['complete']
    assert len(execution['workers'])==8 and all(j['exit_code']==0 for j in execution['workers'])
    seen=[]
    for i,assignment in enumerate(lock['assignments']):
        r=json.loads((dest/f'worker_{i}/report.json').read_text())
        assert r['complete'] and r['lock_sha256']==sha256(dest/'lock.json')
        assert r['calls']==expected_evaluation_calls(lock,assignment)
        assert r['probe_nfe']==7 and all(all(x.values()) for x in r['probe'].values())
        assert [x['group_id'] for x in r['rows']]==[x['group_id'] for x in assignment]
        seen.extend(x['group_id'] for x in r['rows'])
    assert len(seen)==len(set(seen))==len(lock['rows'])
    for p,h in lock['hashes'].items():assert sha256(Path(p))==h
    with ProcessPoolExecutor(max_workers=8) as pool:
        results=list(pool.map(score_diffusion_case,[(str(dest),r) for r in lock['rows']]))
    assert all(r['complete'] for r in results),[r for r in results if not r['complete']]
    records=[x for r in results for x in r['records']];assert len(records)==lock['planned_outputs']
    summaries={}
    sets={'original':lock['train_seeds']} if panel=='original' else {'seen':[600001,600011],'new':[920003,920009,920021,920033]}
    for name,seeds in sets.items():
        sub=copy.deepcopy(lock);sub['train_seeds']=seeds
        selected=records if panel=='original' else [r for r in records if r['seed'] in seeds]
        summaries[name]=dict(cohorts=summarize_folding_cohorts(selected,sub),global_structure=summarize_global_structure(selected,sub))
    write_json(dest/'report.json',dict(complete=True,records=records,summaries=summaries,lock_sha256=sha256(dest/'lock.json'),
        metric_max_abs=max(r['metric_max_abs'] for r in results),scope='terminal descriptive paired quality; matched-flag replay reported separately'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--mode',choices=['prepare','score','replay'],required=True);p.add_argument('--panel',choices=['original','noise']);p.add_argument('--arm',choices=['fixed','diverse']);a=p.parse_args()
    if a.mode=='prepare':prepare_noise_assessment(a.root)
    elif a.mode=='score':score_noise_assessment(a.root,a.panel)
    else:
        from audit_rocm_flag_replay import audit_rocm_gradient_flag_replay
        audit_rocm_gradient_flag_replay(a.root/'original',a.arm)
