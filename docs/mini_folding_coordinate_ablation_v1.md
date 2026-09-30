# C4/S1 GT coordinate-term ablation v1

Status: scientific protocol fixed before any candidate training. Implementation,
runtime preflight and submission remain to be completed. This is one bounded
development experiment, not a deployment gate or another data-size sweep.

## Question and sole intervention

Does removing the experimental-GT globally aligned coordinate MSE term improve
the quality/geometry tradeoff at the same TRAIN423 continuation budget?

The saved1MV8 audit demonstrates an objective tradeoff; the completed scaling
experiment demonstrates poorer held-out transfer from continued TRAIN128 fitting.
Neither proves that coordinate MSE causes all generalization failures. This
ablation tests that candidate explanation without tuning a coefficient on1MV8.

Control is the already completed TRAIN423 run in
`/data/user/shuang886/Folding/folding_scale_training_v1_20260930`, arm`expanded`,
terminal SHA256`3e6c6e1b1a493215adba31df1106efa9e30218c5f92846f4ca4d2e3a6fd17b09`.
Its original lock SHA256 is
`1ec3f1c13fec5ea12981f9efef37957fec264c1bc0e659c9fc4a98519384c357`.
Do not train the candidate from this terminal. Start from the same retained
full-diffusion512 parent as the control, SHA256
`7fc01820269b6f376f8313b79c4ab2bf8fcfd2a0b2a017a432033a51b73fd829`.

Change only `weights.coordinate: 0.01 -> 0.0`. Retain every other weight exactly
from the control lock, including smooth-lDDT temperature, bond/chirality/clash
terms and nativeS2 auxiliary preservation. Continue computing and logging the
unweighted coordinate term for audit. Experimental GT local distances and chemical
labels remain supervision; nativeS2 is not experimental truth.

## Matched training contract

Copy the control's exact423 group IDs,8192 exposure records, order and noises;
same source/cache hashes, ESM2, cachedC4, nativeFP32 backend, S1/K1 and chemistry.
Same288 selected diffusion tensors, frozen remaining model, optimizer reset,
AdamW settings, accumulation4, clipping1 and64-update warmup/cosine2048 schedule.
Exactly2048 new updates/8192 exposures. No augmentation, depth, optimizer, dataset,
noise or interface changes. Do not add ESMC, LoRA or output repair to this test.

Use a separate immutable code/input root on HPC3 `acd_u`, one H100. Preserve
all original control training/evaluation artifacts. Stop at2048; no best-probe
checkpoint selection, extensions, extra seeds or weight sweep. Saved checkpoints
and original TRAIN32 probes stay at0/512/1024/2048. Probes are training diagnostics.

Before training, bind the parent, control, caches, source, protocol, code and
parameter names. On the original shortest/longest TRAIN engineering examples,
verify native/parent forward replay, finite loss and gradients on the selected
scope. Zeroing a loss coefficient must not change an untrained forward. Verify
that all unweighted terms remain identical and the total changes by exactly the
removed weighted coordinate contribution within recorded numeric tolerance.
Bind that preflight to release. Failures are retained; do not overwrite/restart
a partial scientific run without a separately recorded continuation decision.

## Fixed-terminal evaluation

Evaluate the candidate once at2048 on the same455 proteins and the same assigned
two noises. Reuse hash-verified original nativeS1/nativeS2/retained/expanded outputs;
do not recompute those references or treat them as GT. The candidate adds910
prediction NFEs; lock the exact additional engineering-probe count in the execution
manifest before submission. Independent GT scoring and all planned denominators
are required, including runtime failures. No partial-result selection.

Primary contrast is candidate minus frozen expanded control. Also compare candidate
with retained, nativeS1 and nativeS2. Keep originalTRAIN128, addedTRAIN295 and the
now-observed VAL32 separate. The latter is **development validation for this new
experiment**, not a fresh independent confirmation. Exclude it from optimization.
Any promising candidate requires a later independently frozen confirmation set;
do not claim generalization success from repeated use of these32 alone.

Report protein means over noises, AA/Cα-lDDT, aligned Cα RMSD, paired95% bootstrap
intervals, P01/P05/worst5%, quality drops below−0.05, severe collision counts,
strict checked chirality, newly damaged clean outputs, typed connections and cost.
Use the existing metric/mask/calibration definitions; do not restore legacy ideal
connection maxima as the sole veto. Account for possible global/local quality
tradeoffs; lower lDDT loss alone is not acceptance.

This is a diagnostic contrast with no automatic model promotion. Improved held-out
development means accompanied by worsening tails or chemistry must be reported as
a tradeoff. A negative or inconclusive result does not authorize an automatic
coefficient grid. Retained remains the research reference until separate evidence
supports replacing it. No BindCraft/design or backward-certification claim follows.
