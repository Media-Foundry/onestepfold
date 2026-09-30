# TRAIN-only component-gradient and update-budget diagnosis v1

2026-09-30, after40bc604f. The512-update trial is CLOSED. This is a bounded diagnostic,
not its continuation, a learning-rate grid, FD debugging or a validation selection.

Use only the128 already-trained proteins. Before computation, stratify by length
50–127,128–255,256–511,512–1024, rankwithin each by SHA256 of
`diffusion-gradient-budget-v1:20260930:<group_id>`, take first4 each. No scores used
for selection. Sixteen proteins are a deliberately length-balanced TRAIN diagnostic,
not a prevalence estimate or new independent panel. Both original training noises
600001/600011. No old/new VALIDATION outputs or labels are read.

Three parameter states: native plus zero-up adapter, frozenGT terminal512, frozen
GT+S2 terminal512. Reuse identical cachedC4 conditioning; all predictions must replay
the corresponding TRAIN archive exactly. NativeFP32, no model/optimizer updates,
all public base weights unchanged. FullGTmask and old chemistry objective unchanged.

At each16×2×3=96point, compute raw reverse-mode gradients to all835584adapter
parameters for A,D,B,C,R,T. Apply the OLD weights(.01,1,10,1,.1,.0025) when reporting
weighted norms/Gram matrices. Also differentiate completeGT andGT+S2 objectives
directly to check linear reconstruction, without finite differences. All eight
reverse passes reuse one forward graph;96denoiser calls planned. Zero-up initialization
has zero down-matrix gradients by construction; report down/up separately, not as a bug.

Group structure=A/100+D+10B; chemistry=C+.1R; teacher=.0025T. Report norms, cosines,
teacher/GT norm ratio, chemistry/structure ratio and signed projections onto the
GT gradient. A negative cosine is local opposition, not proof of global harm;
projections can exceed1/be negative and are not causal percentages. Zero signal
remains explicit (undefined ratios/cosines), not assigned perfect alignment.

Retain raw gradient vectors remotely for independent CPU recomputation; Git backs up
protocol, identities, hashes, allscalar/Gram results and audit rather than~2GBvectors.
No vector rescaling, clipping, Adam step, coordinate correction or parameter mutation.
The previous fulltraining update sizes and clipping counts remain separate evidence;
these singleprotein gradients do not reproduce batch4 Adam dynamics.

Summarize perpoint and perprotein (two noise results retained), by state and length.
Do not pool the96points as96independent proteins. No new acceptance threshold or
trainingweight will be selected from validation. Stop after this diagnosis and use
the findings to specify one subsequent optimization comparison, if justified.
