#!/usr/bin/env python3
"""Fixed terminal evaluation of the coordinate-weight ablation, with audited reuse."""
import argparse
import copy
import csv
import json
import subprocess
from pathlib import Path

from fastglycan.evaluation_reuse import expected_evaluation_calls
from fastglycan.folding_ablation import verify_coordinate_ablation_lock
from fastglycan.folding_report import render_folding_scale_report
from fastglycan.paired_teacher_protocol import sha256, write_json


def prepare_coordinate_evaluation(root):
    assert not (root/'lock.json').exists(), 'preserve locked evaluation'
    train=root.parent/'folding_coordinate_ablation_v1_20260930'
    tl=json.loads((train/'lock.json').read_text());meta=tl['ablation']
    control=Path(meta['control']);old=Path(meta['evaluation'])
    assert sha256(control/'lock.json')==meta['control_lock_sha256']
    verify_coordinate_ablation_lock(tl,json.loads((control/'lock.json').read_text()))
    audit_path=train/'ablation_training_audit.json';audit=json.loads(audit_path.read_text())
    assert audit['complete'] and audit['same_start'] and audit['same_exposure_order'] and audit['initial_probe_replay_exact']
    assert audit['lock_sha256']==sha256(train/'lock.json')
    assert sha256(Path(audit['checkpoint']['path']))==audit['checkpoint']['sha256']
    assert sha256(old/'lock.json')==meta['evaluation_lock_sha256']
    assert sha256(old/'execution.json')==meta['evaluation_execution_sha256']
    prior=json.loads((old/'lock.json').read_text());execution=json.loads((old/'execution.json').read_text())
    assert execution['complete'] and execution['lock_sha256']==sha256(old/'lock.json')
    assert prior['rows']==tl['rows'] and len(prior['rows'])==455
    references=['native_s1','native_s2','retained','expanded']
    trusted={};inputs=dict(prior['input_hashes'])
    for w in execution['workers']:
        p=old/f'worker_{w["index"]}/report.json'
        assert w['exit_code']==0 and sha256(p)==w['report_sha256']
        report=json.loads(p.read_text())
        assert report['complete'] and report['lock_sha256']==sha256(old/'lock.json')
        for row in report['rows']:
            assert row['group_id'] not in trusted
            trusted[row['group_id']]=row
        inputs[str(p)]=sha256(p)
    assert set(trusted)=={r['group_id'] for r in prior['rows']}
    for row in prior['rows']:
        g=row['group_id'];p=old/'examples'/g/'report.json'
        r=json.loads(p.read_text());assert r==trusted[g]
        seeds=prior['train_seeds'] if row['role']=='train' else prior['validation_seeds']
        entries=[e for e in r['entries'] if e['model'] in references]
        assert len(entries)==8 and {(e['model'],e['seed']) for e in entries}=={(m,s) for m in references for s in seeds}
        for e in entries:
            assert e['name']==f'{e["model"]}_seed{e["seed"]}.npy'
            coordinate=p.parent/e['name'];assert sha256(coordinate)==e['sha256']
            inputs[str(coordinate)]=e['sha256']
        inputs[str(p)]=sha256(p)
        for f in [Path(prior['source'])/'chemistry'/g/'mapping.npz',
                  Path(prior['source'])/'chemistry'/g/'native.pt',
                  Path(prior['source'])/'data/examples'/g/'gt.npz']:
            assert sha256(f)==inputs[str(f)]
    for p in [train/'lock.json',audit_path,control/'lock.json',control/'training_audit.json',old/'lock.json',old/'execution.json']:
        inputs[str(p)]=sha256(p)
    assert inputs[str(control/'training_audit.json')]==meta['control_audit_sha256']
    # No model, chemistry, sampler or per-case metric implementation changes.
    for f in ['models/differentiable_mini.py','models/diffusion_adapter.py','models/diffusion_scope.py',
              'models/soft_sequence_chart.py','folding_scale.py','diffusion_pilot_metrics.py']:
        assert sha256(root/'code/src/fastglycan'/f)==sha256(train/'code/src/fastglycan'/f),f
    hashes={str(p):sha256(p) for p in (root/'code').rglob('*') if p.is_file() and p.suffix in ['.py','.json','.md']}
    lock=copy.deepcopy(prior)
    lock.update(schema='folding_coordinate_evaluation_v1',train=str(train),control=str(control),reference_evaluation=str(old),
        checkpoints={'coordinate_zero':audit['checkpoint']},checkpoint_training_locks={'coordinate_zero':sha256(train/'lock.json')},
        checkpoint_arms={'coordinate_zero':'expanded'},selected_names={'coordinate_zero':tl['selected_names']},
        reuse_models={m:dict(root=str(old/'examples'),model=m,roles=['train','validation']) for m in references},
        models=references+['coordinate_zero'],hashes=hashes,input_hashes=inputs,
        contrasts=[['coordinate_zero',m] for m in ['expanded','retained','native_s1','native_s2']]
            +[['expanded','retained'],['native_s2','native_s1']],
        primary='coordinate_zero minus matched expanded terminal; observed validation32 is development, not fresh confirmation',
        planned_outputs=4550,planned_prediction_nfe=910,planned_probe_nfe=32,
        protocol_sha256=sha256(root/'code/docs/mini_folding_coordinate_evaluation_v1.md'),
        report_title='# C4/S1 coordinate-weight ablation: fixed terminal',
        report_intro='Both 423-protein arms start from the same retained checkpoint and receive the same ordered '
            '8192 exposures / 2048 updates. Only the experimental-GT aligned-coordinate weight changes from 0.01 to 0. '
            'GT local-distance and chemistry supervision remain; native S2 is auxiliary synthetic supervision. '
            'This is not model initialization from zero. ESM2 and C4 conditioning remain frozen.',
        training_curve_note='Matched TRAIN32 probes only. Both arms have exactly the same training membership, order and per-protein exposure.',
        cohort_scope_note='Original TRAIN128 and added TRAIN295 remain separate. The previously observed validation32 is now '
            'development evidence, not an independent confirmation set. Most sources are complete chains from homooligomers; '
            'assembly context and pretraining exposure remain limitations. A promising result requires later fresh confirmation.')
    lock['cohorts']['observed_validation32']=lock['cohorts'].pop('new_validation32')
    lock['cohort_order']=['observed_validation32','original_train128','added_train295']
    assert expected_evaluation_calls(lock,lock['rows'])==dict(native=0,coordinate_zero=910)
    assert len(lock['assignments'])==8 and 8*(1+3*len(lock['checkpoints']))==32
    write_json(root/'lock.json',lock)
    write_json(root/'prepare.json',dict(complete=True,lock_sha256=sha256(root/'lock.json'),
        reused_coordinates=3640,new_prediction_nfe=910,engineering_nfe=32,total_new_nfe=942))


def write_coordinate_report(root):
    output=root/'final';assert not output.exists()
    lock=json.loads((root/'lock.json').read_text());train=Path(lock['train']);control=Path(lock['control'])
    for p in [train/'lock.json',train/'ablation_training_audit.json',control/'lock.json',control/'training_audit.json']:
        assert sha256(p)==lock['input_hashes'][str(p)]
    audit=json.loads((train/'ablation_training_audit.json').read_text())
    original=json.loads((control/'training_audit.json').read_text())
    assert audit['complete'] and original['complete']
    history=train/'expanded/history.jsonl';tr=json.loads((train/'expanded/report.json').read_text())
    assert sha256(history)==tr['history_sha256'] and tr['lock_sha256']==sha256(train/'lock.json')
    clipped=sum(x.get('unclipped_accumulated_grad_norm',0)>1 for x in map(json.loads,history.read_text().splitlines()))
    candidate={**audit,'clipped_updates':clipped}
    training=dict(complete=True,summary={'expanded_control':original['summary']['expanded'],'coordinate_zero':candidate})
    evaluation=json.loads((root/'evaluation.json').read_text());cohorts=json.loads((root/'cohorts.json').read_text())
    assert evaluation['lock_sha256']==sha256(root/'lock.json') and cohorts['evaluation_sha256']==sha256(root/'evaluation.json')
    assert evaluation['counts']==dict(native=0,coordinate_zero=910) and evaluation['probe_nfe']==32
    job=json.loads((root/'submission.json').read_text())['score_job']
    scheduler=subprocess.check_output(['sacct','-j',job,'-n','-X','-P','--format=JobIDRaw,State,ExitCode'],text=True)
    assert f'{job}|COMPLETED|0:0' in scheduler
    text=render_folding_scale_report(lock,training,evaluation,cohorts)
    output.mkdir();(output/'report.md').write_text(text)
    with (output/'paired.csv').open('w',newline='') as f:
        fields=['cohort','group_id','pdb_id','length','candidate','reference','delta_aa','delta_ca','per_noise']
        writer=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');writer.writeheader()
        lookup={r['group_id']:r for r in lock['rows']}
        for row in cohorts['paired']:
            writer.writerow(dict(row,pdb_id=lookup[row['group_id']]['pdb_id'],per_noise=json.dumps(row['per_noise'],sort_keys=True)))
    write_json(output/'training_comparison.json',training)
    paths=[root/'lock.json',root/'execution.json',root/'evaluation.json',root/'cohorts.json',
        train/'ablation_training_audit.json',control/'training_audit.json',history,train/'expanded/report.json']
    write_json(output/'provenance.json',dict(complete=True,score_job=job,scheduler=scheduler,
        inputs={str(p):sha256(p) for p in paths},script_sha256=sha256(Path(__file__)),
        report_sha256=sha256(output/'report.md'),paired_csv_sha256=sha256(output/'paired.csv'),
        scope='fixed terminal matched objective ablation; observed validation is development; no model promotion'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--mode',choices=['prepare','report'],required=True);a=p.parse_args()
    if a.mode=='prepare':prepare_coordinate_evaluation(a.root.resolve())
    else:write_coordinate_report(a.root.resolve())
