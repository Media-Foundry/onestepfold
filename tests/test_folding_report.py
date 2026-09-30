import copy
import pytest
from fastglycan.folding_report import render_folding_scale_report


def test_folding_report_keeps_damage_and_cohort_denominators():
    names=['native_s1','native_s2','retained','train128','expanded']
    groups={'original_train128':['a'],'added_train295':['b'],'new_validation32':['c']}
    lock=dict(models=names,cohorts=groups,rows=[{}, {}, {}],planned_outputs=30)
    quality=dict(mean=.001,ci95=[-.002,.004],p01=-.06,p05=-.05,worst5_mean=-.06,below_minus_005=1)
    contrast=dict(candidate='expanded',reference='train128',quality={'all_atom_lddt':quality,'ca_lddt':quality},
        introduced_severe_on_zero_instances=1,lost_strict_chirality_instances=1)
    model=dict(mean_aa=.81,mean_ca=.89,zero_and_strict_instances=1,instances=2,
        zero_and_strict_both_noises=0,severe_pairs=10)
    cohorts=dict(complete=True,summary={k:dict(proteins=1,models={m:model for m in names},contrasts=[contrast]) for k in groups})
    training=dict(complete=True,summary={a:dict(curves=[],seconds=100,peak_gpu_bytes=2**30,
        exposure_min=2,exposure_max=3,clipped_updates=4) for a in ['train128','expanded']})
    evaluation=dict(complete=True,outputs=30,proteins=3,counts={'native':6,'retained':6,'train128':6,'expanded':6},
        probe_nfe=80,metric_max_abs=1e-16)
    text=render_folding_scale_report(lock,training,evaluation,cohorts)
    assert text.index('## new_validation32') < text.index('## original_train128') < text.index('## added_train295')
    assert '[-0.002000, +0.004000]' in text and '|expanded − train128|1|1|' in text
    assert '|1/2|0/1|10|' in text and 'not comprehensive chemical correctness' in text
    assert '|-0.060000|-0.050000|-0.060000|1/1|' in text
    for change in ['incomplete','outputs','cohort']:
        e=copy.deepcopy(evaluation);c=copy.deepcopy(cohorts)
        if change=='incomplete':e['complete']=False
        elif change=='outputs':e['outputs']=29
        else:c['summary']['new_validation32']['proteins']=0
        with pytest.raises(ValueError):render_folding_scale_report(lock,training,e,c)
