# Mini hybrid pilot: completed results

## 2026-09-28 — Hybrid pilot complete; deployment remains rejected

All eight DiamondHill workers and the independent scorer exited successfully.
Six S1 cases generated 48 gradient and 48 random single-mutation proposals;
two S2 cases were derivative-only. No model training. All process handles terminal.
Local verification matched eight report hashes and 204 coordinate artifact hashes.
Report: reports/mini_hybrid_2026-09-28/report.md; frozen protocol/lock archived there.

Coordinate-to-loss FD passed for both objectives in FP32 and coordinate-only FP64.
Conditioning/full-sequence FD remain mixed. Supplemental block-RMS perturbations
rescue 8BZN old-objective conditioning FD, but not its new objective or control.
This demonstrates scale sensitivity, not an identified autograd defect; no full
model FP64 claim. Fixed-chart derivatives do not describe atom-graph transitions.

Task-only improvements: gradient 23/48, random 23/48. Joint acceptance: both 0/48.
All six baseline sequences fail absolute chemistry limits at both new noise seeds;
max-penetration cap rejects all 96 proposals. These conservative pilot thresholds
were not relaxed. Thus this experiment cannot establish proposal superiority from
valid starting structures. All four archived chemistry-collapse cases are rejected.
The two new-to-objective cases remain development data, not temporal validation.

Next recommendation (not launched): audit native baseline geometry and offending
atom pairs/exclusions against independent chemistry references; calibrate any future
policy on separate data before locking it. Narrow remaining conditioning FD failures
with adequate directional signal. Do not expand candidate budget or train LoRA yet.
Implementation backup: 8baaae52. Final evidence backed up separately.

## Interpretation and next bounded work

The locked hard acceptance policy successfully rejects the archived collapse cases.
It does not establish that the new differentiable objective prevents collapse:
none of the newly evaluated sequences meets all chemistry limits, including every
unmutated baseline. Task-only gains are not design successes. The equal 23/48
counts are descriptive on this small selected panel, not an equivalence test.

Before another optimization run, inspect the atom identities responsible for the
maximum penetration, verify covalent exclusions and reference geometry, and compare
native S1/S2 predictions with experimental structures under exactly the same
measurement. Any threshold calibration must use separate development evidence and
be frozen before a fresh confirmation; preserve this pilot's failures unchanged.

For derivatives, retain the original unit-direction results and the separately
labelled relative-scale diagnostic. The latter improves the old 8BZN check but
does not resolve the remaining failures. Coordinate-only FP64 passing offers no
evidence of a useful whole-model FP64 rescue. No new GPU batch or training has
been launched after this completed pilot.

Full tables: [report](../reports/mini_hybrid_2026-09-28/report.md).
Independent artifact acceptance: [acceptance](../reports/mini_hybrid_2026-09-28/final/acceptance.json).
The archived protocol and lock remain unchanged.
