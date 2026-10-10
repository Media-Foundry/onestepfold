"""Independent arithmetic checks and paired analysis of placement experiments.

This module is CPU-only and does not import the predictor, choose checkpoints,
fit a calibration, or modify the scientific run. Protein remains the unit of
aggregation. A completed training controller alone is not sufficient: the
separate native checkpoint verifier must also have completed all four runs.
"""
from collections import Counter
import gzip
import json
from pathlib import Path

import numpy as np

from fastglycan.anchor_results import pool_anchor_latent
from fastglycan.anchor_reporting import selection_detail_rows
from fastglycan.fullbatch_results import _check_score, _close, _json, _parent_interval, _sha


def require_placement_completion(training, verification):
    training,verification=Path(training),Path(verification)
    lock=_json(training/'training_lock.json');state=_json(training/'controller.json')
    verify_state=_json(verification/'controller.json');verify_lock=_json(verification/'verification_lock.json')
    if not state.get('complete') or state.get('phase')!='complete':
        raise ValueError('original placement comparison is not complete')
    if not verify_state.get('complete') or verify_state.get('phase')!='complete':
        raise ValueError('independent native checkpoint replay is not complete')
    assert lock['arms']==['late','early'] and lock['seeds']==[272001,272003]
    assert lock['run_order']==[['late',272001],['early',272001],['late',272003],['early',272003]]
    assert lock['checkpoints']==[0,32,128] and lock['gradient_budget']==128
    digest=_sha(training/'training_lock.json')
    assert state['lock_sha256']==verify_lock['training_lock_sha256']==digest
    expected={'tests','parallel_gate','gate_verification','ledger_verification'}|{
        f'{kind}_{arm}_{seed}' for kind in ('train','score') for arm,seed in lock['run_order']}
    assert set(state['jobs'])==expected
    assert set(verify_state['jobs'])=={f'{arm}_{seed}' for arm,seed in lock['run_order']}
    for owner in (state,verify_state):
        assert all(j['status']=='complete' and j['exit_code']==0 and not j.get('timeout') for j in owner['jobs'].values())
    ledger=_json(training/'ledger_verification.json');gate=_json(training/'parallel_gate_verification.json')
    assert ledger['complete'] and gate['complete'] and gate['bitwise_steps']==[1,2]
    assert ledger['lock_sha256']==gate['lock_sha256']==digest
    return lock


def placement_trajectory(history, lock, tensor):
    """History step n contains the loss BEFORE update n, not after update n."""
    assert [r['step'] for r in history]==list(range(1,129))
    objectives={r['step']:r['raw'] for r in tensor['objectives']}
    assert set(objectives)=={0,32,128}
    rows=[]
    for item in history:
        value=item['summary'];step=item['step']
        assert [r['site'] for r in value['sites']]==lock['train_sites']
        for field in ('raw','common','centered'):
            _close(value[field],float(np.mean([r[field] for r in value['sites']])))
        _close(value['raw'],value['common']+value['centered'])
        for row in value['sites']:_close(row['raw'],row['common']+row['centered'])
        assert item['gradient_norm']>=0 and np.isfinite(item['gradient_norm'])
        assert item['clipped']==(item['gradient_norm']>1)
        assert np.isfinite(item['seconds']) and item['seconds']>0
        assert value['counts']==dict(forwards=513,backwards=513,reference_forwards=27,
                                    reference_backwards=27,gradient_passes=1)
        rows.append(dict(state_step=step-1,raw=value['raw'],common=value['common'],centered=value['centered']))
    for step in (0,32):_close(rows[step]['raw'],objectives[step],rtol=2e-8,atol=1e-10)
    rows.append(dict(state_step=128,raw=objectives[128],common=None,centered=None))
    seconds=np.asarray([r['seconds'] for r in history])
    return dict(states=rows,optimizer_updates=128,full_gradient_evaluations=128,
        clipped_updates=sum(int(r['clipped']) for r in history),
        update_seconds=dict(sum=float(seconds.sum()),mean=float(seconds.mean()),
            median=float(np.median(seconds)),minimum=float(seconds.min()),maximum=float(seconds.max())),
        timing_is_execution_ledger=True,balanced_benchmark=False)


def selection_contributions(first, second):
    """Decompose a protein-weighted regret difference, retaining every site."""
    a={r['site_key']:r for r in first if r['arm']=='correct'}
    b={r['site_key']:r for r in second if r['arm']=='correct'}
    assert len(a)==sum(r['arm']=='correct' for r in first)
    assert len(b)==sum(r['arm']=='correct' for r in second) and a.keys()==b.keys()
    rows=[]
    for role in sorted({r['role'] for r in a.values()}):
        parents={r['parent'] for r in a.values() if r['role']==role}
        for key,x in a.items():
            if x['role']!=role:continue
            y=b[key]
            assert (x['parent'],x['role'])==(y['parent'],y['role'])
            site_count=sum(r['parent']==x['parent'] and r['role']==role for r in a.values())
            delta=x['old_select_new_regret']-y['old_select_new_regret']
            rows.append(dict(site=key,parent=x['parent'],role=role,pdb=x.get('pdb'),
                early_aa=x['old_selected'],late_aa=y['old_selected'],
                early_regret=x['old_select_new_regret'],late_regret=y['old_select_new_regret'],
                delta=delta,protein_weighted_contribution=delta/site_count/len(parents),
                selection_changed=x['old_selected']!=y['old_selected']))
    return rows


def placement_geometry_transitions(first, second):
    """Compare the same actual candidate/noise outputs, not net pass counts."""
    key=lambda r:(r['site_key'],r['noise'],r['aa'])
    a={key(r):r for r in first if r['arm']=='correct'}
    b={key(r):r for r in second if r['arm']=='correct'}
    assert len(a)==sum(r['arm']=='correct' for r in first)
    assert len(b)==sum(r['arm']=='correct' for r in second) and a.keys()==b.keys()
    result={}
    for role in sorted({r['role'] for r in a.values()}):
        counts=Counter();parents={}
        for k,x in a.items():
            if x['role']!=role:continue
            y=b[k];assert (x['role'],x['parent'])==(y['role'],y['parent'])
            early=x['geometry'];late=y['geometry']
            good=early['zero_severe_strict_checked_chirality'];old=late['zero_severe_strict_checked_chirality']
            values=dict(outputs=1,early_pass=int(good),late_pass=int(old),
                late_pass_to_early_fail=int(old and not good),late_fail_to_early_pass=int(not old and good),
                severe_pair_delta=early['severe_pairs']-late['severe_pairs'],
                wrong_centre_delta=early['checked_chirality_wrong']-late['checked_chirality_wrong'])
            counts.update(values);parents.setdefault(x['parent'],Counter()).update(values)
        assert counts['early_pass']-counts['late_pass']==counts['late_fail_to_early_pass']-counts['late_pass_to_early_fail']
        result[role]=dict(counts= dict(counts),parents=[dict(parent=p,**dict(c)) for p,c in sorted(parents.items())])
    return result


def verify_placement_export(root):
    root=Path(root);manifest=_json(root/'manifest.json');lock=_json(root/'training_lock.json')
    assert manifest['scientific_experiment_complete']
    for name,digest in manifest['files'].items():assert _sha(root/name)==digest,name
    require_placement_completion(root,root/'verification_source')
    assert _sha(root/'protocol.md')==lock['protocol_sha256']
    assert _sha(root/'historical/training_lock.json')==lock['previous_lock_sha256']
    historical_lock=_json(root/'historical/training_lock.json')
    for key in ('train_sites','eval_sites','site_scale_squared','checkpoints','gradient_budget'):
        assert historical_lock[key]==lock[key],key
    checks=Counter();ledger={}
    for arm,seed in lock['run_order']:
        folder=root/'runs'/arm/str(seed)
        reports=[_json(folder/f'rank_{rank}/report.json') for rank in range(6)]
        assert all(r['complete'] and r['steps']==128 and r['checkpoints']==[0,32,128] for r in reports)
        assert len({r['final_sha256'] for r in reports})==1
        total=Counter();native=Counter()
        for rank,record in enumerate(reports):
            assert record['lock_sha256']==_sha(root/'training_lock.json')
            assert (record['arm'],record['seed'],record['rank'])==(arm,seed,rank)
            assert record['local_sites']==lock['train_sites'][rank::6]
            total.update(record['counts']);native.update(record['native_counts'])
        assert dict(total)==dict(forwards=65664,backwards=65664,reference_forwards=3456,
            reference_backwards=3456,evaluation_forwards=2736,evaluation_reference_forwards=144,isolation_forwards=144)
        assert dict(native)==dict(c4=0,input_embedder=0,recycle=0,s1=7296,updates=0)
        tensor=_json(root/f'verification_source/{arm}_{seed}/tensor_verification.json')
        assert tensor['complete'] and (tensor['arm'],tensor['seed'])==(arm,seed)
        assert tensor['training_lock_sha256']==_sha(root/'training_lock.json')
        assert tensor['verifier_sha256']==_json(root/'verification_source/verification_lock.json')['verifier_sha256']
        assert tensor['feature_forwards']==2736 and tensor['reference_forwards']==144
        assert tensor['counts']==dict(c4=0,input_embedder=0,recycle=0,s1=0,updates=0)
        assert len(tensor['checks'])==144 and {(r['step'],r['site']) for r in tensor['checks']}=={
            (step,site) for step in lock['checkpoints'] for site in lock['eval_sites']}
        with gzip.open(root/f'historical/{seed}/scores_0.json.gz','rt') as stream:past=json.load(stream)
        history=[json.loads(line) for line in (folder/'history.jsonl').read_text().splitlines()]
        ledger[f'{arm}_{seed}']=placement_trajectory(history,lock,tensor)
        baseline={(r['site_key'],r['arm']):r for r in past['sites']}
        for step in lock['checkpoints']:
            ev=_json(folder/f'evaluation_{step}.json')
            assert ev['complete'] and ev['step']==ev['gradient_passes']==ev['optimizer_calls']==step
            assert len(ev['latent'])==48 and {r['site'] for r in ev['latent']}==set(lock['eval_sites'])
            assert len(ev['predictions'])==(1824 if step==128 else 912)
            assert len({(r['arm'],r['label']) for r in ev['predictions']})==len(ev['predictions'])
            assert (ev['historical'] is not None)==(arm=='late')
            if arm=='late':assert ev['historical']['bitwise']
            for row in ev['latent']:
                assert (row['role']=='train')==(row['site'] in lock['train_sites'])
                assert (row['mismatch'] is not None)==(step==128)
                for moments in (row['moments'],row['mismatch']):
                    if moments is None:continue
                    assert moments['candidates']==19
                    for field in ('error_energy','predicted_energy','target_energy'):
                        _close(moments['raw'][field],moments['common'][field]+moments['centered'][field],rtol=1e-7,atol=1e-7)
                if step==0:assert row['moments']['raw']['nmse']==row['moments']['centered']['nmse']==1.
            with gzip.open(folder/f'scores_{step}.json.gz','rt') as stream:score=json.load(stream)
            assert score['complete'] and (score['initialization'],score['seed'],score['step'])==(arm,seed,step)
            assert score['evaluation_sha256']==_sha(folder/f'evaluation_{step}.json')
            assert score['scorer_sha256']==lock['code']['scripts/score_pair_recovery.py']
            assert _json(folder/f'summary_{step}.json')=={k:v for k,v in score.items() if k not in ('sites','outputs')}
            checks.update(_check_score(score,ev,baseline));checks['nodes']+=1
        checks.update(runs=1,training_forwards=65664,training_backwards=65664,
            reference_forwards=3456,reference_backwards=3456,s1=7296,
            verification_forwards=2736,verification_reference_forwards=144)
    assert checks['runs']==4 and checks['nodes']==12
    result=dict(complete=True,checks=dict(checks),files_sha_verified=len(manifest['files']),
        score_arithmetic_recomputed=True,coordinate_scoring_recomputed=False,tensor_replay_verified=True,
        all_panels_development=True,promoted=False,lock_sha256=_sha(root/'training_lock.json'))
    (root/'optimization_ledger.json').write_text(json.dumps(ledger,indent=2,allow_nan=False)+'\n')
    (root/'verification.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    return result


def analyze_placement_results(root):
    root=Path(root);lock=_json(root/'training_lock.json');verified=_json(root/'verification.json')
    assert verified['complete'] and verified['lock_sha256']==_sha(root/'training_lock.json')
    ledger=_json(root/'optimization_ledger.json');runs={}
    for seed in lock['seeds']:
        nodes=[]
        for step in lock['checkpoints']:
            evaluations={arm:_json(root/f'runs/{arm}/{seed}/evaluation_{step}.json') for arm in lock['arms']}
            scores={}
            for arm in lock['arms']:
                with gzip.open(root/f'runs/{arm}/{seed}/scores_{step}.json.gz','rt') as stream:scores[arm]=json.load(stream)
            latent={arm:pool_anchor_latent(ev) for arm,ev in evaluations.items()};contrasts={}
            for role in scores['early']['summary']:
                contrasts[role]={field:_parent_interval(scores['early']['summary'][role]['correct']['parent_summaries'],
                    scores['late']['summary'][role]['correct']['parent_summaries'],field)
                    for field in ('spearman','regret','centered_response_rmse')}
                contrasts[role]['centered_latent_nmse']=_parent_interval(latent['early'][role]['parent_summaries'],
                    latent['late'][role]['parent_summaries'],'centered_nmse')
                for name in ('exact','disabled','oracle_pair'):
                    assert scores['early']['summary'][role][name]==scores['late']['summary'][role][name]
            choices=selection_contributions(scores['early']['sites'],scores['late']['sites'])
            for role in contrasts:
                _close(sum(r['protein_weighted_contribution'] for r in choices if r['role']==role),contrasts[role]['regret']['mean'])
            details=selection_detail_rows(scores['early'],scores['late'],seed)
            for row in details:row['method']={'anchor':'early','control':'late'}.get(row['method'],row['method'])
            nodes.append(dict(step=step,latent=latent,summary={arm:s['summary'] for arm,s in scores.items()},
                within_arm_contrasts={arm:s['contrasts'] for arm,s in scores.items()},early_minus_late=contrasts,
                choices=choices,selection_details=details,
                geometry=placement_geometry_transitions(scores['early']['outputs'],scores['late']['outputs'])))
        runs[str(seed)]=dict(nodes=nodes,optimization={arm:ledger[f'{arm}_{seed}'] for arm in lock['arms']})
    result=dict(complete=True,runs=runs,primary_step=128,all_panels_development=True,promoted=False,
        equal_candidate_exposure=True,equal_trainable_parameters=True,equal_compute=False,
        controls_rerun=True,historical_control_checkpoints_bitwise=True,inference_speedup_measured=False,
        lock_sha256=_sha(root/'training_lock.json'))
    (root/'analysis.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    return result
