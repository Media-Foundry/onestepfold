# Matched ESMC interface folding check v1

Freeze before any ESMC structural prediction. Independent of active global-distance
training/evaluation: same retained512 Mini diffusion checkpoint for both inputs,
SHA7fc01820269b6f376f8313b79c4ab2bf8fcfd2a0b2a017a432033a51b73fd829.
Only substitute the fixed TRAIN423 bridgebf06a640...949e and paired final ESMC
features. Frozen remaining model, hard native chemistry, C4/S1/K1, FP32, dropout
off and identity-bound noise; no output repair or training. This measures this
interface plus encoder, not intrinsic ESMC versus ESM2 superiority.

Use exactly32 original TRAIN probe IDs already in the scaling lock plus all32
observed DEV; same two seeds per role as prior evaluations. No new protein/seed
selection. DEV is observed development evidence; no per-target or best-of-noise
selection. Reuse128 hash-bound retained predictions. Add128 ESMC predictions.
Recompute native C4 for every target and require exact archived conditioning
parity before running ESMC C4. All chemistry tensors remain identical; only the
sequence embedding and its linear projection change. Pack ESMC conditioning in
the same manner as original inference. No stale ESM2 s/z enters the ESMC output.

One separate shortest52/longest968 TRAIN preflight precedes four length-squared
balanced workers. Per engineering target: nativeC4/S1 exact retained replay,
ESMC C4/S1, restored-nativeC4/S1, reloaded-ESMC C4/S1 exact repeat. Require all
non-interface weights unchanged and full state restored at job end. Forward
hooks verify544 Pairformer stack calls (136 four-cycle passes) and136 diffusion
calls in total:128 candidate outputs plus8 preflight outputs. Preflight and parity
work are overhead, not deployment cost. Sequence encoder inference is cached and
excluded from measured timing; do not claim whole-fold speed.

Fixed GT atom masks/identities, existing per-case scorer unchanged with independent
dense lDDT check. Report separate protein means, paired AA/CA differences/95% CIs,
P01/P05/worst5%,drops<-0.05,GT-alignedCA RMSD and upper deterioration tails, geometry
and introduced failures.256 scores include128 reused references. Failures remain
in64-protein denominator; no partial success report or automatic promotion.

All scientific sources/code/checkpoints/bridge/protocol hash-bound before preflight.
HPC3 acd_u; preflight success gates four independent workers, then CPU scoring.
No auto-requeue; invalid dependencies cancel. Do not change ridge or model after
seeing results. Poor outcomes apply to this fixed interface; a later new method
requires a separate justified experiment.

Execution correction: first preflight662579 failed native coordinate exact replay
before an ESMC batch was released. Native C4 flattened values matched the cache,
but the new driver passed original un-packed tensor views to diffusion. Retry1
uses the same flat.split(sizes).reshape(shapes) native layout as the archived
reference and the existing ESMC path. No checkpoint, scientific input, threshold,
model operation or budget changes; failed root preserved. Successful retry is
required before attributing this to the packing mismatch.
