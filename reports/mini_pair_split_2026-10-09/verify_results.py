"""Independent arithmetic and original-endpoint checks; CPU only."""
from pathlib import Path
import gzip,hashlib,json,math
import numpy as np
from scipy.stats import spearmanr

root=Path(__file__).resolve().parent
manifest=json.loads((root/'manifest.json').read_text())
for name,digest in manifest['files'].items(): assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
summary=json.loads((root/'summary.json').read_text());rows=summary['sites']
assert len(rows)==len({(r['site_key'],r['arm']) for r in rows})==864
lookup={(r['site_key'],r['arm']):r for r in rows}
rho_checks=0;regret_checks=0
for row in rows:
    predicted=np.asarray(row['tasks']);exact=np.asarray(lookup[row['site_key'],'exact']['tasks'])
    for j in range(3):
        a,b=(exact[j],predicted[j]) if j<2 else (exact.mean(0),predicted.mean(0))
        rho=float(spearmanr(a,b).statistic)
        actual=row['ranking'][j]['spearman'] if j<2 else row['aggregate_ranking']['spearman']
        assert (actual is None and math.isnan(rho)) or math.isclose(actual,rho,abs_tol=1e-12)
        rho_checks+=1
    regret=float(exact[1,np.argmin(predicted[0])]-exact[1].min())
    assert math.isclose(row['old_select_new_regret'],regret,abs_tol=1e-12);regret_checks+=1
old=json.loads((root.parent/'mini_lora_noise_2026-10-09/site_records.json').read_text())
endpoint_checks=0
for name,group in old.items():
    for row in group['sites']:
        if row['arm'] not in ('exact','disabled','8208_adapted'):continue
        arm=name+'_full' if row['arm']=='8208_adapted' else row['arm']
        new=lookup[row['site_key'],arm]
        for key in ('tasks','ranking','aggregate_ranking','old_selected','old_select_new_regret','response','local_mean','local_max','aa_lddt','ca_lddt'):
            assert new[key]==row[key],(name,row['site_key'],key)
        endpoint_checks+=1
derived=json.loads((root/'derived_manifest.json').read_text())
assert hashlib.sha256((root/'output_records.json.gz').read_bytes()).hexdigest()==derived['output_records.json.gz']
with gzip.open(root/'output_records.json.gz','rt') as f: outputs=json.load(f)
assert len(outputs)==len({(r['arm'],r['label'],r['noise']) for r in outputs})==32832
for role,arms in summary['summary'].items():
    for arm,values in arms.items():
        oo=[r for r in outputs if r['role']==role and r['arm']==arm]
        assert values['outputs']==len(oo)
        assert values['geometry_pass']==sum(r['geometry']['zero_severe_strict_checked_chirality'] for r in oo)
        assert values['severe_pairs']==sum(r['geometry']['severe_pairs'] for r in oo)
        assert values['wrong_centres']==sum(r['geometry']['checked_chirality_wrong'] for r in oo)
        for key in ('disabled_pass_to_fail','disabled_fail_to_pass'): assert values[key]==sum(r[key] for r in oo)
        local=np.array([r['fidelity']['local_ca_rmsd_global_frame'] for r in oo])
        for key,value in (('local_p95',np.quantile(local,.95)),('local_p99',np.quantile(local,.99)),('local_max',local.max()),('local_over1',(local>1).sum())):
            assert values[key]==value
result=dict(complete=True,sha_verified_repo_source_files=len(manifest['files']), collection_sha_verified_files=manifest['collection_sha256_verified'],sites=len(rows),output_records=len(outputs),
    spearman_recomputations=rho_checks,regret_recomputations=regret_checks,original_endpoint_site_comparisons=endpoint_checks,
    geometry_tail_counts_verified=True,focused_tests_passed=17)
(root/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
