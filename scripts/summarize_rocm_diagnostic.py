#!/usr/bin/env python3
"""Score completed coordinates without relabelling the failed exact-replay gate."""
import argparse
import json
import shutil
from pathlib import Path
from fastglycan.paired_teacher_protocol import sha256,write_json


def summarize_rocm_diagnostic(root,workers):
    from score_diffusion_learning import summarize_diffusion_evaluation
    from analyze_folding_structure_extent import summarize_structure_extent
    from fastglycan.folding_evaluation import summarize_folding_cohorts
    from fastglycan.folding_global_metrics import summarize_global_structure
    from fastglycan.folding_report import render_folding_scale_report
    lock=json.loads((root/'lock.json').read_text())
    controller=json.loads((root/'controller_execution.json').read_text())
    assert not controller['complete'] and 'collect failed' in controller['error']
    inference=json.loads((root/'inference_execution.json').read_text())
    assert inference['complete'] and inference['lock_sha256']==sha256(root/'lock.json')
    assert sorted(j['index'] for j in inference['jobs'])==list(range(8))
    discrepancy=json.loads((root/'replay_discrepancy.json').read_text())
    assert discrepancy['complete'] and len(discrepancy['records'])==128
    # A separate derived view; no changes to locked code, coordinates, or failed release.
    view=root/'diagnostic_scores';view.mkdir(exist_ok=False)
    shutil.copyfile(root/'lock.json',view/'lock.json')
    for name in ['code','examples']+[f'worker_{i}' for i in range(8)]:
        (view/name).symlink_to(root/name,target_is_directory=True)
    records=[];trusted={}
    for job in inference['jobs']:
        assert job['exit_code']==0
        p=root/f'worker_{job["index"]}/report.json';report=json.loads(p.read_text())
        assert report['complete'] and report['lock_sha256']==sha256(root/'lock.json')
        for row in report['rows']:
            g=row['group_id'];assert g not in trusted;trusted[g]=row
            assert json.loads((root/'examples'/g/'report.json').read_text())==row
            for e in row['entries']:assert sha256(root/'examples'/g/e['name'])==e['sha256']
        records.append(dict(index=job['index'],pid=job['pid'],exit_code=0,report_sha256=sha256(p)))
    assert set(trusted)=={r['group_id'] for r in lock['rows']}
    write_json(view/'execution.json',dict(complete=True,workers=records,lock_sha256=sha256(view/'lock.json'),
        scope='prediction execution only; original exact-replay protocol NOT accepted',
        protocol_accepted=False,original_controller_sha256=sha256(root/'controller_execution.json')))
    summarize_diffusion_evaluation(view,workers)
    evaluation=json.loads((view/'evaluation.json').read_text())
    assert evaluation['complete'] and evaluation['outputs']==1820 and evaluation['probe_nfe']==56
    cohorts=dict(complete=True,evaluation_sha256=sha256(view/'evaluation.json'),**summarize_folding_cohorts(evaluation['records'],lock))
    write_json(view/'cohorts.json',cohorts)
    extent=view/'extent';extent.mkdir()
    hashes={str(p):sha256(p) for p in [view/'lock.json',view/'execution.json',view/'evaluation.json']};hashes.update(lock['hashes'])
    rmsd={}
    for x in evaluation['records']:rmsd.setdefault(x['group_id'],{}).setdefault(x['model'],{})[str(x['seed'])]=x['ca_aligned_rmsd']
    write_json(extent/'manifest.json',dict(evaluation_root=str(view),evaluation_lock_sha256=sha256(view/'lock.json'),hashes=hashes,
        example_reports={g:sha256(view/'examples'/g/'report.json') for g in trusted},rmsd=rmsd,
        diagnostic_candidate='strong',diagnostic_reference='weak'))
    summarize_structure_extent(extent,workers)
    ext=json.loads((extent/'report.json').read_text());assert ext['complete'] and ext['outputs']==1820
    audit=Path(lock['train'])/'terminal_audit.json';assert sha256(audit)==lock['input_hashes'][str(audit)]
    global_result=summarize_global_structure(evaluation['records'],lock)
    disclaimer=('**DESCRIPTIVE DIAGNOSTIC ONLY: the original exact terminal-coordinate replay gate failed. '
        'Its failure and original outputs are preserved. This report is not a protocol acceptance, '
        'model promotion, or deployment release.**\n\n')
    text=disclaimer+render_folding_scale_report(lock,json.loads(audit.read_text()),evaluation,cohorts)+'\n'+global_result.pop('markdown')
    text+='\n## Far experimental-distance MAE (sequence gap ≥24, GT ≥30 Å)\n\n|Cohort|Weak|Strong|Strong−weak|95% CI|\n|---|---:|---:|---:|---|\n'
    for name in lock['cohort_order']:
        s=ext['summary'][name];key='seq24_gt_ge30.mae';d=s['contrasts'][0]['metrics'][key]
        text+=f"|{name}|{s['models']['weak'][key]['mean']}|{s['models']['strong'][key]['mean']}|{d['mean']}|{d['ci95']}|\n"
    text+='\nDistance and RMSD increases are worse; empty-band support and all per-protein statistics are in JSON.\n'
    # Quantify whether replay mismatch affects the actual probe metrics or discrete geometry.
    lookup={(x['group_id'],x['seed'],x['model']):x for x in evaluation['records']};changes=[]
    for arm in ['weak','strong']:
        probe=Path(lock['train'])/arm/'expanded/probe_2048/report.json'
        for old in json.loads(probe.read_text())['records']:
            new=lookup[old['group_id'],old['seed'],arm]
            changes.append(dict(arm=arm,group_id=old['group_id'],seed=old['seed'],
                delta_aa=new['all_atom_lddt']-old['all_atom_lddt'],delta_ca=new['ca_lddt']-old['ca_lddt'],
                delta_rmsd=new['ca_aligned_rmsd']-old['ca_aligned_rmsd'],
                severe_delta=new['geometry']['severe_pairs']-old['geometry']['severe_pairs'],
                strict_changed=new['geometry']['strict_checked_chirality']!=old['geometry']['strict_checked_chirality']))
    write_json(view/'replay_metric_changes.json',dict(complete=True,records=changes,
        max_abs_aa=max(abs(x['delta_aa']) for x in changes),max_abs_ca=max(abs(x['delta_ca']) for x in changes),
        max_abs_rmsd=max(abs(x['delta_rmsd']) for x in changes),
        changed_severe_counts=sum(x['severe_delta']!=0 for x in changes),changed_strict=sum(x['strict_changed'] for x in changes)))
    write_json(view/'global_structure.json',global_result);(view/'report.md').write_text(text)
    files=['evaluation.json','cohorts.json','global_structure.json','extent/report.json','replay_metric_changes.json','report.md']
    write_json(view/'diagnostic_provenance.json',dict(complete=True,diagnostic_only=True,protocol_accepted=False,
        files={f:sha256(view/f) for f in files},script_sha256=sha256(Path(__file__)),
        inference_sha256=sha256(root/'inference_execution.json'),replay_discrepancy_sha256=sha256(root/'replay_discrepancy.json')))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--workers',type=int,default=8)
    a=p.parse_args();summarize_rocm_diagnostic(a.root,a.workers)
