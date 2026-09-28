#!/usr/bin/env python3
"""Audit branch additivity and render conditioning/loss diagnostic tables."""
import argparse,hashlib,json
from pathlib import Path

p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--prior-root',type=Path,required=True);p.add_argument('--hybrid-root',type=Path,required=True);a=p.parse_args();root=a.root
runs={name:json.load(open(root/(name+'.json'))) for name in ['control_s_inputs','control_s','control_z','8bzn_all']}
for name,r in runs.items():
 assert r['complete'] and r['forward_replay_exact'] and r['prior_point_replay']
 for objective in r['summary']:
  for field in ('linear_pass','objective_pass'):
   flags=[]
   for d in r['directions']:
    rows=d['rows'];flags.append(any(x['values'][objective][field] and y['values'][objective][field] for x,y in zip(rows,rows[1:])))
   assert flags[:3]==r['summary'][objective][field]['random_directions']
   assert flags[3]==r['summary'][objective][field]['aligned']
prior=json.load(open(a.prior_root/'pullback_control.json'))
additivity=[]
for direction in range(3):
 for objective in ('old','new'):
  parts=[runs['control_'+branch]['directions'][direction]['rows'][0]['values'][objective]['analytic'] for branch in ['s_inputs','s','z']]
  total=sum(parts);reference=prior['directions'][direction]['rows'][0]['values'][objective+'_fp32']['analytic']
  if abs(total-reference)>1e-6+1e-4*abs(reference):raise ValueError('branch sum differs from parent derivative')
  additivity.append(dict(direction=direction,objective=objective,parts=parts,total=total,reference=reference,
                         between_branch_cancellation=sum(abs(x) for x in parts)/max(abs(total),1e-15)))
lines=['# Conditioning branch / objective backtrace','',
'No model, objective weights or deployment thresholds changed. Existing control and8BZN only; no sequence optimization or temporal test. All folding calls FP32. Original failed gates remain archived.','',
'## Replay guard attribution','',
'First four jobs stopped at a guard that compared packed-gradient inputs against an original no-grad tuple. The follow-up layout audit holds these factors apart. Packed grad/no-grad/repeated forwards are exactly equal; original grad/no-grad also match. Original and packed inputs have identical values/shapes/strides, but different storage arrangements and slightly different outputs. This establishes packing sensitivity, not random execution or a backward defect; a specific kernel has not been identified. v2 fixes the guard to compare packed inputs on both sides, retaining exact equality.','',
'## Per-branch random-direction checks','',
'Three original Gaussian directions are restricted to each branch, retaining their original RMS scale. An additional gradient-aligned direction is labelled separately and never substitutes for random-direction gates. Each pass requires two adjacent h values under the unchanged 5%+1e-6 criterion.','',
'| Target / branch | Objective | Linearized FD random | Objective FD random | Aligned linear / objective |','|---|---|---:|---:|---|']
for name,r in runs.items():
 for objective in ['old','new','contact','ca_clash','ca_chain','bond','peptide','clash','chirality']:
  s=r['summary'][objective];lin=s['linear_pass'];obj=s['objective_pass']
  inactive=all(d['rows'][0]['values'][objective]['analytic']==0 for d in r['directions'])
  label=objective+(' (zero directional signal)' if inactive else '')
  lines.append(f"| {name} | {label} | {sum(lin['random_directions'])}/3 | {sum(obj['random_directions'])}/3 | {lin['aligned']} / {obj['aligned']} |")
lines += ['','## Cross-branch cancellation','',
'The three isolated derivatives sum back to the previous mixed derivative within 1e-6+1e-4 relative tolerance. Ratios below describe cancellation between branches, not a condition-number bound.','',
'| Direction | Objective | s_inputs | s | z | Sum | Sum abs / abs sum |','|---:|---|---:|---:|---:|---:|---:|']
for row in additivity:
 vals=' | '.join(f'{v:.7g}' for v in row['parts'])
 lines.append(f"| {row['direction']} | {row['objective']} | {vals} | {row['total']:.7g} | {row['between_branch_cancellation']:.2f} |")
lines += ['','## Numerical detail','',
'Per-term analytic/linearized/nonlinear responses, absolute dot-product sums, h scans and pointer alignment are retained in JSON. These are local conditioning tests; they do not certify end-to-end sequence derivatives or cross-graph mutations. Zero-signal terms passing absolute tolerance are not positive gradient evidence. The helper decomposition is tested against original total values and coordinate gradients.','']

import numpy as np
pair=json.load(open(root/'clash_pairs_8bzn/report.json'));assert pair['complete']
parent=json.load(open(a.hybrid_root/'8bzn_s1/report.json'));hard=parent['baseline']['values']['211']
path=a.hybrid_root/'8bzn_s1'/hard['coordinate_file']
assert hashlib.sha256(path.read_bytes()).hexdigest()==hard['coordinate_sha256']
with np.load(path) as data:
 coords=data['coordinates'].reshape(-1,3)
 top=pair['rows'][0]['top_pairs'][0];i=top['first']['index'];j=top['second']['index']
 assert data['atom_names'][i]==top['first']['atom'] and data['atom_names'][j]==top['second']['atom']
 hard_distance=float(np.linalg.norm(coords[i]-coords[j]))
lines += ['## Localized clash mechanism','',
 'This is the soft chart at softmax(4×onehot): native amino-acid probability≈0.742 at every position, before optimization. It is not the native hard prediction. Atom inventory and identity-keyed initial noise211 are fixed.', '',
 f"HIS42-CE1 / THR43-OG1 distance: soft chart {top['base_distance']:.6f} Å, archived native hard seed211 {hard_distance:.6f} Å. The latter is a matched atom/noise comparison, not an experimental GT distance.", '',
 '| h | Pair contribution to clash remainder | Total clash remainder | Signed fraction | Hinge active at base/plus/minus |',
 '|---:|---:|---:|---:|---|']
for row in pair['rows']:
 t=row['top_pairs'][0]
 lines.append(f"| {row['h']} | {t['remainder']:.7f} | {row['total_remainder']:.7f} | {t['remainder']/row['total_remainder']:.1%} | {t['active_zero']}/{t['active_plus']}/{t['active_minus']} |")
lines += ['',
 'The dominant pair never crosses the hinge threshold in this test. Its near-zero separation makes the distance response strongly nonlinear at these finite perturbations. Other pairs do cross the hinge; this is not a claim that all hinge effects vanish. Pair attribution recomputes distances in FP64 from saved FP32 coordinates; it is not FP64 model inference.', '',
 'At h=.003, all-atom clash accounts for99.6% of the total new-objective nonlinear-minus-linearized remainder. The dominant pair alone accounts for74.2% of the clash remainder; at h=.001 this rises to90.5%. These are signed remainder ratios for the selected failing direction, not population estimates.', '',
 '## Updated conclusion', '',
 'The current soft input already produces a severely overlapping state before any sequence optimization. Together with the nonzero, reproducible branch derivatives, this supports investigating the soft input interpolation and geometry objective before altering diffusion weights. It does not certify all derivatives: control random-direction checks still fail, with smaller signals degrading as h shrinks. Its three branch derivatives add back to the prior mixed derivative; new-objective direction1 also has3.74× cross-branch cancellation.', '',
 'All three control branches pass the new-objective linearized check on the separately labelled gradient-aligned direction. The nonlinear objective still fails there for s and z, so this is not a usable optimizer gate or proof that simply following the gradient is safe.', '',
 'Next proposed bounded experiment: measure hard-neighborhood input interpolation (and individual ESM/reference-feature paths) against native geometry, keeping graph and noise fixed. Any change to distance regularization should be an explicit ablation, retaining hard physical-geometry acceptance. Do not equate a smoother loss with chemically valid structures. No such new experiment or model training has been launched in this batch.', '']

(root/'report.md').write_text('\n'.join(lines))
manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.glob('*.json')}
(root/'acceptance.json').write_text(json.dumps(dict(complete=True,branch_additivity=additivity,input_sha256=manifest,report_sha256=hashlib.sha256((root/'report.md').read_bytes()).hexdigest()),indent=2)+'\n')
