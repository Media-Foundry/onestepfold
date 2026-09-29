# C4/S1 connection-onset confirmation v1

2026-09-30. Freeze CalibratedConnectionObjective from9f1393cd, its independent32
calibration q95 values, original chemistry and all solver settings. Move the
bounded paired experiment to actual C4/S1 inputs. No quantile, weight, step,
initialization or target selection changes based on outputs. This is confirmation
on seven previously used development proteins, NOT independent generalization.

Keep all eight historical source slots and two seeds12345/54321.3CR6's unsupported
covalent topology stays skipped before inference; retain its two prediction/four
repair slots in reporting. Native input packets contain sequence-derived chemical
features only; experimental GT is opened by scoring/repair evaluation, never by
model prediction or repair objective. Preserve atom identity/order and sourceGT.

On DiamondHill, at most one raw worker per supported protein/GCD (seven concurrent
GCDs; eight available). Frozen protenix_mini_esm_v0.5.0 and native ESM2-3B, FP32
parameters and operations, eval mode, no autocast/TF32/MC dropout, no MSA/template.
Use the audited full_recycle_pairformer with4 executed cycles, shared conditioning
across the two fixed identity-key noises. Preserve packed tensor layout, identity
augmentation, gamma0=0/lambda=1/eta=1, stable-Euler and N_step1. Check executed
Pairformer/denoiser counts and actual schedule. Log resolved config and effective
overrides separately. Repeat the first noise once with the same conditioning to
check exact forward replay; this is not another candidate or best-of-K selection.
Raw ceiling5400s per process; no retry with altered settings. Hash weight files
before and after the batch; check imported runtime and input hashes before use.

These settings differ from historical C1 inputs in noise construction and sampler
details too. Do not attribute any C1→C4 difference solely to recycle count.
The primary comparison is old vs calibrated repair on each new, identical C4 raw.

After model processes exit, freeze raw coordinate hashes and run both repair arms
using the previous CPU FP64 two-worker,3x60 L-BFGS protocol and900s external
ceiling. Both start from the same zero pose chart. All14 supported inputs get both
arms; preserve failures, missing outputs and unsupported source slots. No GT in
the solve, no branch correction, no relaxation after solve. Preserve all original
geometry/connection gates, empirical onsets remain objective parameters only.

Independent NumPy replay verifies saved parameters, input pairing, observed-mask
AA/Cα-lDDT, all old geometry results, branch diagnostics, and both objective
values. New C4 predictions have no historical repair replay baseline; explicitly
mark that check unavailable instead of pretending the C1 coordinates are matched.
Keep C4 forward exact replays separate from historical solver replay counts.

Report raw and both final outputs, per-noise/per-protein quality, losses relative
to raw, original joint acceptance, all individual geometry residuals, strict
checked chirality, serious overlaps, max penetration, global/local displacement,
runtime/memory and source failures. Carry the prior bounded development screen:
AA andCA paired protein means both improve and zero-severe+strict-chirality+budget
count does not decline. This is not deployment acceptance or a revised chemical
gate. Stop after this batch; inspect failure modes before any new method version.
