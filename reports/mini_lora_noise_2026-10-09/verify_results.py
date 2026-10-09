"""CPU-only independent arithmetic checks of frozen result artifacts."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import statistics
import numpy as np
from scipy.stats import spearmanr

root=Path(__file__).resolve().parent
manifest=json.loads((root/'manifest.json').read_text())
for name,digest in manifest['files'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
controller=json.loads((root/'controller.json').read_text())
assert controller['complete'] and controller['phase']=='closed'
assert all(j['status']=='complete' and j['exit_code']==0 for j in controller['jobs'].values())
data=json.loads((root/'site_records.json').read_text())
checked=0; derived={};changes=[]
for arm in ('single','dual'):
    for seed in (272001,272003):
        key=f'{arm}_{seed}'; folder=root/arm/'runs'/str(seed)
        summary=json.loads((folder/'summary.json').read_text())['summary']
        audit=json.loads((folder/'noise_audit.json').read_text())
        train=json.loads((folder/'training_complete.json').read_text())
        replay=json.loads((folder/'replay_timing.json').read_text())
        assert train['complete'] and train['step']==8208 and len(set(train['replica_hashes']))==1
        assert all(c['recycle']==c['s1']==8208 and c['input_embedder']==c['c4']==0 for c in train['rank_counts'])
        assert replay['complete'] and all(x['bitwise'] for x in replay['replays'])
        assert replay['serial_order_bitwise'] and replay['disabled_restored_sites']==48
        exposures=audit['exposure_counts']; counts=Counter((x['site'],x['aa']) for x in exposures)
        assert len(counts)==513 and set(counts.values())==({1} if arm=='single' else {2})
        assert {x['count'] for x in exposures}==({32} if arm=='single' else {16})
        assert {x['noise'] for x in exposures}==({230201} if arm=='single' else {230201,230211})
        for row in data[key]['sites']:
            tasks=np.asarray(row['tasks']);assert tasks.shape==(2,19) and np.isfinite(tasks).all()
            exact=next(x for x in data[key]['sites'] if x['site_key']==row['site_key'] and x['arm']=='exact')
            teacher=np.asarray(exact['tasks']);selected=int(tasks[0].argmin())
            assert abs(row['old_select_new_regret']-(teacher[1,selected]-teacher[1].min()))<1e-12
            for ni in (0,1):
                rho=float(spearmanr(teacher[ni],tasks[ni]).statistic)
                assert abs(row['ranking'][ni]['spearman']-rho)<1e-12
            rho=float(spearmanr(teacher.mean(0),tasks.mean(0)).statistic)
            assert abs(row['aggregate_ranking']['spearman']-rho)<1e-12
            checked+=1
        geos={}
        for role in summary:
            geos[role]={}
            for checkpoint in ('exact','disabled','4104_adapted','8208_adapted'):
                rows=[x for x in audit['geometry'] if x['role']==role and x['pdb']=='ALL' and x['checkpoint_arm']==checkpoint]
                totals={k:sum(x.get(k,0) for x in rows) for k in ('outputs','passed','new_failures','repairs','severe_pairs','wrong_centres','already_failed_severe_pairs','already_failed_wrong_centres')}
                assert totals['outputs']==summary[role][checkpoint]['outputs']
                assert totals['passed']==summary[role][checkpoint]['geometry_pass']
                assert totals['new_failures']==summary[role][checkpoint]['disabled_pass_to_fail']
                assert totals['repairs']==summary[role][checkpoint]['disabled_fail_to_pass']
                geos[role][checkpoint]=totals
        medians={a:statistics.median(x['seconds'] for x in replay['timing'] if x['arm']==a) for a in ('cold_C4','disabled','adapted')}
        derived[key]=dict(geometry=geos,timing_medians=medians,speedup=medians['cold_C4']/medians['adapted'])
for seed in (272001,272003):
    a={x['site_key']:x for x in data[f'single_{seed}']['sites'] if x['arm']=='8208_adapted'}
    b={x['site_key']:x for x in data[f'dual_{seed}']['sites'] if x['arm']=='8208_adapted'}
    for k,x in a.items():
        y=b[k]
        if x['role']=='dev_unseen_protein' and x['old_selected']!=y['old_selected']:
            changes.append(dict(seed=seed,pdb=x['pdb'],site=x['original_aa']+str(x['position']+1),
                single_selected=x['old_selected'],dual_selected=y['old_selected'],single_regret=x['old_select_new_regret'],
                dual_regret=y['old_select_new_regret'],delta=y['old_select_new_regret']-x['old_select_new_regret']))
a={x['site_key']:x['old_selected'] for x in data['dual_272001']['sites'] if x['arm']=='8208_adapted' and x['role']=='dev_unseen_protein'}
b={x['site_key']:x['old_selected'] for x in data['dual_272003']['sites'] if x['arm']=='8208_adapted' and x['role']=='dev_unseen_protein'}
result=dict(complete=True,verified_source_artifacts=len(manifest['files']),site_arm_rows_recomputed=checked,
    spearman_checks=checked*3,regret_checks=checked,controller_seconds=controller['seconds'],
    dual_seed_same_selected_sites=sum(a[k]==b[k] for k in a),dual_seed_compared_sites=len(a),
    derived=derived,held_selection_changes=changes)
(root/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('derived','held_selection_changes')}))
