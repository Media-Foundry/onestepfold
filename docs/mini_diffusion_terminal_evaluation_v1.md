# Diffusion learning pilot: terminal evaluation execution lock

2026-09-30, before any held-out prediction or score. Implements the comparison in
`mini_diffusion_learning_pilot_v1.md`; no checkpoint, target, seed or loss selection.

Require BOTH training arms complete512updates/2048exposures with identical order,
initialization and fixed LR schedule. Re-read history and optimizer step counts;
verify loss component arithmetic, finite gradients and checkpoint hashes. Native
base parameter equality is checked by the terminal training worker. Do not begin
held-out inference if these checks fail.

All160 targets, two fixed seeds per role, four models: untouchedS1, untouchedS2,
mergedGT-S1 and mergedGT+S2-S1. TRAIN uses600001/600011; VALIDATION600029/600043.
TRAIN native predictions reuse the audited cache. VALIDATION predictions are new.
No input dependence on GT: GT is read only by the separate CPU scoring stage.
EightGCDs partition complete targets by length², never split an individual target's
noise/model comparisons across workers. No postprocessing or relaxation.

Every worker checks nativeS1 against a TRAIN cache probe and each adapter at zero,
loaded and merged state. Loaded/merged predictions must match exactly, native
state-dict keys must return. This probe is engineering replay, not a quality choice.
Planned new diffusion calls:512 TRAIN student +320 VALIDATION +56 probes =888.
Final score inventory:128 TRAIN×2×4=1024 and32 VALIDATION×2×4=256, total1280.

Scoring uses Boolean GT mask before all quality/bond-GT arithmetic and checks the
native mapping against original atom37 observations. Full predicted atom inventory
is used for chemistry, including atoms missing in GT. Observed inter-residue AA/CA
lDDT is independently recalculated using dense distances in row blocks. Sparse
chemistry search includes all possible positive penetrations (4Å > maximum radius
sum3.6Å), graph distances<=3 excluded. Unit checks compare against the former dense
GeometryTopology and poison missing GT with NaN to expose accidental label use.
Report observed-GT bond error and legacy native-reference bond diagnostics separately.

Typed connection distributions retain the frozen calibration bands, unsupported
cis groups and GT branch mismatch; these are descriptive, not new acceptance gates.
Legacy joint pass is not applicable as a combined repair gate because this experiment
does not impose the old raw-displacement contract. No chemistry failures are waived.

Summaries are separate for TRAIN and VALIDATION. Average the two noise scores within
each protein first. Primary paired mean AA-lDDT differences and percentile95% CI use
10000 paired protein bootstrap samples, seed20260930. Secondary CA, P01/P05,
worst5%mean (ceil(.05*N) proteins), Δ<−.05 counts and per-noise differences remain.
These small-tail summaries are descriptive, especially N=32. Report new severe
clashes on previously zero-clash outputs and lost strict checked stereochemistry.
No pooling across roles/no best-of-seed/no new noninferiority margin.

Inference timing is cached-conditioning diffusion timing on shared eightGCD hardware;
it is not end-to-end ESM+four-recycle latency or an isolated timing benchmark. S1 NFE
remains one after weight merging. Record training wall time separately. Runtime or
scoring failures stay in the planned denominator and prevent a complete summary;
do not silently exclude a target.
