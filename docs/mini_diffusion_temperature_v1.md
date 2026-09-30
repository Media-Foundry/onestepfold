# One matched-strength smooth-lDDT temperature intervention

2026-09-30, after326125f8 and before the new calibration or training.
The previous recipe×LR comparison is closed, unchanged. This is one new objective
intervention, not a temperature/LR/rank search and not a restart of numerical FD work.

## Evidence and hypothesis

The current sparse loss matches reported lDDT's observed inter-residue15Å neighborhood
and per-atom reduction. Its sigmoid width0.1Å is a custom scratch-era choice, not a
mask implementation defect. The frozen native Protenix source uses
`sigmoid(threshold - distance_error)`, equivalent to width1Å. It uses a different
reduction, so changing our width alone does NOT reproduce the official full loss.
Reference: https://github.com/bytedance/Protenix/blob/main/protenix/model/loss.py
Local frozen source: `/media/PM982/onestepfold/protenix_stage0_pkg/v1_1/site/protenix/model/loss.py`,
SHA256 c5a8c348d589829f3ed1eee36dbc04206773b50a4f22cac00f11fa4d7d978a88.

A narrow surrogate concentrates slope near the four thresholds and saturates away
from them. This is a mathematical property, not evidence that it caused the observed
quality tradeoff. Test whether widening that response, with typical initial gradient
strength matched, improves actual hard-lDDT/chemistry at the same optimization budget.
No source/GT inventory, metric, chemistry rule, inference backend or sequence path changes.

## Initial-state scale calibration, then one new run

Use exactly the previously frozen16TRAIN groups, two original training noises,
public Mini plus zero adapter. Compute native S1 once perpoint,32forwards total.
Get the two raw D parameter-gradient vectors at temperatures0.1 and1.0 (64VJPs).
Require coordinates and0.1 gradients to replay the archived initial diagnostic.
Save both vectors and independently recompute norms/dot products on CPU.
No terminal or validation quality is used to select a weight.

Define m_t=median_protein(mean_two_noises(||grad D_t||_2)). Fix
`new_weight_D = old_weight_D * m_0.1 / m_1.0`, where old_weight_D=1.
This matches one initial Euclidean norm statistic, not every target or Adam update;
report the actual directional cosines and the factor. No scan or post hoc adjustment.

One new `wide_matched` arm starts from original public Mini/zero rank8 adapter.
All other weights equal the frozen calibrated recipe from326125f8; LR and schedule
match its calibrated_high arm exactly (peak1e-4,32warmup,cosine to1e-5).
Same128TRAIN/order/two noises/2048exposures/accum4/512updates/clip1/Adam settings.
Teacher remains nativeS2 coordinate auxiliary, not experimental truth.
Keep0.1 as code default for every historical caller. Baseline is archived
calibrated_high, not a new rerun, and neither checkpoint initializes the new run.
Stop after512 regardless of interim losses; no checkpoint selection.

## Terminal TRAIN-only comparison

All128TRAIN at both original seeds. Compare nativeS1/S2, archivedcalibrated_high,
newwide_matched (plus archivedcalibrated_low descriptively). Reuse only hash-bound
coordinates. Preserve raw AA/CA quality, protein paired means/10000bootstrap seed20260930,
paired tails, new clashes on previously zero inputs, strict checked stereo, GT bonds,
connection distributions/branch mismatches, weight change and real coordinate response.
Two-noise averages are within protein; no pooling seeds as independent proteins.
No new generalization or deployment claim; old revealed validation32 remains unused.
Scalar D losses across temperatures are not the same objective or directly comparable.

The main comparison is wide_matched−calibrated_high. A change in temperature plus
matched scalar is one combined intervention; do not attribute any result solely to
width or claim exact equal total-gradient/compute strength. No new chemical pass or
noninferiority threshold. Failure to establish useful joint progress closes this
hypothesis at this budget rather than triggering another temperature sweep.
