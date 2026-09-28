#!/usr/bin/env python3
"""Report original gates without converting low-signal passes into evidence."""
import argparse,json
from pathlib import Path
from fastglycan.paired_teacher_protocol import sha256,write_json
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root;audit=json.load(open(root/'audit.json'));assert audit['complete']
lines=['# Near-hard full ERC logits gradient gate','',
'Existing development cases only:8BZN/control, alpha1e-4/1e-3, C4/S1 or S2, native fixed chemical graph, identity-keyed noise211, FP32. Exact hard is a replay/chemistry reference, not a central-difference point. Every q±hv recomputes live ESM and all input-dependent conditioning/caches. No training, optimization, source-combination expansion or loss smoothing.', '',
'Original random directions remain in logits space:seed731, Gaussian L×20, per-residue shift removed, global norm1; h=.3,.1,.03,.01,.003. Original gate:5%+1e-6, two adjacent h for every direction, finite nonzero and exactly repeated gradient. Actual q is FP32 log of intended interior probabilities, with softmax(q) fed to the model.', '',
'Informative is a separate conservative annotation: original tolerance pass, relative-only pass, nonzero loss/probability/coordinate response, and relative tolerance term larger than absolute (max(|AD|,|FD|)>2e-5), again at adjacent h in every direction. Low-signal/absolute-assisted passing rows remain original passes, not positive derivative evidence. This crossover is not a measured hardware noise bound.', '',
'## Original and signal-aware gates','',
'Each count below is passing random directions out of3. A complete gate additionally checks gradient finiteness/nonzero/repeatability. The new objective retains its .01KL(p||p0) term; coordinate linearization includes the direct KL derivative.','',
'| Arm | Objective | Nonlinear FD | Linearized FD | Informative nonlinear | Original gate | Signal label |','|---|---|---:|---:|---:|---|---|']
reports={}
for item in audit['runs']:
 r=json.load(open(root/item['name']/'report.json'));reports[item['name']]=r
 for objective in ['old','new']:
  n=item['summary'][objective]['nonlinear'];l=item['summary'][objective]['linearized']
  lines.append(f"| {item['name']} | {objective} | {sum(n['original_direction_plateaus'])}/3 | {sum(l['original_direction_plateaus'])}/3 | {sum(n['informative_direction_plateaus'])}/3 | {n['original_passed']} | {n['label']} |")
lines+=['','## Geometry relative to same-sampler hard baseline','',
'Absolute and nonregression requirements remain unchanged. A hard baseline failing chemistry is not exempted, and small displacement does not establish a usable design state.','',
'| Arm | Hard/near severe pairs | Hard/near max penetration Å | Hard/near bond RMSE Å | Hard/near peptide MAE Å | Near chemistry gate | CA displacement Å |','|---|---|---|---|---|---|---:|']
for name,r in reports.items():
 b=r['hard_geometry'];g=r['geometry'];fmt=lambda k:f"{b[k]:.5g} / {g[k]:.5g}"
 lines.append(f"| {name} | {fmt('severe_pairs')} | {fmt('max_penetration')} | {fmt('bond_rmse')} | {fmt('peptide_mae')} | {r['geometry_gate']['accepted']} | {r['near_hard_ca_rmsd']:.6g} |")
lines+=['','## Magnitudes and replay','',
'Ranges cover all original random-direction h rows for the new objective; signs and individual numerators are retained in JSON. No direction or h is substituted after observing the results.','',
'| Arm | abs(AD) range | abs(loss numerator) range | Probability delta norm range | Coordinate delta norm range | Grad/no-grad exact | Repeated gradient max error |','|---|---|---|---|---|---|---|']
for name,r in reports.items():
 rows=[row for d in r['directions'] for row in d['rows']]
 def span(values):return f'{min(values):.3g}–{max(values):.3g}'
 lines.append(f"| {name} | {span([abs(x['objectives']['new']['nonlinear']['analytic']) for x in rows])} | {span([abs(x['objectives']['new']['nonlinear']['numerator']) for x in rows])} | {span([x['probability_delta_norm'] for x in rows])} | {span([x['coordinate_delta_norm'] for x in rows])} | {r['grad_no_grad_exact']} | {r['gradient_stats']['new']['repeat_max_abs']:.3g} |")
lines+=['','Input traces (token mixture→ESM→projected ESM→s_inputs), all geometry metrics including chirality, gradients, probabilities and coordinates are archived per arm. CPU loss/geometry replay validates artifacts but never replaces recorded GPU values when computing the original FD verdict. A passing numerical gate on these fixed graphs would not certify cross-argmax transitions, hard-mutation utility or a globally continuous oracle.','']
(root/'report.md').write_text('\n'.join(lines));write_json(root/'acceptance.json',dict(complete=True,audit_sha256=sha256(root/'audit.json'),report_sha256=sha256(root/'report.md'),coordinate_records=audit['coordinate_records'],model_deployment_accepted=False))
