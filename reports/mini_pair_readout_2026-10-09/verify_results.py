"""Independent arithmetic and source-provenance verification for head fits."""
import gzip
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import scipy.linalg
from scipy.stats import spearmanr
import torch


def verify_pair_readout(root):
    manifest=json.loads((root/'manifest.json').read_text())
    for name,digest in manifest['files'].items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
    lock=json.loads((root/'readout_lock.json').read_text())
    source=root.parent/'mini_pair_recovery_2026-10-09'
    original_lock=json.loads((source/'training_lock.json').read_text())
    assert lock['train_sites']==original_lock['train_sites'] and lock['site_scale_squared']==original_lock['site_scale_squared']
    assert lock['rcond']==1e-6 and lock['centered_decoder'] is False
    checks=dict(fits=0,correlations=0,regrets=0,historical_controls=0,output_records=0,residual_decompositions=0,train_weight_rows=0,historical_latent_replays=0)
    counts=dict(s1=0,updates=0,recycle=0,c4=0,input_embedder=0,feature_forwards=0)
    for arm in lock['arms']:
        for seed in lock['seeds']:
            folder=root/'runs'/arm/str(seed)
            report=json.loads((folder/'report.json').read_text());assert report['complete']
            ev=json.loads((folder/'evaluation.json').read_text());fit=json.loads((folder/'fit.json').read_text())
            assert ev['complete'] and fit['complete']
            assert ev['frozen_sha256_after']==report['frozen_sha256']
            assert ev['counts']==dict(s1=3746,updates=0,recycle=0,c4=0,input_embedder=0)
            assert ev['feature_forwards']==1426
            for key in ev['counts']:counts[key]+=ev['counts'][key]
            counts['feature_forwards']+=ev['feature_forwards']
            assert [r['site'] for r in fit['fit_sites']]==lock['train_sites']
            for row in fit['fit_sites']:
                expected=1/(27*19*row['length']**2*128*lock['site_scale_squared'][row['site']])
                assert row['row_weight']==expected and row['rows']==19*row['length']**2
                checks['train_weight_rows']+=1
            packed=torch.load(folder/'readouts.pt',map_location='cpu',weights_only=False)
            w0=packed['original'].numpy()
            for objective,audit in fit['audits'].items():
                aug=packed['qr'][objective].numpy();x,y=aug[:,:128],aug[:,128:]
                delta=scipy.linalg.lstsq(x,y-x@w0,cond=lock['rcond'],lapack_driver='gelsd')[0]
                w=packed['solutions'][objective].numpy()
                np.testing.assert_allclose(w,w0+delta,rtol=2e-8,atol=1e-9)
                singular=scipy.linalg.svdvals(x)
                assert audit['rank']==int((singular>singular[0]*lock['rcond']).sum())
                np.testing.assert_allclose(singular,audit['singular_values'],rtol=1e-10,atol=1e-13)
                for method,value in (('old',w0),('fit',w),('zero',np.zeros_like(w))):
                    calculated=float(np.square(x@value-y).sum())
                    assert math.isclose(calculated,audit['objective_'+method],rel_tol=1e-10,abs_tol=1e-11)
                    assert math.isclose(calculated,ev['direct_objectives'][objective][method],rel_tol=2e-8,abs_tol=1e-10)
                assert audit['objective_fit']<=audit['objective_old']+1e-10
                assert audit['rows']==sum(r['rows'] for r in fit['fit_sites'])==11552513
                checks['fits']+=1
            historical_ev=json.loads((source/'runs'/arm/str(seed)/'evaluation_8208.json').read_text())
            historical_latent={r['site']:r['moments'] for r in historical_ev['latent']}
            for row in ev['sites']:
                assert row['old']==historical_latent[row['site']],(arm,seed,row['site'])
                checks['historical_latent_replays']+=1
                for method in ('old','full'):
                    m=row[method];assert m['candidates']==19
                    for field in ('target_energy','predicted_energy','error_energy'):
                        assert math.isclose(m['raw'][field],m['common'][field]+m['centered'][field],rel_tol=1e-7,abs_tol=1e-7)
                    checks['residual_decompositions']+=1
            with gzip.open(folder/'scores.json.gz','rt') as f:scores=json.load(f)
            with gzip.open(source/'runs'/arm/str(seed)/'scores_8208.json.gz','rt') as f:old=json.load(f)
            previous={(r['site_key'],r['arm']):r for r in old['sites']}
            lookup={(r['site_key'],r['arm']):r for r in scores['sites']}
            assert len(lookup)==len(scores['sites'])==288
            for row in scores['sites']:
                exact=np.asarray(lookup[row['site_key'],'exact']['tasks']);pred=np.asarray(row['tasks'])
                for ni in range(3):
                    a,b=(exact[ni],pred[ni]) if ni<2 else (exact.mean(0),pred.mean(0))
                    rho=float(spearmanr(a,b).statistic)
                    recorded=row['ranking'][ni]['spearman'] if ni<2 else row['aggregate_ranking']['spearman']
                    assert (recorded is None and math.isnan(rho)) or math.isclose(rho,recorded,abs_tol=1e-12)
                    checks['correlations']+=1
                regret=float(exact[1,np.argmin(pred[0])]-exact[1].min())
                assert math.isclose(regret,row['old_select_new_regret'],abs_tol=1e-12);checks['regrets']+=1
                if row['arm'] in ('exact','disabled','oracle_pair','old'):
                    past=previous[row['site_key'],'correct' if row['arm']=='old' else row['arm']]
                    for key in ('tasks','ranking','aggregate_ranking','old_selected','old_select_new_regret','response','local_mean','local_max','aa_lddt','ca_lddt'):
                        assert row[key]==past[key],(arm,seed,row['site_key'],row['arm'],key)
                    checks['historical_controls']+=1
            outputs=scores['outputs'];assert len(outputs)==len({(r['label'],r['arm'],r['noise']) for r in outputs})==10944
            checks['output_records']+=len(outputs)
            for role,arms in scores['summary'].items():
                for method,value in arms.items():
                    rr=[r for r in scores['sites'] if r['role']==role and r['arm']==method]
                    oo=[r for r in outputs if r['role']==role and r['arm']==method]
                    assert value['geometry_pass']==sum(r['geometry']['zero_severe_strict_checked_chirality'] for r in oo)
                    assert value['severe_pairs']==sum(r['geometry']['severe_pairs'] for r in oo)
                    assert value['wrong_centres']==sum(r['geometry']['checked_chirality_wrong'] for r in oo)
                    for key in ('disabled_pass_to_fail','disabled_fail_to_pass','old_pass_to_fail','old_fail_to_pass','exact_pass_to_fail','exact_fail_to_pass'):
                        assert value[key]==sum(r[key] for r in oo)
                    local=np.array([r['fidelity']['local_ca_rmsd_global_frame'] for r in oo])
                    for key,expected in [('local_max',local.max()),('local_p95',np.quantile(local,.95)),('local_p99',np.quantile(local,.99)),('local_over1',int((local>1).sum()))]:
                        assert value[key]==expected
                    regrets=[float(np.mean([r['old_select_new_regret'] for r in rr if r['parent']==p])) for p in sorted({r['parent'] for r in rr})]
                    assert math.isclose(value['regret'],np.mean(regrets),abs_tol=1e-12)
    assert counts==dict(s1=14984,updates=0,recycle=0,c4=0,input_embedder=0,feature_forwards=5704)
    result=dict(complete=True,checks=checks,counts=counts,source_files_sha_verified=len(manifest['files']),
                independent_solver_checked=True,full_field=True,all_panels_development=True)
    (root/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':
    verify_pair_readout(Path(__file__).resolve().parent)
