#!/usr/bin/env python3
import argparse,json
from pathlib import Path
from collections import Counter
from fastglycan.paired_teacher_protocol import sha256
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root
accept=json.load(open(root/'final/acceptance.json'));audit=json.load(open(root/'final/report.json'))
assert sha256(root/'final/report.json')==accept['report_sha256']
lines=['# Hybrid mutation / segmented derivative pilot','',
'Locked protocol; no model training. New seeds211(selection)/223(confirmation). Six S1 proposal targets and two S2 derivative-only references.','',
'Each cell below is the original fixed unit-direction FD gate result, not proof of an autograd bug. Low directional signal and perturbation scaling must be considered. Coordinate FP64 tests only the coordinate-to-loss segment, never the full folding model.','',
'| Case | Steps | Coordinate old32/64 | Coordinate new32/64 | Conditioning old/new | Sequence old/new |',
'|---|---:|---|---|---|---|']
def value(v):return 'pass' if v else 'fail'
for run in audit['runs']:
 s=run['segments'];pair=lambda a,b:f'{value(s[a])}/{value(s[b])}'
 lines.append(f'| {run["name"]} | {run["name"][-1]} | {pair("coordinates_old_float32","coordinates_old_float64")} | {pair("coordinates_new_float32","coordinates_new_float64")} | {pair("conditioning_old","conditioning_new")} | {pair("sequence_old","sequence_new")} |')
lines += ['','## Equal-budget hard proposals','',
'Geometry acceptance is conjunctive: task gains cannot compensate for failed absolute or nonregression geometry limits. These are conservative pilot limits, not universal chemical standards. No thresholds were relaxed after observing results.','',
'| Case | Panel | Baseline geometry valid211/223 | Arm | Task improves211 | Geometry valid211 | Joint accepted211 | Confirmed223 |',
'|---|---|---|---|---:|---:|---:|---:|']
counts=Counter()
for run in audit['runs']:
 if 'arms' not in run:continue
 report=json.load(open(root/run['name']/'report.json'))
 assert sha256(root/run['name']/'report.json')==run['report_sha256']
 for arm,summary in run['arms'].items():
  rows=[r for r in report['candidates'] if r['arm']==arm]
  task=sum('no_task_improvement' not in r['decisions']['211']['reasons'] for r in rows)
  geometry=sum(not any(reason!='no_task_improvement' for reason in r['decisions']['211']['reasons']) for r in rows)
  baseline='/'.join(value(run['baseline_geometry'][seed]['accepted']) for seed in ('211','223'))
  lines.append(f'| {run["name"]} | {run["panel"]} | {baseline} | {arm} | {task}/8 | {geometry}/8 | {summary["accepted_on_selection_noise"]}/8 | {summary["retained_on_confirmation_noise"]}/8 |')
  for r in rows:counts.update(r['decisions']['211']['reasons'])
lines += ['','Reasons can overlap; rejection counts: `'+json.dumps(dict(counts),sort_keys=True)+'`.','',
'If the baseline and all candidates violate absolute geometry constraints, this pilot does not establish whether gradient proposals are superior on a valid design starting point. Zero joint acceptance is not evidence that gradients are useless. Task-only gains remain diagnostic, not design successes.','',
'Old8BZN/control collapse regressions were rescored with graph-distance≤3 exclusions and all rejected. Raw severe counts therefore differ from the earlier direct-bond-only metric; compare new-policy baseline and candidate values within the same report.','',
'The two confirmation targets were selected before candidate results and near-duplicate filtered, but originate from existing development data. They are new-to-this-objective confirmations, not a frozen temporal/homology-independent test.']
for case in ('8bzn','control'):
 path=root/f'relative_fd_{case}/report.json'
 if path.exists():
  r=json.load(open(path));assert r['complete']
  lines += ['',f'## Additional relative-scale conditioning FD: {case}','',
            'Three Gaussian directions scaled separately by the RMS of s_inputs,s,z; original unit-direction outcomes are unchanged. Same5% relative+1e-6 absolute criterion, with relative h=.03,.01,.003,.001,.0003. This is a numerical diagnostic, not acceptance-rule retuning.',
            '',f'Old objective: {value(r["objectives"]["old"]["passed"])}. New objective: {value(r["objectives"]["new"]["passed"])}.']
(root/'report.md').write_text('\n'.join(lines)+'\n')
