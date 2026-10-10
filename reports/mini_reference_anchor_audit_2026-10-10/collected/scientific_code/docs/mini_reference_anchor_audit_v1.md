# Paired-reference native suffix: implementation and gradient audit

This2026-10-10 audit follows c12a2681. It tests a different training graph,
not another optimizer or post-hoc scale. No model is optimized or selected.
All previous experiments and quality conclusions remain closed.

Let U_theta(a) be the existing stage-aligned pair suffix applied to candidate
block13 and its own frozen conditioning, and U_theta(WT,i) its actual execution
on the reference at site i. Define A_theta(i)=U_theta(WT,i)-WT_z_C4 and predict
U_theta(a)-A_theta(i). Reference inputs are legal WT data, never mutant teacher
states. Keep candidate B_inputs/B_s exactly; keep native Mini and S1 frozen.
There are no additional trainable parameters, spatial-rank restrictions, new
loss weights, or changed final targets. No-edit output remains the exact input.

At initialization both native suffix executions recover their archived states,
so A=0 and every candidate matches the old baseline exactly. At fixed theta the
subtraction is common across the site's candidates and cannot improve centered
AA predictions in real arithmetic. Its possible value is in the training graph:
reference drift must receive its gradient, not be detached or reused after an
optimizer update. The AA objective/gradient is unchanged at fixed parameters;
the common-error gradient is changed. This does not expand centered-AA capacity.

Use the same original48 sites and24 references. Existing candidate block13,
B_inputs/B_s/B_z and teacher labels are reused. Generate only24 WT continuation
calls from existing WT3/RNG, one per reference, to record WT block13/14. Require
bit-identical WT final s/z replay. No new target C4/recycle, ESM/MSA preparation,
teacher label, diffusion, scoring or experimental structure is generated.
The reference-cache work and bytes are reported separately, not hidden as free.

Two original seeds272001/272003. Check all48x19 candidates per seed against the
original class from the immutable fullbatch source: same state hash, outputs,
fixed single/input, initial zero anchor, candidate order and reference integrity.
Keep original forward semantics and parameter/state names after extracting its
suffix method. Unit tests also check a perturbed model, exact no-edit, stale or
foreign cache rejection, finite differences, and joint versus shared pullback.

On TRAIN only (15 references,27 sites,513 candidates), at initialization compute
the full, common and AA gradients of the old Final objective. Average within a
site in native FP32 and across sites in FP64, as in the previous audit. Check
the full gradient against the stored initial gradient (relative L2<=5e-6).
The common VJP uses the fixed current site mean error; its gradient is exactly
the common MSE gradient in real arithmetic. Subtract the WT reference VJP from
both full/common gradients to derive the anchored full/common gradients. The
AA gradient is unchanged. Record norms, alignments, site variation and group
contributions; these are instantaneous gradients, not Adam update attribution.
Reference VJPs and both candidate backward passes are charged explicitly.

Independently compare the streaming reference-gradient proxy with a joint
autograd graph on the fixed first TRAIN site T37, all19 candidates, both seeds.
The proxy aggregates gradient at a detached reference-output leaf, then applies
exactly one pullback through the real reference graph. Accept relative gradient
L2<=5e-5 in native FP32; retain max absolute differences. FP64 unit tests use
strict1e-11/1e-12 and a finite-difference check. No optimizer step occurs.

For a nonzero-state functional check, load the already fixed AdamW272001/128
checkpoint from the preceding batch. On T37 check candidate-order independence,
no-edit identity, and AA centering invariance within FP32 subtraction rounding
bounds. This is not a quality comparison or a model selection. No held-protein
scores are computed or used to choose this architecture.

Run on HIP4 with HIP_VISIBLE_DEVICES only. HIP5 remains untouched;6/7 unused.
Lock source/data/old-checkpoint/protocol hashes before execution. A single run
has a two-hour cap; retain a failed attempt and do not automatically retry.
Success means the architecture and its actual backward/cache behavior are
implemented correctly. It does not establish learnability, generalization,
decoder benefit, or speed. A later training protocol must be defined separately.
