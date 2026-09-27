#!/usr/bin/env python3
"""Render completed, independently audited four-gate results without new inference."""
import argparse,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from fastglycan.paired_teacher_protocol import sha256


def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root
 final=root/'final_audit_v2';accept=json.load(open(final/'acceptance.json'));report=json.load(open(final/'report.json'))
 if sha256(final/'report.json')!=accept['report_sha256']:raise ValueError('audit hash mismatch')
 rows=[];data={}
 for run in report['runs']:
  name=Path(run['path']).name;path=root/name/'report.json'
  if sha256(path)!=run['report_sha256']:raise ValueError('run report changed after audit')
  r=json.load(open(path));label=name.rsplit('_s',1)[0].replace('gate_v2_','').replace('gate_v1','initial100')
  data.setdefault(label,{})[r['opt_s']]=r
  jumps=run['chart_boundaries'];maximum=max((x['rmsd'] for x in jumps),default=None)
  g=run['gates'];fd=' / '.join('pass' if g[f'local_gradient_s{s}'] else 'fail' for s in (1,2))
  delta=run['hard_loss_deltas'];arm=r['opt_s']
  rows.append(f'| {label} | s{arm} | {"pass" if g["native_replay"] else "fail"} | {fd} | {"down" if g["soft_optimization"] else "not down"} | {delta[f"s{arm}_seed103"]:+.6f} | {delta[f"s{arm}_seed107"]:+.6f} | {maximum:.3f} |' if maximum is not None else
              f'| {label} | s{arm} | {"pass" if g["native_replay"] else "fail"} | {fd} | {"down" if g["soft_optimization"] else "not down"} | {delta[f"s{arm}_seed103"]:+.6f} | {delta[f"s{arm}_seed107"]:+.6f} | unmeasured |')
 fig,axes=plt.subplots(2,2,figsize=(10,7),constrained_layout=True)
 for ax,(label,arms) in zip(axes.flat,data.items()):
  for arm,r in sorted(arms.items()):
   t=r['trajectory'];ax.plot([v['update'] for v in t],[v['loss'] for v in t],label=f'optimize S{arm}')
   changed=[v for v in t if v['topology_changed']]
   ax.scatter([v['update'] for v in changed],[v['loss'] for v in changed],s=14,marker='x')
  ax.set_title(label);ax.set_xlabel('optimizer update');ax.set_ylabel('own-sampler soft proxy loss');ax.legend()
 fig.savefig(root/'optimization_curves.png',dpi=180);plt.close(fig)
 content='''# Four-stage sequence gate results

All reported gates are implementation/diagnostic evidence, not binder-design acceptance.
The input map recomputes ESM and chemistry from20-way sequence probabilities but
uses a piecewise native atom inventory. It is not globally smooth. The objective
is monomer nonlocal Cα contacts plus chain/clash guards; it does not measure affinity.

Negative hard-loss deltas mean improvement relative to the original hard sequence.
Seed103 is the optimization noise;107 is held out. Finite differences require a
plateau at two adjacent h values in each of3directions. Failed gates are retained.

| Target | Optimization | Native replay | FD S1 / S2 | Soft loss | Hard Δ seed103 | Hard Δ seed107 | Maximum chart jump Å |
|---|---|---|---|---|---:|---:|---:|
'''+ '\n'.join(rows)+'''

![Soft optimization curves](optimization_curves.png)

Cross marks indicate hard-sequence/atom-inventory changes. A decreasing soft loss
alone is insufficient: the rebuilt hard sequence must retain its benefit under
independent noise, and all-atom geometry must be checked separately. The full JSON
includes matched S1/S2 cross-scores, bond errors, peptide C–N errors, chirality,
sub-Angstrom clashes, hard-replay errors and file hashes.

The selected targets are diagnostics, not a prevalence sample. The chart-boundary
measurements are finite observed jumps, not a proof of global continuity. No model
weights were trained and no frozen test set was used. Deployment remains rejected.
'''
 boundary_path=root/'boundary_v1/report.json'
 if boundary_path.exists():
  boundary=json.load(open(boundary_path))
  if not boundary['complete']:raise ValueError('boundary probe incomplete')
  content += '\n## Actual atom-inventory boundary probe\n\n'
  content += 'On the first argmax crossing along the saved100-residue S1 optimization displacement:\n\n'
  content += '| h | Max probability difference | Aligned Cα RMSD Å | Atom inventories |\n|---:|---:|---:|---|\n'
  for row in boundary['rows']:
   content += f"| {row['h']:.0e} | {row['probability_max_difference']:.7f} | {row['aligned_ca_rmsd']:.6f} | {row['atom_counts'][0]} → {row['atom_counts'][1]} |\n"
  content += '\nThe output difference remains about0.184A while the input difference shrinks100-fold. This observed nonvanishing boundary jump rejects a globally smooth-oracle claim for the current chart implementation. It does not implicate diffusion step count alone.\n'
 (root/'report.md').write_text(content)

if __name__=='__main__':main()
