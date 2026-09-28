#!/usr/bin/env python3
"""Render the bounded atom-identity/experimental-reference/FD audit."""
import argparse,json,hashlib
from pathlib import Path

p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root
r=json.load(open(root/'report.json'));accept=json.load(open(root/'acceptance.json'))
assert r['complete'] and hashlib.sha256((root/'report.json').read_bytes()).hexdigest()==accept['report_sha256']
lines=['# Native geometry and derivative attribution — 2026-09-28','',
'CPU attribution reuses six development targets and experimental atom37 coordinates. No frozen temporal test, model training, threshold adjustment, or new mutation search. Two bounded conditioning checks used DiamondHill GCD0/1; the folding forward remained FP32.','',
'## Geometry measurement checks','',
'All native atom names, residue IDs and chain IDs match saved arrays. Independent sparse adjacency powers reproduce every graph-distance≤3 exclusion exactly. All six chains have L−1 peptide bonds. NumPy FP64 distances reproduce stored maximum penetration and severe-pair counts. This rules out these specific indexing/exclusion errors for the tested cases, not every possible representation issue.','',
'On the same observed atoms, experimental structures have zero noncovalent pairs below 1 Å, bond RMSE 0.034–0.040 Å, peptide MAE 0.0031–0.0062 Å, and chirality fraction 1.0. Missing experimental atoms never enter these calculations. The native sequence topology does not infer additional disulfide connectivity; no general ligand/disulfide chemistry calibration is claimed.','',
'## Severe pairs (distance < 1 Å)','',
'Each prediction cell is seed211 / seed223. Observed means both atoms are experimentally observed. Terminal10 means either of the first/last ten residues; removing them is an attribution diagnostic, never a revised acceptance rule.','',
'| Target | GT | Prediction all | Prediction observed | Prediction excluding terminal10 |',
'|---|---:|---:|---:|---:|']
for c in r['cases']:
 vals=lambda key:' / '.join(str(c['baselines'][s][key]['severe_pairs']) for s in ['211','223'])
 lines.append(f"| {c['case']} ({c['pdb']}) | {c['experimental']['all_atoms']['severe_pairs']} | {vals('all_atoms')} | {vals('observed_atoms')} | {vals('excluding_terminal10')} |")
lines += ['',
'9QR4 is dominated by unobserved terminal residues; initial100 and confirmation1 are dominated by terminal geometry. This is not the whole explanation: 8BZN, control and especially 8JC6 retain internal, experimentally observed collisions. A few local overlaps can coexist with high average distance-based quality; these diagnostics measure different aspects of the prediction.','',
'Examples (seed211, native residue numbering):','',
'| Target | Atoms | Predicted distance Å | Experimental distance Å |','|---|---|---:|---:|']
for name in ['8bzn','control','confirmation2']:
 c=next(c for c in r['cases'] if c['case']==name);v=c['baselines']['211']['top_pairs'][0];atom=lambda d:f"{d['residue_name']}{d['residue']}-{d['atom']}"
 lines.append(f"| {c['pdb']} | {atom(v['first'])} / {atom(v['second'])} | {v['distance']:.3f} | {v['experimental_distance']:.3f} |")
lines += ['','## Existing S1/S2 hard starts','',
'Rescored archived, unoptimized native hard predictions at seeds103/107. These use the earlier noise protocol and are separate from the newer seeds211/223; this is a within-archive S1/S2 comparison.','',
'| Target | Seed | S1 severe pairs | S2 severe pairs | S1/S2 max penetration Å |','|---|---:|---:|---:|---:|']
old=json.load(open(root/'archived_steps.json'))['rows']
for x in old:
 if x['steps']!=1:continue
 y=next(v for v in old if (v['case'],v['seed'],v['steps'])==(x['case'],x['seed'],2))
 lines.append(f"| {x['case']} | {x['seed']} | {x['geometry']['severe_pairs']} | {y['geometry']['severe_pairs']} | {x['geometry']['max_penetration']:.3f} / {y['geometry']['max_penetration']:.3f} |")
lines += ['','The second step helps some cases but does not uniformly repair chemistry; 8BZN seed103 increases from 6 to 17 severe pairs. Therefore these failures cannot be attributed exclusively to one diffusion call.','',
'## Conditioning derivative decomposition','',
'For the fixed conditioning point and fixed noise, compare vᵀ∇L with two central differences: the original nonlinear L(X), and ⟨∇X L(X₀), X(q+h v)−X(q−h v)⟩/(2h). The latter holds the loss gradient at X₀ fixed, isolating the denoiser response along the tested direction. Three block-RMS-scaled Gaussian directions; h=.01,.003,.001,.0003,.0001; unchanged 5% relative+1e−6 tolerance and adjacent-step requirement. Conditioning here is s_inputs/s/z, not sequence logits; this does not validate the full sequence path.','',
'| Target | Objective | Linearized coordinate FD | Nonlinear objective FD |','|---|---|---:|---:|']
for name in ['8bzn','control']:
 d=json.load(open(root/f'pullback_{name}.json'));assert d['complete']
 for objective in ['old','new']:
  s=d['summary'][objective+'_fp32'];count=lambda f:sum(s[f]['directions'])
  lines.append(f"| {name} | {objective} | {count('linear_pass')}/3 directions | {count('objective_pass')}/3 directions |")
lines += ['',
'8BZN new-loss direction1: at h=.003, autograd=0.159275, linearized FD=0.156962, nonlinear FD=0.084708. The denoiser response agrees while the finite perturbation through the loss does not. At h=.0003 the nonlinear estimate improves to0.155643, but at h=.0001 both estimates drift. This supports a narrow useful FD window caused by loss nonlinearity and finite-precision forward response; it does not prove a backward implementation defect. Original failed gates remain failed.','',
'Control remains unresolved: one direction fails even after the loss is linearized. This may involve directional cancellation/conditioning and forward numerical error; no single root cause is established. A passing random-direction test is limited evidence, not a full Jacobian proof.','',
'Recomputing only the downstream loss and its coordinate gradient in FP64 changes none of these direction pass/fail outcomes. The folding model was never converted to FP64, so this is not a whole-model FP64 verdict.','',
'## Decision','',
'Keep deployment rejected for the current input/objective/design procedure, and preserve the Mini one-step hypothesis. Geometry failures are measurable in native hard predictions before optimization; a hard chemistry gate is exposing them rather than creating them. Do not loosen caps on this panel or count task-only gains as design success.','',
'Next bounded priorities: isolate control conditioning directions by s_inputs/s/z and inspect per-term geometry-loss sensitivity; separately establish a chemistry-valid hard starting prediction/repair protocol with explicit coordinate-drift and task-quality limits. Any repair adds computation and must be reported. Do not start LoRA, expand mutation budgets or claim S2 is a chemistry-correct teacher from these data.','']
(root/'report.md').write_text('\n'.join(lines))
