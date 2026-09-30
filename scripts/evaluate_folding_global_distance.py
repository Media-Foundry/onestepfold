#!/usr/bin/env python3
"""Audited reuse, fixed terminal scoring and distance diagnostics for C4/S1."""
import argparse
import csv
import json
import subprocess
from pathlib import Path
from fastglycan.global_distance_training import verify_global_distance_lock
from fastglycan.folding_global_evaluation import make_global_distance_evaluation_lock,render_global_distance_extent,REFERENCE_MODELS
from fastglycan.folding_report import render_folding_scale_report
from fastglycan.folding_global_metrics import summarize_global_structure
from fastglycan.paired_teacher_protocol import sha256,write_json


REFERENCE_LOCK = '65a1849e3fe9baab572d685a0cb782d7956e6c8d659d92619175ce3bc7f6255b'


def prepare_global_distance_evaluation(root):
    assert not (root/'lock.json').exists()
    train=root.parent/'folding_global_distance_training_v1_20260930';old=root.parent/'folding_coordinate_evaluation_v1_20260930'
    tl=json.loads((train/'lock.json').read_text());meta=tl['global_distance'];control=Path(meta['control'])
    assert sha256(control/'lock.json')==meta['control_lock_sha256']
    verify_global_distance_lock(tl,json.loads((control/'lock.json').read_text()))
    audit_path=train/'global_training_audit.json';audit=json.loads(audit_path.read_text())
    assert audit['complete'] and audit['same_start'] and audit['same_exposure_order'] and audit['initial_probe_replay_exact']
    assert audit['lock_sha256']==sha256(train/'lock.json')
    assert sha256(Path(audit['checkpoint']['path']))==audit['checkpoint']['sha256']
    assert sha256(old/'lock.json')==REFERENCE_LOCK
    prior=json.loads((old/'lock.json').read_text());execution=json.loads((old/'execution.json').read_text())
    assert execution['complete'] and execution['lock_sha256']==REFERENCE_LOCK
    assert prior['rows']==tl['rows'] and len(prior['rows'])==455 and prior['models']==REFERENCE_MODELS
    trusted={};inputs=dict(prior['input_hashes'])
    for w in execution['workers']:
        p=old/f'worker_{w["index"]}/report.json';assert w['exit_code']==0 and sha256(p)==w['report_sha256']
        report=json.loads(p.read_text());assert report['complete'] and report['lock_sha256']==REFERENCE_LOCK
        for row in report['rows']:
            assert row['group_id'] not in trusted;trusted[row['group_id']]=row
        inputs[str(p)]=sha256(p)
    assert set(trusted)=={r['group_id'] for r in prior['rows']}
    for row in prior['rows']:
        g=row['group_id'];p=old/'examples'/g/'report.json';r=json.loads(p.read_text());assert r==trusted[g]
        seeds=prior['train_seeds'] if row['role']=='train' else prior['validation_seeds']
        assert len(r['entries'])==10 and {(e['model'],e['seed']) for e in r['entries']}=={(m,s) for m in REFERENCE_MODELS for s in seeds}
        for e in r['entries']:
            assert e['name']==f'{e["model"]}_seed{e["seed"]}.npy'
            coordinate=p.parent/e['name'];assert sha256(coordinate)==e['sha256'];inputs[str(coordinate)]=e['sha256']
        inputs[str(p)]=sha256(p)
        for f in [Path(prior['source'])/'chemistry'/g/'mapping.npz',Path(prior['source'])/'chemistry'/g/'native.pt',Path(prior['source'])/'data/examples'/g/'gt.npz']:
            assert sha256(f)==inputs[str(f)]
    zero=root.parent/'folding_coordinate_ablation_v1_20260930'
    for p in [train/'lock.json',audit_path,control/'lock.json',control/'training_audit.json',old/'lock.json',old/'execution.json',zero/'lock.json',zero/'ablation_training_audit.json']:
        inputs[str(p)]=sha256(p)
    for f in ['models/differentiable_mini.py','models/diffusion_adapter.py','models/diffusion_scope.py','models/soft_sequence_chart.py','folding_scale.py','diffusion_pilot_metrics.py']:
        assert sha256(root/'code/src/fastglycan'/f)==sha256(train/'code/src/fastglycan'/f),f
    for f in ['evaluate_diffusion_learning.py','score_diffusion_learning.py','evaluate_folding_scale.py']:
        assert sha256(root/'code/scripts'/f)==sha256(old/'code/scripts'/f),f
    hashes={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.json','.md']}
    lock=make_global_distance_evaluation_lock(prior,train=train,control=control,reference_evaluation=old,
        checkpoint=audit['checkpoint'],training_lock_sha256=sha256(train/'lock.json'),selected_names=tl['selected_names'],
        hashes=hashes,input_hashes=inputs,protocol_sha256=sha256(root/'code/docs/mini_folding_global_distance_evaluation_v1.md'))
    write_json(root/'lock.json',lock)
    write_json(root/'prepare.json',dict(complete=True,lock_sha256=sha256(root/'lock.json'),reused_coordinates=4550,
        new_prediction_nfe=910,engineering_nfe=32,total_new_nfe=942,planned_scored_outputs=5460))


def global_distance_extent(root):
    from analyze_folding_structure_extent import summarize_structure_extent
    lock=json.loads((root/'lock.json').read_text());execution=json.loads((root/'execution.json').read_text())
    assert execution['complete'] and execution['lock_sha256']==sha256(root/'lock.json')
    evaluation=json.loads((root/'evaluation.json').read_text());assert evaluation['complete'] and evaluation['outputs']==5460
    assert evaluation['lock_sha256']==sha256(root/'lock.json')
    destination=root/'extent';destination.mkdir(exist_ok=False)
    hashes={str(p):sha256(p) for p in [root/'lock.json',root/'execution.json',root/'evaluation.json']}
    hashes.update(lock['hashes']);trusted={}
    for w in execution['workers']:
        p=root/f'worker_{w["index"]}/report.json';assert sha256(p)==w['report_sha256'];hashes[str(p)]=sha256(p)
        for row in json.loads(p.read_text())['rows']:
            assert row['group_id'] not in trusted;trusted[row['group_id']]=row
    examples={};rmsd={}
    for row in lock['rows']:
        g=row['group_id'];p=root/'examples'/g/'report.json';assert json.loads(p.read_text())==trusted[g];examples[g]=sha256(p)
    for x in evaluation['records']:rmsd.setdefault(x['group_id'],{}).setdefault(x['model'],{})[str(x['seed'])]=x['ca_aligned_rmsd']
    write_json(destination/'manifest.json',dict(evaluation_root=str(root),evaluation_lock_sha256=sha256(root/'lock.json'),hashes=hashes,
        example_reports=examples,rmsd=rmsd,diagnostic_candidate='global_distance',diagnostic_reference='coordinate_zero'))
    del evaluation
    summarize_structure_extent(destination,8)


def write_global_distance_report(root):
    output=root/'final';assert not output.exists();lock=json.loads((root/'lock.json').read_text())
    train=Path(lock['train']);control=Path(lock['control']);zero=root.parent/'folding_coordinate_ablation_v1_20260930'
    audit_paths=[train/'global_training_audit.json',control/'training_audit.json',zero/'ablation_training_audit.json']
    for p in audit_paths+[train/'lock.json',control/'lock.json',zero/'lock.json']:assert sha256(p)==lock['input_hashes'][str(p)]
    audit=json.loads(audit_paths[0].read_text());original=json.loads(audit_paths[1].read_text());zero_audit=json.loads(audit_paths[2].read_text())
    assert audit['complete'] and original['complete'] and zero_audit['complete']
    training=dict(complete=True,summary={'expanded_control':original['summary']['expanded']});paths=[]
    for name,folder,a in [('coordinate_zero',zero,zero_audit),('global_distance',train,audit)]:
        history=folder/'expanded/history.jsonl';report=folder/'expanded/report.json';tr=json.loads(report.read_text())
        assert sha256(history)==tr['history_sha256'] and tr['lock_sha256']==sha256(folder/'lock.json')
        clipped=sum(x.get('unclipped_accumulated_grad_norm',0)>1 for x in map(json.loads,history.read_text().splitlines()))
        training['summary'][name]={**a,'clipped_updates':clipped};paths.extend([history,report])
    evaluation=json.loads((root/'evaluation.json').read_text());cohorts=json.loads((root/'cohorts.json').read_text())
    assert evaluation['lock_sha256']==sha256(root/'lock.json') and cohorts['evaluation_sha256']==sha256(root/'evaluation.json')
    assert evaluation['counts']==dict(native=0,global_distance=910) and evaluation['probe_nfe']==32
    submission=json.loads((root/'submission.json').read_text());jobs=[submission['score_job'],submission['extent_job']]
    scheduler=subprocess.check_output(['sacct','-j',','.join(jobs),'-n','-X','-P','--format=JobIDRaw,State,ExitCode'],text=True)
    assert all(f'{j}|COMPLETED|0:0' in scheduler for j in jobs)
    extent=json.loads((root/'extent/report.json').read_text());em=json.loads((root/'extent/manifest.json').read_text())
    assert extent['manifest_sha256']==sha256(root/'extent/manifest.json') and em['hashes'][str(root/'evaluation.json')]==sha256(root/'evaluation.json')
    assert extent['rmsd_replay_max']<1e-8
    global_structure=summarize_global_structure(evaluation['records'],lock)
    text=render_folding_scale_report(lock,training,evaluation,cohorts)+'\n'+global_structure.pop('markdown')+'\n'+render_global_distance_extent(extent,lock)
    output.mkdir();(output/'report.md').write_text(text)
    write_json(output/'global_structure.json',dict(evaluation_sha256=sha256(root/'evaluation.json'),**global_structure))
    with (output/'paired.csv').open('w',newline='') as f:
        fields=['cohort','group_id','pdb_id','length','candidate','reference','delta_aa','delta_ca','per_noise'];writer=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');writer.writeheader()
        lookup={r['group_id']:r for r in lock['rows']}
        for row in cohorts['paired']:writer.writerow(dict(row,pdb_id=lookup[row['group_id']]['pdb_id'],per_noise=json.dumps(row['per_noise'],sort_keys=True)))
    write_json(output/'training_comparison.json',training)
    paths+=audit_paths+[root/'lock.json',root/'execution.json',root/'evaluation.json',root/'cohorts.json',root/'extent/report.json',root/'extent/manifest.json']
    write_json(output/'provenance.json',dict(complete=True,jobs=jobs,scheduler=scheduler,inputs={str(p):sha256(p) for p in paths},
        script_sha256=sha256(Path(__file__)),report_sha256=sha256(output/'report.md'),paired_csv_sha256=sha256(output/'paired.csv'),
        global_structure_sha256=sha256(output/'global_structure.json'),scope='fixed terminal candidate; development evidence, no automatic promotion'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--mode',choices=['prepare','extent','report'],required=True);a=p.parse_args();root=a.root.resolve()
    if a.mode=='prepare':prepare_global_distance_evaluation(root)
    elif a.mode=='extent':global_distance_extent(root)
    else:write_global_distance_report(root)
