#!/usr/bin/env python3
"""Render audited terminal results without modifying frozen evaluation artifacts."""
import argparse
import csv
import inspect
import json
import subprocess
from pathlib import Path
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.folding_report import render_folding_scale_report


def write_folding_scale_report(root, output):
    assert not output.exists(), 'preserve previous report output'
    lock=json.loads((root/'lock.json').read_text());train=Path(lock['train'])
    evaluation=json.loads((root/'evaluation.json').read_text());cohorts=json.loads((root/'cohorts.json').read_text())
    training=json.loads((train/'training_audit.json').read_text())
    assert evaluation['lock_sha256']==sha256(root/'lock.json')
    assert cohorts['evaluation_sha256']==sha256(root/'evaluation.json')
    assert training['lock_sha256']==sha256(train/'lock.json')
    assert sha256(train/'training_audit.json')==lock['input_hashes'][str(train/'training_audit.json')]
    submission=json.loads((root/'submission.json').read_text());job=submission['score_job']
    scheduler=subprocess.check_output(['sacct','-j',job,'-n','-X','-P','--format=JobIDRaw,State,ExitCode'],text=True)
    assert f'{job}|COMPLETED|0:0' in scheduler
    text=render_folding_scale_report(lock,training,evaluation,cohorts)
    output.mkdir(parents=True)
    (output/'report.md').write_text(text)
    # Compact, auditable per-protein quality pairs, keeping both noise responses.
    with (output/'paired.csv').open('w',newline='') as f:
        fields=['cohort','group_id','pdb_id','length','candidate','reference','delta_aa','delta_ca','per_noise']
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        lookup={r['group_id']:r for r in lock['rows']}
        for row in cohorts['paired']:
            writer.writerow(dict(row,pdb_id=lookup[row['group_id']]['pdb_id'],per_noise=json.dumps(row['per_noise'],sort_keys=True)))
    inputs=[root/'lock.json',root/'evaluation.json',root/'cohorts.json',root/'execution.json',train/'lock.json',train/'training_audit.json']
    write_json(output/'provenance.json',dict(complete=True,score_job=job,scheduler=scheduler,
        inputs={str(p):sha256(p) for p in inputs},script_sha256=sha256(Path(__file__)),
        renderer_sha256=sha256(Path(inspect.getsourcefile(render_folding_scale_report))),
        report_sha256=sha256(output/'report.md'),paired_csv_sha256=sha256(output/'paired.csv'),
        scope='rendering existing audited outputs, no metric or scientific-protocol change'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();write_folding_scale_report(a.root.resolve(),a.output.resolve())
