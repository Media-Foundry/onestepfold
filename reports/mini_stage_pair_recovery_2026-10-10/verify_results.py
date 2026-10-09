"""Verify locked cohorts, exposures, historical controls and score arithmetic."""
from collections import Counter
import gzip,hashlib,json,math
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr


def verify_stage_results(root, *, interim=False):
    manifest=json.loads((root/('interim_manifest.json' if interim else 'manifest.json')).read_text())
    for name,digest in manifest['files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
    old_root=root.parent/'mini_pair_recovery_2026-10-09'
    old=json.loads((old_root/'training_lock.json').read_text())
    lock=json.loads((root/'build_lock.json').read_text());stage=json.loads((root/'stage_manifest.json').read_text())
    assert len(stage['records'])==len({r['label'] for r in stage['records']})==912
    assert sum(r['role']=='train' for r in stage['records'])==513
    assert lock['site_scale_squared']==old['site_scale_squared']
    parts=[json.loads((root/f'cache_{i}.json').read_text()) for i in range(4)]
    assert all(p['complete'] for p in parts)
    assert sum(p['counts']['recycle'] for p in parts)==2964 and sum(p['counts']['s1'] for p in parts)==1824
    checks=dict(runs=0,nodes=0,latent_replays=0,updates=0,s1=1824,correlations=0,regrets=0,controls=0,outputs=0)
    with gzip.open(old_root/'runs/pretrained/272001/scores_8208.json.gz','rt') as f:past=json.load(f)
    historical={(r['site_key'],r['arm']):r for r in past['sites']}
    initial={}
    for cohort in (('n1',) if interim else ('n1','n15')):
        cfg=json.loads((root/cohort/'training_lock.json').read_text())
        assert cfg['site_scale_squared']==old['site_scale_squared']
        assert cfg['train_sites']==(['p3_s37'] if cohort=='n1' else old['train_sites'])
        assert len(cfg['eval_sites'])==(1 if cohort=='n1' else 48)
        for arm in ('final','hint'):
            for seed in (272001,272003):
                folder=root/cohort/'runs'/arm/str(seed);report=json.loads((folder/'report.json').read_text())
                assert report['complete'] and report['parameters']==stage['parameters']
                initial.setdefault(seed,report['initial_sha256']);assert initial[seed]==report['initial_sha256']==stage['initial_hashes'][str(seed)]
                assert report['counts']==dict(c4=0,input_embedder=0,recycle=0,updates=8208,s1=228 if cohort=='n1' else 7296)
                assert report['training_forwards']==16416
                assert hashlib.sha256((folder/'history.jsonl').read_bytes()).hexdigest()==report['history_sha256']
                rows=[json.loads(s) for s in (folder/'history.jsonl').read_text().splitlines()];assert len(rows)==8208
                choices={k:[r['aa'] for r in past['outputs'] if r['site_key']==k and r['arm']=='exact' and r['noise']==230201] for k in cfg['train_sites']}
                exposure={k:Counter({aa:0 for aa in choices[k]}) for k in cfg['train_sites']}
                for i,row in enumerate(rows):
                    key=cfg['train_sites'][i%len(cfg['train_sites'])];visit=i//len(cfg['train_sites'])
                    assert row['step']==i+1 and row['site']==key
                    assert row['aa']==[choices[key][(2*visit+j)%19] for j in (0,1)]
                    exposure[key].update(row['aa'])
                    for loss,part in zip(row['loss'],row['loss_parts']):
                        expected=part['final'] if arm=='final' else (part['final']+part['hint'])/2
                        assert math.isclose(loss,expected,rel_tol=2e-7,abs_tol=1e-9)
                    assert row['clipped']==(row['gradient_norm']>1)
                assert {k:dict(v) for k,v in exposure.items()}==report['exposure']
                assert all(n==(864 if cohort=='n1' else 32) for row in report['exposure'].values() for n in row.values())
                first=report['gradient_audits'][0];assert first['step']==1
                assert first['norms']['blocks.0']>0 and first['norms']['blocks.1']>0 and not first['missing']
                independent=json.loads((folder/'tensor_verification.json').read_text());assert independent['complete']
                assert independent['counts']==dict(c4=0,input_embedder=0,updates=0,recycle=0,s1=0)
                assert len(independent['checks'])==len(cfg['eval_sites'])*len(cfg['checkpoints'])
                checks['latent_replays']+=len(independent['checks'])
                for step in cfg['checkpoints']:
                    ev=json.loads((folder/f'evaluation_{step}.json').read_text());assert ev['complete']
                    assert {r['site'] for r in ev['latent']}==set(cfg['eval_sites'])
                    for rec in ev['latent']:
                        assert (rec['hint_moments'] is not None)==(rec['role']=='train')
                        for mode in (rec['moments'],rec['hint_moments']):
                            if mode is None:continue
                            for key in ('error_energy','target_energy','predicted_energy'):
                                assert math.isclose(mode['raw'][key],mode['common'][key]+mode['centered'][key],rel_tol=1e-7,abs_tol=1e-7)
                        if step==0:assert rec['moments']['raw']['nmse']==rec['moments']['centered']['nmse']==1.
                    with gzip.open(folder/f'scores_{step}.json.gz','rt') as f:score=json.load(f)
                    lookup={(r['site_key'],r['arm']):r for r in score['sites']}
                    assert len(lookup)==len(cfg['eval_sites'])*(5 if step==8208 else 4)
                    if cohort=='n1':assert score['contrasts']=={'train':{}}
                    for row in score['sites']:
                        exact=np.array(lookup[row['site_key'],'exact']['tasks']);pred=np.array(row['tasks'])
                        for ni in range(3):
                            x,y=(exact[ni],pred[ni]) if ni<2 else (exact.mean(0),pred.mean(0))
                            rho=float(spearmanr(x,y).statistic);got=row['ranking'][ni]['spearman'] if ni<2 else row['aggregate_ranking']['spearman']
                            assert (got is None and math.isnan(rho)) or math.isclose(rho,got,abs_tol=1e-12);checks['correlations']+=1
                        regret=exact[1,np.argmin(pred[0])]-exact[1].min()
                        assert math.isclose(regret,row['old_select_new_regret'],abs_tol=1e-12);checks['regrets']+=1
                        if row['arm'] in ('exact','disabled','oracle_pair'):
                            previous=historical[row['site_key'],row['arm']]
                            for key in ('tasks','ranking','aggregate_ranking','response','old_selected','old_select_new_regret','local_mean','local_max','aa_lddt'):
                                assert row[key]==previous[key],(cohort,arm,seed,step,row['site_key'],key)
                            checks['controls']+=1
                        if step==0 and row['arm']=='correct':assert row['tasks']==lookup[row['site_key'],'disabled']['tasks']
                    checks['outputs']+=len(score['outputs'])
                    for role,methods in score['summary'].items():
                        for method,value in methods.items():
                            oo=[r for r in score['outputs'] if r['role']==role and r['arm']==method]
                            assert value['geometry_pass']==sum(r['geometry']['zero_severe_strict_checked_chirality'] for r in oo)
                            assert value['severe_pairs']==sum(r['geometry']['severe_pairs'] for r in oo)
                            assert value['wrong_centres']==sum(r['geometry']['checked_chirality_wrong'] for r in oo)
                            for key in ('disabled_pass_to_fail','disabled_fail_to_pass','exact_pass_to_fail','exact_fail_to_pass'):
                                assert value[key]==sum(r[key] for r in oo)
                            local=np.array([r['fidelity']['local_ca_rmsd_global_frame'] for r in oo])
                            for key,expected in [('local_max',local.max()),('local_p95',np.quantile(local,.95)),('local_over1',int((local>1).sum()))]:assert value[key]==expected
                    checks['nodes']+=1
                checks['runs']+=1;checks['updates']+=8208;checks['s1']+=report['counts']['s1']
    assert checks['runs']==(4 if interim else 8)
    assert checks['updates']==(32832 if interim else 65664) and checks['s1']==(2736 if interim else 31920)
    result=dict(complete=True,source_files_sha_verified=len(manifest['files']),checks=checks,
                all_panels_development=True,checkpoint_forward_reverified=True,
                verified_cohorts=['n1'] if interim else ['n1','n15'],scientific_experiment_complete=not interim)
    (root/('verification_interim.json' if interim else 'verification.json')).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':
    root=Path(__file__).resolve().parent
    verify_stage_results(root,interim=not (root/'manifest.json').exists())
