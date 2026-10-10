"""CPU-only arithmetic verification and paired analysis of anchored training."""
from collections import Counter
import gzip
import json
from pathlib import Path

import numpy as np

from fastglycan.fullbatch_results import (
    _check_score, _close, _json, _parent_interval, _sha, verify_fullbatch_history)


def verify_anchor_results(root):
    root=Path(root);manifest=_json(root/'manifest.json');lock=_json(root/'training_lock.json')
    assert manifest['scientific_experiment_complete']
    for name,digest in manifest['files'].items():assert _sha(root/name)==digest,name
    assert _sha(root/'protocol.md')==lock['protocol_sha256']
    controller=_json(root/'controller.json')
    assert controller['complete'] and controller['phase']=='closed'
    assert controller['lock_sha256']==_sha(root/'training_lock.json')
    assert set(controller['jobs'])=={f'{k}_anchor_{s}' for k in ('train','score','verify') for s in lock['seeds']}
    assert all(r['status']=='complete' and r['exit_code']==0 for r in controller['jobs'].values())
    assert lock['arms']==['anchor'] and lock['seeds']==[272001,272003]
    assert lock['checkpoints']==[0,32,128] and lock['gradient_budget']==128
    old=_json(root/'controls/training_lock.json')
    assert _sha(root/'controls/training_lock.json')==lock['controls_lock_sha256']
    for key in ('train_sites','eval_sites','site_scale_squared','initial_hashes','initial_objective'):
        assert old[key]==lock[key],key
    checks=Counter();ledger={}
    for seed in lock['seeds']:
        control=root/'controls/adamw'/str(seed)
        for name,digest in lock['matched_controls'][str(seed)].items():
            if not name.startswith('checkpoints/'):assert _sha(control/name)==digest,name
        with gzip.open(control/'scores_0.json.gz','rt') as f:past=json.load(f)
        historical={(r['site_key'],r['arm']):r for r in past['sites']}
        folder=root/'runs/anchor'/str(seed)
        report,tensor=_json(folder/'report.json'),_json(folder/'tensor_verification.json')
        assert report['complete'] and tensor['complete']
        assert report['arm']=='anchor' and report['seed']==seed
        assert report['gradient_passes']==128 and report['checkpoints']==lock['checkpoints']
        assert report['initial_sha256']==lock['initial_hashes'][str(seed)]
        assert report['training_lock_sha256']==controller['lock_sha256']
        assert report['training_counts']==dict(forwards=65664,backwards=65664,gradient_passes=128,
            reference_forwards=3456,reference_backwards=3456)
        assert report['native_counts']==dict(c4=0,input_embedder=0,recycle=0,s1=7296,updates=0)
        assert report['evaluation_forwards']==2736 and report['evaluation_reference_forwards']==144
        assert report['isolation_forwards']==6 and report['isolation_reference_forwards']==2
        assert report['initial_gradient_relative_error']<=5e-5
        assert report['cache_bytes']<=lock['resident_tensor_byte_cap']
        assert _sha(folder/'history.jsonl')==report['history_sha256']
        assert tensor['counts']==dict(c4=0,input_embedder=0,recycle=0,s1=0,updates=0)
        assert tensor['verifier_sha256']==lock['code']['scripts/verify_anchor_training.py']
        assert tensor['feature_forwards']==2736 and tensor['reference_forwards']==144
        assert {(r['step'],r['site']) for r in tensor['checks']}=={
            (step,site) for step in lock['checkpoints'] for site in lock['eval_sites']}
        history=[json.loads(x) for x in (folder/'history.jsonl').read_text().splitlines()]
        ledger[f'anchor_{seed}']=verify_fullbatch_history(history,lock,report,tensor['objectives'])
        for step in lock['checkpoints']:
            ev=_json(folder/f'evaluation_{step}.json')
            assert ev['complete'] and ev['step']==ev['gradient_passes']==step
            assert {r['site'] for r in ev['latent']}==set(lock['eval_sites'])
            assert len(ev['predictions'])==(1824 if step==128 else 912)
            for row in ev['latent']:
                assert (row['role']=='train')==(row['site'] in lock['train_sites'])
                assert (row['mismatch'] is not None)==(step==128)
                for moments in (row['moments'],row['mismatch']):
                    if moments is None:continue
                    for field in ('error_energy','target_energy','predicted_energy'):
                        _close(moments['raw'][field],moments['common'][field]+moments['centered'][field],rtol=1e-7,atol=1e-7)
                if step==0:assert row['moments']['raw']['nmse']==row['moments']['centered']['nmse']==1.
            with gzip.open(folder/f'scores_{step}.json.gz','rt') as f:score=json.load(f)
            assert score['complete'] and score['step']==step and score['seed']==seed
            assert score['scorer_sha256']==lock['code']['scripts/score_pair_recovery.py']
            assert score['evaluation_sha256']==_sha(folder/f'evaluation_{step}.json')
            assert _json(folder/f'summary_{step}.json')=={k:v for k,v in score.items() if k not in ('sites','outputs')}
            checks.update(_check_score(score,ev,historical));checks['nodes']+=1
        checks.update(runs=1,training_forwards=65664,training_backwards=65664,
            training_reference_forwards=3456,training_reference_backwards=3456,s1=7296,
            fixed_prediction_forwards=2736,evaluation_reference_forwards=144,isolation_forwards=6,
            isolation_reference_forwards=2,verification_forwards=2736,verification_reference_forwards=144)
    assert checks['runs']==2 and checks['nodes']==6
    result=dict(complete=True,checks=dict(checks),files_sha_verified=len(manifest['files']),
        coordinate_scoring_recomputed=False,score_arithmetic_recomputed=True,tensor_replay_verified=True,
        all_panels_development=True,promoted=False,lock_sha256=_sha(root/'training_lock.json'))
    (root/'optimization_ledger.json').write_text(json.dumps(ledger,indent=2,allow_nan=False)+'\n')
    (root/'verification.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    return result


def pool_anchor_latent(evaluation):
    """Site-normalized quantities, averaged within protein then across proteins."""
    pooled={}
    for role in sorted({r['role'] for r in evaluation['latent']}):
        rows=[r for r in evaluation['latent'] if r['role']==role];parents=[]
        for parent in sorted({r['parent'] for r in rows}):
            rr=[r for r in rows if r['parent']==parent];row=dict(parent=parent,sites=len(rr))
            for mode in ('raw','common','centered'):
                for field in ('nmse','energy_ratio','cosine'):
                    values=[r['moments'][mode][field] for r in rr if r['moments'][mode][field] is not None]
                    row[f'{mode}_{field}']=float(np.mean(values)) if values else None
            fractions=[r['moments']['common']['predicted_energy']/r['moments']['raw']['predicted_energy']
                       for r in rr if r['moments']['raw']['predicted_energy']>0]
            row['common_fraction']=float(np.mean(fractions)) if fractions else None
            if evaluation['step']==128:
                row['mismatch_centered_nmse']=float(np.mean([r['mismatch']['centered']['nmse'] for r in rr]))
            parents.append(row)
        summary=dict(parents=len(parents),sites=len(rows),parent_summaries=parents)
        for field in parents[0]:
            if field in ('parent','sites'):continue
            values=[r[field] for r in parents if r[field] is not None]
            summary[field]=float(np.mean(values)) if values else None
        pooled[role]=summary
    return pooled


def analyze_anchor_results(root):
    root=Path(root);verified=_json(root/'verification.json');lock=_json(root/'training_lock.json')
    assert verified['complete'] and verified['lock_sha256']==_sha(root/'training_lock.json')
    ledger=_json(root/'optimization_ledger.json');runs={}
    for seed in lock['seeds']:
        folder=root/'runs/anchor'/str(seed);control=root/'controls/adamw'/str(seed);nodes=[]
        for step in lock['checkpoints']:
            ev=_json(folder/f'evaluation_{step}.json');old_ev=_json(control/f'evaluation_{step}.json')
            with gzip.open(folder/f'scores_{step}.json.gz','rt') as f:score=json.load(f)
            with gzip.open(control/f'scores_{step}.json.gz','rt') as f:old_score=json.load(f)
            latent,old_latent=pool_anchor_latent(ev),pool_anchor_latent(old_ev)
            paired={}
            for role in score['summary']:
                paired[role]={field:_parent_interval(score['summary'][role]['correct']['parent_summaries'],
                    old_score['summary'][role]['correct']['parent_summaries'],field)
                    for field in ('spearman','regret','centered_response_rmse')}
                paired[role]['centered_latent_nmse']=_parent_interval(latent[role]['parent_summaries'],
                    old_latent[role]['parent_summaries'],'centered_nmse')
            lookup={(r['site_key'],r['arm']):r for r in score['sites']}
            previous={r['site_key']:r for r in old_score['sites'] if r['arm']=='correct'}
            choices=[]
            for row in score['sites']:
                if row['arm']!='correct':continue
                key=row['site_key'];base=lookup[key,'disabled'];old=previous[key]
                choice=dict(site=key,parent=row['parent'],pdb=row['pdb'],role=row['role'],
                    aa=row['old_selected'],baseline_aa=base['old_selected'],control_aa=old['old_selected'],
                    regret=row['old_select_new_regret'],baseline_regret=base['old_select_new_regret'],
                    control_regret=old['old_select_new_regret'])
                if step==128:
                    wrong=lookup[key,'mismatched']
                    choice.update(mismatch_aa=wrong['old_selected'],mismatch_regret=wrong['old_select_new_regret'])
                choices.append(choice)
            nodes.append(dict(step=step,latent=latent,control_latent=old_latent,summary=score['summary'],
                control_summary=old_score['summary'],contrasts=score['contrasts'],anchor_minus_control=paired,choices=choices))
        runs[str(seed)]=dict(nodes=nodes,optimization=ledger[f'anchor_{seed}'],report=_json(folder/'report.json'))
    result=dict(complete=True,runs=runs,all_panels_development=True,promoted=False,
        equal_candidate_exposure=True,equal_compute=False,controls_reused_from_closed_batch=True,
        reference_extra_work_counted=True,primary_step=128)
    (root/'analysis.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    return result
